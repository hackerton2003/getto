from django.urls import path
from apps.notifications.views import (
    NotificationListView,
    NotificationReadView,
    WebhookSubscriptionListCreateView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:notification_id>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("webhooks/", WebhookSubscriptionListCreateView.as_view(), name="webhook-subscriptions"),
]
