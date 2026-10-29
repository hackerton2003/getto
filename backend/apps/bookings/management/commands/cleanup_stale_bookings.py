from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

from apps.bookings.models import Booking
from services.bookings import BookingService


class Command(BaseCommand):
    help = (
        "Clean up stale pending bookings that have not been confirmed/paid "
        "within the configured timeframe, restoring reserved rooms to available."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Number of hours before a pending booking is considered stale (default: 24).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of stale bookings to expire in this run.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the cleanup without modifying booking or room status.",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        limit = options["limit"]
        dry_run = options["dry_run"]
        if hours < 1:
            raise CommandError("--hours must be a positive integer.")
        if limit is not None and limit < 1:
            raise CommandError("--limit must be a positive integer.")

        cutoff = timezone.now() - timedelta(hours=hours)
        stale_qs = Booking.objects.filter(
            status=Booking.Status.PENDING,
            created_at__lte=cutoff,
        ).select_related("room", "customer").order_by("created_at")

        if limit:
            stale_bookings = list(stale_qs[:limit])
        else:
            stale_bookings = list(stale_qs)

        count = len(stale_bookings)
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"No stale pending bookings older than {hours} hours found."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Found {count} stale pending booking(s) older than {hours}h to expire:"
                )
            )
            for b in stale_bookings:
                self.stdout.write(f"  - Booking #{b.id} ({b.reference_no}), room #{b.room_id}, created {b.created_at}")
            return

        expired = BookingService.expire_stale_bookings(expiry_hours=hours, limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully expired {len(expired)} stale booking(s) and restored room availabilities."
            )
        )
