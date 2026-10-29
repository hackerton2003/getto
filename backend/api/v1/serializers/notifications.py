from rest_framework import serializers

from apps.notifications.models import Notification, WebhookSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class WebhookSubscriptionCreateSerializer(serializers.Serializer):
    target_url = serializers.URLField(max_length=500)
    event_types = serializers.ListField(
        child=serializers.CharField(max_length=100),
        allow_empty=False,
    )


class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = ("id", "target_url", "event_types", "active", "created_at")
        read_only_fields = fields


class WebhookSubscriptionCreatedSerializer(WebhookSubscriptionSerializer):
    secret = serializers.CharField()

    class Meta(WebhookSubscriptionSerializer.Meta):
        fields = (*WebhookSubscriptionSerializer.Meta.fields, "secret")
