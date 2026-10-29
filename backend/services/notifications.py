from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import logging

from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def send(*, recipient_type, recipient_id, title, message, channel=Notification.Channel.IN_SYSTEM):
        if recipient_type not in Notification.RecipientType.values:
            raise ValidationError({"recipient_type": "Choose a valid recipient type."})
        if channel not in Notification.Channel.values:
            raise ValidationError({"channel": "Choose a valid notification channel."})
        if channel == Notification.Channel.SMS:
            raise ValidationError({"channel": "SMS delivery is unavailable until an SMS provider is configured."})
        recipient = None
        if channel == Notification.Channel.EMAIL:
            recipient = NotificationService._recipient_email(recipient_type, recipient_id)
            if not recipient:
                raise ValidationError({"recipient": "Recipient does not have an email address."})
        notification = Notification.objects.create(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            title=title,
            message=message,
            channel=channel,
            created_at=timezone.now(),
        )
        if channel == Notification.Channel.EMAIL:
            transaction.on_commit(lambda: NotificationService._deliver_email(
                recipient, title, message,
            ))
        return notification

    @staticmethod
    def _recipient_email(recipient_type, recipient_id):
        from apps.customers.models import Customer
        from apps.house_owners.models import AccommodationOwner
        from apps.staff.models import Staff

        models = {
            Notification.RecipientType.CUSTOMER: Customer,
            Notification.RecipientType.OWNER: AccommodationOwner,
            Notification.RecipientType.STAFF: Staff,
        }
        model = models.get(recipient_type)
        return model.objects.filter(pk=recipient_id).values_list("email", flat=True).first() if model else None

    @staticmethod
    def _deliver_email(recipient, subject, message):
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
        except Exception:
            logger.exception("Could not deliver notification email to %s", recipient)

    @staticmethod
    def mark_read(*, notification_id, recipient_type, recipient_id):
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(
                pk=notification_id,
                recipient_type=recipient_type,
                recipient_id=recipient_id,
            )
            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=("is_read",))
            return notification
