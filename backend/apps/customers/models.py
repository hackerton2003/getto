from django.db import models
from django.db.models import F, Q
from apps.universities.models import Campus, University
from apps.locations.models import District, Region, Ward

# Create your models here.
class Customer(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DEACTIVATED = "deactivated", "Deactivated"

    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    photo = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=255)

    university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,
        related_name="customers",
    )

    campus = models.ForeignKey(
        Campus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customers",
    )

    admission_info = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"
        ordering = ["firstname", "lastname"]

    def __str__(self):
        return f"{self.firstname} {self.lastname}"
        
        
        
class CustomerPreference(models.Model):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_preferences",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_preferences",
    )
    ward = models.ForeignKey(
        Ward,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_preferences",
    )
    preferred_room_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )
    min_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "customer_preferences"
        constraints = [
            models.CheckConstraint(
                condition=(Q(min_price__isnull=True) | Q(min_price__gte=0)),
                name="pref_min_price_nonneg",
            ),
            models.CheckConstraint(
                condition=(Q(max_price__isnull=True) | Q(max_price__gte=0)),
                name="pref_max_price_nonneg",
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_price__isnull=True)
                    | Q(max_price__isnull=True)
                    | Q(min_price__lte=F("max_price"))
                ),
                name="pref_price_range_valid",
            ),
        ]

    def __str__(self):
        return f"Preferences - {self.customer.firstname} {self.customer.lastname}"
        
        
class Favourite(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="favourites",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="favourited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favourites"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "property"],
                name="unique_customer_property_favourite",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.firstname} - {self.property.name}"

        
        
class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.IntegerField()
    comment = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by_staff = models.ForeignKey(
        "staff.Staff", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="moderated_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="review_rating_in_range",
            ),
            models.UniqueConstraint(
                fields=["customer", "property"],
                name="unique_customer_property_review",
            )
        ]

    def __str__(self):
        return f"{self.customer.firstname} - {self.property.name} - {self.rating}"
        
        
        
class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWED = "reviewed", "Reviewed"
        DISMISSED = "dismissed", "Dismissed"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reason = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    reviewed_by_staff = models.ForeignKey(
        "staff.Staff", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_property_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.firstname} - {self.property.name}"
