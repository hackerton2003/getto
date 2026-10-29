from django.db import models

# Create your models here.

from apps.staff.models import Staff


class AccommodationOwner(models.Model):

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

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_by_staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_accommodation_owners",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accommodation_owners"
        ordering = ["firstname", "lastname"]

    def __str__(self):
        return f"{self.firstname} {self.lastname}"
