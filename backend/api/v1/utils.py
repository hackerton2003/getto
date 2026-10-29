from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.system.models import AuditLog
from services.system import SystemService


def raise_api_validation(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


def audit_staff_action(request, action, description=None):
    SystemService.record_audit(
        actor_type=AuditLog.ActorType.STAFF,
        actor_id=request.user.pk,
        actor_lastname=request.user.lastname,
        actor_phone=request.user.phone,
        action=action,
        description=description,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


class PublicReadOnlyViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    pagination_class = None
