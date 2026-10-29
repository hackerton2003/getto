from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.system.views import (
    AuditLogViewSet,
    SystemSettingsView,
    VisitorLogViewSet,
)

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("visitor-logs", VisitorLogViewSet, basename="visitor-log")

urlpatterns = [
    path("settings/", SystemSettingsView.as_view(), name="system-settings"),
] + router.urls
