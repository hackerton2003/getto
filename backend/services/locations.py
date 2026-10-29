from django.core.exceptions import ValidationError
from django.db import transaction

from apps.locations.models import District, Region, Street, Ward


class LocationService:
    @staticmethod
    @transaction.atomic
    def create_location_path(*, region_name, district_name, ward_name, street_name):
        names = (region_name, district_name, ward_name, street_name)
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValidationError("Location names cannot be blank.")
        region, _ = Region.objects.get_or_create(name=region_name.strip())
        district, _ = District.objects.get_or_create(
            region=region,
            name=district_name.strip(),
        )
        ward, _ = Ward.objects.get_or_create(
            district=district,
            name=ward_name.strip(),
        )
        street, _ = Street.objects.get_or_create(
            ward=ward,
            name=street_name.strip(),
        )
        return street