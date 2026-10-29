from django.contrib import admin
from apps.payments.models import Payment, Receipt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_reference",
        "booking",
        "customer",
        "rental_amount",
        "service_fee",
        "total_amount",
        "payment_method",
        "status",
        "paid_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("payment_reference", "customer__email")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt_number", "payment", "issued_at")
    search_fields = ("receipt_number", "payment__payment_reference")
