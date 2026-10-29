from django.db import models

# Create your models here.
from django.db import models

from apps.locations.models import District, Ward


class University(models.Model):
    name = models.CharField(max_length=150)
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="universities",
    )

    class Meta:
        db_table = "universities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campus(models.Model):
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="campuses",
    )
    name = models.CharField(max_length=150)
    ward = models.ForeignKey(
        Ward,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="campuses",
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    class Meta:
        db_table = "campuses"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.university.name}"
