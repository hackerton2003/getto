from django.core.management.base import BaseCommand

from services.webhooks import WebhookService


class Command(BaseCommand):
    help = "Deliver due webhook callbacks and schedule retries for failures."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 1000:
            self.stderr.write("--limit must be between 1 and 1000")
            return

        deliveries = WebhookService.deliver_due(limit=limit)
        delivered = sum(delivery.status == "delivered" for delivery in deliveries)
        pending = sum(delivery.status == "pending" for delivery in deliveries)
        failed = sum(delivery.status == "failed" for delivery in deliveries)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(deliveries)} callbacks: {delivered} delivered, "
                f"{pending} pending retry, {failed} failed."
            )
        )
