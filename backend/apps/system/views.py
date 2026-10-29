from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema

from api.v1.pagination import StandardResultsSetPagination
from api.v1.permissions import IsStaff
from api.v1.serializers.system import (
    AuditLogSerializer,
    SystemSettingsSerializer,
    VisitorLogSerializer,
)
from api.v1.utils import raise_api_validation
from apps.system.models import AuditLog, SystemSettings, VisitorLog
from services.system import SystemService


class SystemSettingsView(APIView):
    permission_classes = (IsStaff,)

    @extend_schema(responses={200: SystemSettingsSerializer}, operation_id="system_settings_retrieve")
    def get(self, request):
        settings_instance = SystemService.get_settings()
        return Response(SystemSettingsSerializer(settings_instance).data)

    @extend_schema(request=SystemSettingsSerializer, responses={200: SystemSettingsSerializer}, operation_id="system_settings_update")
    def patch(self, request):
        if not isinstance(request.data, Mapping):
            raise ValidationError({"detail": "Expected an object containing settings fields."})
        try:
            settings_instance = SystemService.update_settings(
                settings_id=SystemService.get_settings().pk,
                **{key: value for key, value in request.data.items() if key != "id"},
            )
        except SystemSettings.DoesNotExist as exc:
            raise NotFound("System settings not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(SystemSettingsSerializer(settings_instance).data)


class AuditLogViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsStaff,)
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsSetPagination


class VisitorLogViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsStaff,)
    queryset = VisitorLog.objects.all()
    serializer_class = VisitorLogSerializer
    pagination_class = StandardResultsSetPagination
