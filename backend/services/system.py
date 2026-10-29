from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.system.models import AuditLog, SystemSettings, VisitorLog


class SystemService:
    @staticmethod
    def get_settings(*, company_name="Getto"):
        settings, _ = SystemSettings.objects.get_or_create(
            pk=1,
            defaults={"company_name": company_name},
        )
        return settings

    @staticmethod
    @transaction.atomic
    def update_settings(*, settings_id, **changes):
        allowed_fields = {
            "company_name",
            "logo",
            "slogan",
            "ads",
            "address",
            "location",
            "service_fee_percentage",
            "panel_theme",
            "enduser_theme",
        }
        unexpected_fields = set(changes) - allowed_fields
        if unexpected_fields:
            raise ValidationError({"fields": f"Unsupported settings: {', '.join(sorted(unexpected_fields))}."})

        if "service_fee_percentage" in changes:
            fee = SystemService._percentage(changes["service_fee_percentage"])
            if not fee.is_finite() or not Decimal("0") <= fee <= Decimal("100"):
                raise ValidationError({"service_fee_percentage": "Fee percentage must be between 0 and 100."})
            changes["service_fee_percentage"] = fee

        settings = SystemSettings.objects.select_for_update().get(pk=settings_id)
        for field_name in ("panel_theme", "enduser_theme"):
            if field_name in changes:
                field = SystemSettings._meta.get_field(field_name)
                valid_values = {value for value, _ in field.choices}
                if changes[field_name] not in valid_values:
                    raise ValidationError({field_name: "Choose a valid theme."})

        for field_name, value in changes.items():
            setattr(settings, field_name, value)
        settings.save(update_fields=tuple(changes))
        return settings

    @staticmethod
    def _percentage(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"service_fee_percentage": "Enter a valid percentage."}) from None

    @staticmethod
    def record_audit(*, actor_type, action, actor_id=None, actor_lastname=None,
                     actor_phone=None, description=None, ip_address=None):
        if actor_type not in AuditLog.ActorType.values:
            raise ValidationError({"actor_type": "Choose a valid actor type."})
        return AuditLog.objects.create(
            actor_type=actor_type,
            actor_id=actor_id,
            actor_lastname=actor_lastname,
            actor_phone=actor_phone,
            action=action,
            description=description,
            ip_address=ip_address,
            created_at=timezone.now(),
        )

    @staticmethod
    def record_visit(*, ip_address=None, latitude=None, longitude=None,
                     location_name=None, user_agent=None):
        if latitude is not None:
            latitude = SystemService._coordinate(latitude, "latitude", Decimal("-90"), Decimal("90"))
        if longitude is not None:
            longitude = SystemService._coordinate(longitude, "longitude", Decimal("-180"), Decimal("180"))
        return VisitorLog.objects.create(
            ip_address=ip_address,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            user_agent=user_agent,
            visited_at=timezone.now(),
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