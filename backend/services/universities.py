from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.universities.models import Campus


class UniversityService:
    @staticmethod
    def create_campus(*, university_id, name, latitude, longitude, ward=None):
        latitude = UniversityService._coordinate(latitude, "latitude", Decimal("-90"), Decimal("90"))
        longitude = UniversityService._coordinate(longitude, "longitude", Decimal("-180"), Decimal("180"))
        return Campus.objects.create(
            university_id=university_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            ward=ward,
        )

    @staticmethod
    def _coordinate(value, field_name, minimum, maximum):
        try:
            coordinate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: "Enter a valid coordinate."}) from None
        if not coordinate.is_finite() or not minimum <= coordinate <= maximum:
            raise ValidationError({field_name: f"Coordinate must be between {minimum} and {maximum}."})
        return coordinate