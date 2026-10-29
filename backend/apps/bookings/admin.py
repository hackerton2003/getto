from django.contrib import admin
from apps.bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference_no",
        "customer",
        "room",
        "status",
        "request_date",
        "confirmed_at",
        "cancelled_at",
    )
    list_filter = ("status", "request_date")
    search_fields = ("reference_no", "customer__email", "room__property__name")
