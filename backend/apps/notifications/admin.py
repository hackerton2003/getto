from django.contrib import admin
from apps.notifications.models import (
    Notification,
    WebhookDelivery,
    WebhookSubscription,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient_type",
        "recipient_id",
        "title",
        "channel",
        "is_read",
        "created_at",
    )
    list_filter = ("recipient_type", "channel", "is_read")
    search_fields = ("title", "message")


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner_type",
        "owner_id",
        "target_url",
        "active",
        "created_at",
    )
    list_filter = ("owner_type", "active")
    search_fields = ("target_url",)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscription",
        "event_type",
        "status",
        "attempts",
        "last_http_status",
        "next_attempt_at",
        "created_at",
    )
    list_filter = ("status", "event_type")
    readonly_fields = ("payload", "created_at")
