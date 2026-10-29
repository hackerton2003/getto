from rest_framework import serializers

from apps.bookings.models import Booking
from apps.payments.models import Payment, Receipt


class PaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    payment_method = serializers.CharField(max_length=50)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = "__all__"