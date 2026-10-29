from rest_framework import serializers

from apps.bookings.models import Booking
from apps.properties.models import Room


class BookingCreateRequestSerializer(serializers.Serializer):
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
    )


class StaleBookingExpirySerializer(serializers.Serializer):
    hours = serializers.IntegerField(required=False, min_value=1, default=24)
    limit = serializers.IntegerField(required=False, min_value=1, allow_null=True)


class StaleBookingExpiryResponseSerializer(serializers.Serializer):
    expired_count = serializers.IntegerField()
    expired_booking_ids = serializers.ListField(child=serializers.IntegerField())


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"
