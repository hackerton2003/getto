from django.contrib import admin
from apps.system.models import AuditLog, SystemSettings, VisitorLog


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "service_fee_percentage",
        "panel_theme",
        "enduser_theme",
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "actor_type",
        "actor_id",
        "action",
        "ip_address",
        "created_at",
    )
    list_filter = ("actor_type", "action")
    readonly_fields = ("created_at",)
    search_fields = ("action", "description", "actor_lastname")


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ("id", "ip_address", "location_name", "visited_at")
    readonly_fields = ("visited_at",)
    search_fields = ("ip_address", "location_name", "user_agent")
