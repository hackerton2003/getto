from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.payments.models import Payment, Receipt
from apps.system.models import SystemSettings


class PaymentService:
    @staticmethod
    def _amount(value, field_name, *, allow_zero=False):
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: "Enter a valid monetary amount."}) from None
        if amount < 0 or (amount == 0 and not allow_zero):
            comparator = "zero or greater" if allow_zero else "greater than zero"
            raise ValidationError({field_name: f"Amount must be {comparator}."})
        return amount

    @classmethod
    def create_payment(cls, *, booking_id, payment_method, service_fee=None):
        with transaction.atomic():
            booking = Booking.objects.select_for_update().select_related("room").get(pk=booking_id)
            if booking.status not in (Booking.Status.PENDING, Booking.Status.CONFIRMED):
                raise ValidationError({"booking": "Payment is not allowed for this booking."})

            rental_amount = cls._amount(booking.room.price, "rental_amount")
            if service_fee is None:
                fee_percentage = SystemSettings.objects.filter(pk=1).values_list(
                    "service_fee_percentage", flat=True
                ).first()
                if fee_percentage is None:
                    fee_percentage = Decimal("10.00")
                service_fee = (rental_amount * fee_percentage / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            fee = cls._amount(service_fee, "service_fee", allow_zero=True)
            return Payment.objects.create(
                booking=booking,
                customer=booking.customer,
                rental_amount=rental_amount,
                service_fee=fee,
                total_amount=rental_amount + fee,
                payment_reference=f"PAY-{uuid4().hex.upper()}",
                payment_method=payment_method,
                status=Payment.Status.PENDING,
            )

    @staticmethod
    def complete_payment(*, payment_id):
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment_id)
            if payment.status == Payment.Status.FAILED:
                raise ValidationError({"payment": "A failed payment cannot be completed."})

            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.COMPLETED
                payment.paid_at = timezone.now()
                payment.save(update_fields=("status", "paid_at"))

            receipt = payment.receipts.first()
            if receipt is None:
                receipt = Receipt.objects.create(
                    payment=payment,
                    receipt_number=f"RCT-{uuid4().hex.upper()}",
                    issued_at=timezone.now(),
                )
            return payment, receipt

    @staticmethod
    def fail_payment(*, payment_id):
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment_id)
            if payment.status == Payment.Status.COMPLETED:
                raise ValidationError({"payment": "A completed payment cannot be failed."})
            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=("status",))
            return payment