from django.urls import path
from apps.bookings.views import (
    BookingCancelView,
    BookingDecisionView,
    BookingDetailView,
    BookingListCreateView,
    StaffBookingExpireStaleView,
)

urlpatterns = [
    path("", BookingListCreateView.as_view(), name="booking-create"),
    path("<int:booking_id>/", BookingDetailView.as_view(), name="booking-detail"),
    path("<int:booking_id>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("<int:booking_id>/<str:decision>/", BookingDecisionView.as_view(), name="booking-decision"),
    path("expire-stale/", StaffBookingExpireStaleView.as_view(), name="staff-booking-expire-stale"),
]
