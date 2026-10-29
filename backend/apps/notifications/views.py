from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.serializers.notifications import (
    NotificationSerializer,
    WebhookSubscriptionCreateSerializer,
    WebhookSubscriptionCreatedSerializer,
    WebhookSubscriptionSerializer,
)
from api.v1.utils import raise_api_validation
from apps.notifications.models import Notification, WebhookSubscription
from services.notifications import NotificationService
from services.webhooks import WebhookService


class NotificationListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: NotificationSerializer(many=True)}, operation_id="notifications_list")
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient_type=request.user.account_type,
            recipient_id=request.user.pk,
        )
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationReadView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=None, responses={200: NotificationSerializer}, operation_id="notifications_mark_read")
    def post(self, request, notification_id):
        try:
            notification = NotificationService.mark_read(
                notification_id=notification_id,
                recipient_type=request.user.account_type,
                recipient_id=request.user.pk,
            )
        except Notification.DoesNotExist as exc:
            raise NotFound("Notification not found.") from exc
        return Response(NotificationSerializer(notification).data)


class WebhookSubscriptionListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: WebhookSubscriptionSerializer(many=True)}, operation_id="webhooks_list")
    def get(self, request):
        subscriptions = WebhookSubscription.objects.filter(
            owner_type=request.user.account_type,
            owner_id=request.user.pk,
        )
        return Response(WebhookSubscriptionSerializer(subscriptions, many=True).data)

    @extend_schema(request=WebhookSubscriptionCreateSerializer, responses={201: WebhookSubscriptionCreatedSerializer}, operation_id="webhooks_create")
    def post(self, request):
        if request.user.account_type not in WebhookSubscription.OwnerType.values:
            raise ValidationError({"detail": "This account type cannot register webhooks."})
        serializer = WebhookSubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            subscription = WebhookService.register(
                owner_type=request.user.account_type,
                owner_id=request.user.pk,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        response_data = WebhookSubscriptionSerializer(subscription).data
        response_data["secret"] = subscription.secret
        return Response(response_data, status=status.HTTP_201_CREATED)

    @extend_schema(request={"type": "object", "properties": {"subscription_id": {"type": "integer"}}, "required": ["subscription_id"]}, responses={204: None}, operation_id="webhooks_delete")
    def delete(self, request):
        subscription_id = request.data.get("subscription_id")
        if not subscription_id:
            raise ValidationError({"subscription_id": "This field is required."})
        subscription = get_object_or_404(
            WebhookSubscription,
            pk=subscription_id,
            owner_type=request.user.account_type,
            owner_id=request.user.pk,
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
