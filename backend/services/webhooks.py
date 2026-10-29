import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import WebhookDelivery, WebhookSubscription


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class WebhookService:
    EVENT_TYPES = {
        "verification.submitted",
        "verification.approved",
        "verification.rejected",
        "verification.document.uploaded",
    }
    MAX_ATTEMPTS = 8
    TIMEOUT_SECONDS = 8
    MAX_RESPONSE_LENGTH = 500

    @classmethod
    def validate_target_url(cls, target_url):
        parsed = urllib.parse.urlsplit(target_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValidationError({"target_url": "Webhook URLs must be HTTPS URLs without credentials or fragments."})
        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal")):
            raise ValidationError({"target_url": "Webhook URL must use a public hostname."})
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValidationError({"target_url": "Webhook URL must not target a private or reserved IP address."})
        return target_url

    @classmethod
    def register(cls, *, owner_type, owner_id, target_url, event_types):
        if owner_type not in WebhookSubscription.OwnerType.values:
            raise ValidationError({"owner_type": "Unsupported webhook owner type."})
        cls.validate_target_url(target_url)
        if not event_types or not isinstance(event_types, list):
            raise ValidationError({"event_types": "Select at least one event type."})
        invalid_events = set(event_types) - cls.EVENT_TYPES
        if invalid_events:
            raise ValidationError({"event_types": f"Unsupported events: {', '.join(sorted(invalid_events))}."})
        return WebhookSubscription.objects.create(
            owner_type=owner_type,
            owner_id=owner_id,
            target_url=target_url,
            secret=secrets.token_urlsafe(32),
            event_types=sorted(set(event_types)),
        )

    @classmethod
    def publish(cls, *, owner_type, owner_id, event_type, data):
        if event_type not in cls.EVENT_TYPES:
            raise ValidationError({"event_type": "Unsupported webhook event."})
        subscriptions = WebhookSubscription.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            active=True,
        )
        now = timezone.now()
        created = []
        event_id = str(uuid.uuid4())
        payload = {
            "id": event_id,
            "type": event_type,
            "occurred_at": now.isoformat(),
            "data": data,
        }
        with transaction.atomic():
            for subscription in subscriptions:
                if event_type in subscription.event_types:
                    created.append(WebhookDelivery.objects.create(
                        subscription=subscription,
                        event_type=event_type,
                        payload=payload,
                        next_attempt_at=now,
                    ))
        return created

    @staticmethod
    def _assert_public_destination(hostname):
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError("Webhook hostname could not be resolved.") from exc
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("Webhook hostname resolves to a private or reserved IP address.")

    @classmethod
    def _post_delivery(cls, subscription, payload):
        parsed = urllib.parse.urlsplit(subscription.target_url)
        cls._assert_public_destination(parsed.hostname)
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        timestamp = str(int(timezone.now().timestamp()))
        signed_content = timestamp.encode("ascii") + b"." + body
        signature = hmac.new(subscription.secret.encode("utf-8"), signed_content, hashlib.sha256).hexdigest()
        request = urllib.request.Request(
            subscription.target_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Getto-Webhooks/1.0",
                "X-Getto-Event": payload["type"],
                "X-Getto-Delivery": payload["id"],
                "X-Getto-Timestamp": timestamp,
                "X-Getto-Signature": f"sha256={signature}",
            },
            method="POST",
        )
        opener = urllib.request.build_opener(_NoRedirectHandler)
        try:
            with opener.open(request, timeout=cls.TIMEOUT_SECONDS) as response:
                response.read(cls.MAX_RESPONSE_LENGTH)
                return response.status, None
        except urllib.error.HTTPError as exc:
            return exc.code, f"HTTP {exc.code}: {exc.reason}"[:cls.MAX_RESPONSE_LENGTH]
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return None, str(exc)[:cls.MAX_RESPONSE_LENGTH]

    @classmethod
    def deliver_one(cls, delivery_id):
        now = timezone.now()
        with transaction.atomic():
            delivery = WebhookDelivery.objects.select_for_update().select_related("subscription").get(pk=delivery_id)
            if delivery.status != WebhookDelivery.Status.PENDING or delivery.next_attempt_at > now:
                return delivery
            if not delivery.subscription.active:
                delivery.status = WebhookDelivery.Status.FAILED
                delivery.last_error = "Webhook subscription is inactive."
                delivery.save(update_fields=("status", "last_error"))
                return delivery
            delivery.attempts += 1
            attempt_number = delivery.attempts
            delivery.next_attempt_at = now + timedelta(seconds=cls.TIMEOUT_SECONDS + 1)
            delivery.save(update_fields=("attempts", "next_attempt_at"))
            subscription = delivery.subscription
            payload = delivery.payload

        http_status, error = cls._post_delivery(subscription, payload)
        with transaction.atomic():
            delivery = WebhookDelivery.objects.select_for_update().get(pk=delivery_id)
            if delivery.status != WebhookDelivery.Status.PENDING or delivery.attempts != attempt_number:
                return delivery
            delivery.last_http_status = http_status
            if http_status is not None and 200 <= http_status < 300:
                delivery.status = WebhookDelivery.Status.DELIVERED
                delivery.delivered_at = timezone.now()
                delivery.last_error = ""
                delivery.save(update_fields=("status", "delivered_at", "last_http_status", "last_error"))
                return delivery

            delivery.last_error = error or f"Unexpected HTTP status {http_status}."
            if attempt_number >= cls.MAX_ATTEMPTS:
                delivery.status = WebhookDelivery.Status.FAILED
                delivery.save(update_fields=("status", "last_http_status", "last_error"))
                return delivery

            delay_seconds = min(60 * (2 ** (attempt_number - 1)), 3600)
            delivery.next_attempt_at = timezone.now() + timedelta(seconds=delay_seconds)
            delivery.save(update_fields=("next_attempt_at", "last_http_status", "last_error"))
            return delivery

    @classmethod
    def deliver_due(cls, *, limit=100):
        ids = list(WebhookDelivery.objects.filter(
            status=WebhookDelivery.Status.PENDING,
            next_attempt_at__lte=timezone.now(),
        ).order_by("next_attempt_at").values_list("pk", flat=True)[:limit])
        return [cls.deliver_one(delivery_id) for delivery_id in ids]