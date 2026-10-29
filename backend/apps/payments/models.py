from django.db import models
from django.db.models import F, Q
from apps.bookings.models import Booking

# Create your models here.
class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    rental_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    service_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
    )
    payment_method = models.CharField(
        max_length=50,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "payments"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status__in=("pending", "completed", "failed"))
                    & Q(rental_amount__gt=0)
                    & Q(service_fee__gte=0)
                    & Q(total_amount=F("rental_amount") + F("service_fee"))
                ),
                name="payment_amounts_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.payment_reference} - {self.status}"
        
        
        
class Receipt(models.Model):
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
    )
    issued_at = models.DateTimeField()

    class Meta:
        db_table = "receipts"
        constraints = [
            models.UniqueConstraint(
                fields=("payment",),
                name="one_receipt_per_payment",
            ),
        ]

    def __str__(self):
        return self.receipt_number
