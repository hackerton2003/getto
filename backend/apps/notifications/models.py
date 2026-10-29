from django.db import models

# Create your models here.

class Notification(models.Model):
    class RecipientType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        OWNER = "owner", "Owner"
        STAFF = "staff", "Staff"

    class Channel(models.TextChoices):
        IN_SYSTEM = "in_system", "In System"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    recipient_type = models.CharField(
        max_length=20,
        choices=RecipientType.choices,
    )
    recipient_id = models.BigIntegerField()
    title = models.CharField(
        max_length=150,
    )
    message = models.TextField()
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.IN_SYSTEM,
    )
    is_read = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField()

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class WebhookSubscription(models.Model):
    class OwnerType(models.TextChoices):
        OWNER = "owner", "Accommodation Owner"
        STAFF = "staff", "Staff"

    owner_type = models.CharField(max_length=20, choices=OwnerType.choices)
    owner_id = models.BigIntegerField()
    target_url = models.URLField(max_length=500)
    secret = models.CharField(max_length=128)
    event_types = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhook_subscriptions"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=("owner_type", "owner_id", "active"))]

    def __str__(self):
        return f"{self.owner_type}:{self.owner_id} -> {self.target_url}"


class WebhookDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    subscription = models.ForeignKey(
        WebhookSubscription,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    last_http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "webhook_deliveries"
        ordering = ["next_attempt_at", "created_at"]
        indexes = [models.Index(fields=("status", "next_attempt_at"))]

    def __str__(self):
        return f"{self.event_type} - {self.status}"
