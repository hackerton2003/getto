from django.urls import path
from apps.payments.views import (
    PaymentDetailView,
    PaymentListCreateView,
    ReceiptListView,
)

urlpatterns = [
    path("payments/", PaymentListCreateView.as_view(), name="payment-list-create"),
    path("payments/<int:payment_id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("receipts/", ReceiptListView.as_view(), name="receipt-list"),
]
