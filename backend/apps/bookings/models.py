from django.db import models
from django.db.models import Q

# Create your models here.

class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    room = models.ForeignKey(
        "properties.Room",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    reference_no = models.CharField(
        max_length=50,
        unique=True,
    )
    request_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "bookings"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=("pending", "confirmed", "rejected", "cancelled", "expired")),
                name="booking_status_valid",
            ),
            models.UniqueConstraint(
                fields=("room",),
                condition=Q(status__in=("pending", "confirmed")),
                name="uniq_active_booking_room",
            ),
        ]

    def __str__(self):
        return f"{self.reference_no} - {self.status}"
        
    
