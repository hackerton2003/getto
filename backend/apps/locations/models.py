from django.db import models

# Create your models here.


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "regions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(models.Model):
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="districts",
    )
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "districts"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "name"],
                name="unique_district_per_region",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.region.name}"


class Ward(models.Model):
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="wards",
    )
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wards"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["district", "name"],
                name="unique_ward_per_district",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.district.name}"


class Street(models.Model):
    ward = models.ForeignKey(
        Ward,
        on_delete=models.PROTECT,
        related_name="streets",
    )
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "streets"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["ward", "name"],
                name="unique_street_per_ward",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.ward.name}"
