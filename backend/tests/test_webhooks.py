import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from api.v1.authentication import create_access_token
from apps.house_owners.models import AccommodationOwner
from apps.notifications.models import WebhookDelivery, WebhookSubscription
from services.webhooks import WebhookService


class WebhookWorkflowTests(TestCase):
    def setUp(self):
        self.owner = AccommodationOwner.objects.create(
            firstname="Webhook",
            lastname="Owner",
            phone="+255733333331",
            email="webhook-owner@example.test",
            password="unused-test-password",
        )
        self.other_owner = AccommodationOwner.objects.create(
            firstname="Other",
            lastname="Owner",
            phone="+255733333332",
            email="other-webhook-owner@example.test",
            password="unused-test-password",
        )
        self.client = self.client_for(self.owner)
        self.other_client = self.client_for(self.other_owner)

    @staticmethod
    def client_for(owner):
        client = APIClient()
        token = create_access_token(owner, "owner")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def test_register_returns_secret_once_and_subscription_is_owner_scoped(self):
        url = reverse("webhook-subscriptions")
        response = self.client.post(
            url,
            {
                "target_url": "https://hooks.example.com/getto",
                "event_types": ["verification.approved", "verification.rejected"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("secret", response.data)
        secret = response.data["secret"]
        subscription = WebhookSubscription.objects.get(owner_id=self.owner.pk)
        self.assertEqual(subscription.secret, secret)

        listed = self.client.get(url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertNotIn("secret", listed.data[0])
        self.assertEqual(self.other_client.get(url).data, [])

    def test_registration_rejects_insecure_and_private_targets(self):
        for target_url in ("http://hooks.example.com/", "https://127.0.0.1/hook", "https://localhost/hook"):
            with self.subTest(target_url=target_url):
                response = self.client.post(
                    reverse("webhook-subscriptions"),
                    {"target_url": target_url, "event_types": ["verification.approved"]},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookSubscription.objects.count(), 0)

    def test_publish_queues_only_subscribed_events_for_owner(self):
        WebhookService.register(
            owner_type="owner",
            owner_id=self.owner.pk,
            target_url="https://hooks.example.com/getto",
            event_types=["verification.approved"],
        )
        created = WebhookService.publish(
            owner_type="owner",
            owner_id=self.owner.pk,
            event_type="verification.approved",
            data={"verification_id": 91},
        )
        ignored = WebhookService.publish(
            owner_type="owner",
            owner_id=self.owner.pk,
            event_type="verification.rejected",
            data={"verification_id": 92},
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(ignored, [])
        self.assertEqual(WebhookDelivery.objects.count(), 1)
        self.assertEqual(created[0].payload["data"]["verification_id"], 91)

    def test_delivery_records_success_and_retries_failure_with_backoff(self):
        subscription = WebhookService.register(
            owner_type="owner",
            owner_id=self.owner.pk,
            target_url="https://hooks.example.com/getto",
            event_types=["verification.approved"],
        )
        delivery = WebhookService.publish(
            owner_type="owner",
            owner_id=self.owner.pk,
            event_type="verification.approved",
            data={"verification_id": 93},
        )[0]

        with patch.object(WebhookService, "_post_delivery", return_value=(204, None)):
            delivered = WebhookService.deliver_one(delivery.pk)
        self.assertEqual(delivered.status, WebhookDelivery.Status.DELIVERED)
        self.assertEqual(delivered.attempts, 1)
        self.assertIsNotNone(delivered.delivered_at)

        retry_delivery = WebhookDelivery.objects.create(
            subscription=subscription,
            event_type="verification.approved",
            payload={"id": "retry-1", "type": "verification.approved", "data": {}},
            next_attempt_at=timezone.now() - timedelta(seconds=1),
        )
        with patch.object(WebhookService, "_post_delivery", return_value=(503, "Service unavailable")):
            pending = WebhookService.deliver_one(retry_delivery.pk)
        self.assertEqual(pending.status, WebhookDelivery.Status.PENDING)
        self.assertEqual(pending.last_http_status, 503)
        self.assertGreater(pending.next_attempt_at, timezone.now())

    def test_delivery_signature_matches_timestamp_and_payload(self):
        subscription = WebhookService.register(
            owner_type="owner",
            owner_id=self.owner.pk,
            target_url="https://hooks.example.com/getto",
            event_types=["verification.approved"],
        )
        payload = {
            "id": "delivery-signature-test",
            "type": "verification.approved",
            "data": {"verification_id": 104},
        }
        response = MagicMock()
        response.status = 202
        response.__enter__.return_value = response
        response.read.return_value = b""
        opener = MagicMock()
        opener.open.return_value = response

        with patch.object(WebhookService, "_assert_public_destination"), patch(
            "services.webhooks.urllib.request.build_opener",
            return_value=opener,
        ):
            status_code, error = WebhookService._post_delivery(subscription, payload)

        self.assertEqual(status_code, 202)
        self.assertIsNone(error)
        request = opener.open.call_args.args[0]
        headers = {name.lower(): value for name, value in request.headers.items()}
        timestamp = headers["x-getto-timestamp"]
        expected_signature = hmac.new(
            subscription.secret.encode("utf-8"),
            timestamp.encode("ascii") + b"." + request.data,
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(headers["x-getto-signature"], f"sha256={expected_signature}")
        self.assertEqual(json.loads(request.data), payload)
