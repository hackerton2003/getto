from datetime import timedelta
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.customers.models import Customer
from apps.properties.models import Property, Room
from services.properties import PropertyService
from services.notifications import NotificationService


class BookingService:
    ACTIVE_STATUSES = (Booking.Status.PENDING, Booking.Status.CONFIRMED)
    TRANSITIONS = {
        Booking.Status.PENDING: {
            Booking.Status.CONFIRMED,
            Booking.Status.REJECTED,
            Booking.Status.CANCELLED,
            Booking.Status.EXPIRED,
        },
        Booking.Status.CONFIRMED: {
            Booking.Status.CANCELLED,
            Booking.Status.EXPIRED,
        },
    }

    @classmethod
    def create_booking(cls, *, customer_id, room_id):
        property_id = Room.objects.values_list("property_id", flat=True).get(pk=room_id)
        now = timezone.now()

        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            room = Room.objects.select_for_update().get(pk=room_id, property=property_instance)
            if room.status != Room.Status.AVAILABLE:
                raise ValidationError({"room": "This room is not available for booking."})

            customer = Customer.objects.get(pk=customer_id)
            if customer.status != Customer.Status.ACTIVE:
                raise ValidationError({"customer": "Only active customers can book a room."})

            booking = Booking.objects.create(
                customer=customer,
                room=room,
                reference_no=f"BK-{uuid4().hex.upper()}",
                request_date=now,
                status=Booking.Status.PENDING,
                created_at=now,
                updated_at=now,
            )
            room.status = Room.Status.RESERVED
            room.save(update_fields=("status", "updated_at"))
            PropertyService._sync_locked_room_counts(property_instance)
            NotificationService.send(
                recipient_type="owner",
                recipient_id=property_instance.owner_id,
                title="New booking request",
                message=f"Booking {booking.reference_no} was requested for {property_instance.name}.",
            )
            return booking

    @classmethod
    def transition(cls, *, booking_id, status):
        if status not in Booking.Status.values:
            raise ValidationError({"status": "Choose a valid booking status."})

        room_id = Booking.objects.values_list("room_id", flat=True).get(pk=booking_id)
        property_id = Room.objects.values_list("property_id", flat=True).get(pk=room_id)
        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            room = Room.objects.select_for_update().get(pk=room_id, property=property_instance)
            booking = Booking.objects.select_for_update().get(pk=booking_id, room=room)

            if booking.status == status:
                return booking
            if status not in cls.TRANSITIONS.get(booking.status, set()):
                raise ValidationError({
                    "status": f"Cannot change booking from {booking.status} to {status}."
                })

            now = timezone.now()
            booking.status = status
            booking.updated_at = now
            if status == Booking.Status.CONFIRMED:
                booking.confirmed_at = now
            if status == Booking.Status.CANCELLED:
                booking.cancelled_at = now
            booking.save(update_fields=("status", "updated_at", "confirmed_at", "cancelled_at"))

            has_active_booking = Booking.objects.filter(
                room=room,
                status__in=cls.ACTIVE_STATUSES,
            ).exists()
            room.status = Room.Status.RESERVED if has_active_booking else Room.Status.AVAILABLE
            room.save(update_fields=("status", "updated_at"))
            PropertyService._sync_locked_room_counts(property_instance)
            recipient_type = "owner" if status == Booking.Status.CANCELLED else "customer"
            recipient_id = property_instance.owner_id if status == Booking.Status.CANCELLED else booking.customer_id
            NotificationService.send(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                title="Booking status updated",
                message=f"Booking {booking.reference_no} is now {booking.status}.",
            )
            return booking

    @classmethod
    def expire_stale_bookings(cls, *, expiry_hours=24, limit=None):
        """
        Expires pending bookings older than `expiry_hours` (e.g. 24-48 hours),
        restores reserved room status back to AVAILABLE, and resyncs property room counts.
        """
        if isinstance(expiry_hours, bool) or not isinstance(expiry_hours, int) or expiry_hours < 1:
            raise ValidationError({"hours": "Hours must be a positive integer."})
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
        ):
            raise ValidationError({"limit": "Limit must be a positive integer."})
        cutoff = timezone.now() - timedelta(hours=expiry_hours)
        stale_qs = Booking.objects.filter(
            status=Booking.Status.PENDING,
            created_at__lte=cutoff,
        ).order_by("created_at")

        if limit:
            stale_booking_ids = list(stale_qs.values_list("id", flat=True)[:limit])
        else:
            stale_booking_ids = list(stale_qs.values_list("id", flat=True))

        expired_bookings = []
        for booking_id in stale_booking_ids:
            try:
                booking = cls.transition(booking_id=booking_id, status=Booking.Status.EXPIRED)
                expired_bookings.append(booking)
            except (ObjectDoesNotExist, ValidationError):
                continue

        return expired_bookings
