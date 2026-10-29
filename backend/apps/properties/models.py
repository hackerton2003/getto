from django.db import models
from django.db.models import F, Q

from apps.house_owners.models import AccommodationOwner
from apps.locations.models import Street

# Create your models here.

class Property(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    owner = models.ForeignKey(
        AccommodationOwner,
        on_delete=models.PROTECT,
        related_name="properties",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    street = models.ForeignKey(
        Street,
        on_delete=models.PROTECT,
        related_name="properties",
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )
    total_rooms = models.IntegerField(default=0)
    available_rooms = models.IntegerField(default=0)
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "properties"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_rooms__gte=0, available_rooms__gte=0)
                & Q(available_rooms__lte=F("total_rooms")),
                name="property_room_counts_valid",
            ),
        ]

    def __str__(self):
        return self.name
        
        
class PropertyMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="media",
    )
    type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
    )
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "property_media"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.property.name} - {self.type}"
        
        
        
class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        OCCUPIED = "occupied", "Occupied"
        UNAVAILABLE = "unavailable", "Unavailable"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    room_type = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    capacity = models.IntegerField()
    length_m = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    width_m = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    area_sqm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    facilities = models.TextField(
        null=True,
        blank=True,
    )
    security_info = models.TextField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_VERIFICATION,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rooms"
        ordering = ["property", "room_type"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="room_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1),
                name="room_capacity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.room_type}"
        
        
class RoomMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="media",
    )
    type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
    )
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "room_media"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.room.property.name} - {self.room.room_type} - {self.type}"
        
        
class Verification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    submitted_at = models.DateTimeField()
    reviewed_by_staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_verifications",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    remarks = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "verifications"
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("property",),
                condition=Q(status="pending"),
                name="uniq_pending_verif_property",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.status}"


class VerificationDocument(models.Model):
    verification = models.ForeignKey(
        Verification,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file_path = models.CharField(
        max_length=255,
    )
    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)

    class Meta:
        db_table = "verification_documents"

    def __str__(self):
        return f"Verification Document - {self.verification.property.name}"
