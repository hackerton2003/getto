from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.locations.models import Street
from apps.properties.models import (
    Property,
    PropertyMedia,
    Room,
    RoomMedia,
    Verification,
    VerificationDocument,
)


class OwnerPropertyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)
    street = serializers.PrimaryKeyRelatedField(queryset=Street.objects.all())
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)


class OwnerPropertyUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    street = serializers.PrimaryKeyRelatedField(queryset=Street.objects.all(), required=False)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False)


class OwnerRoomCreateSerializer(serializers.Serializer):
    room_type = serializers.CharField(max_length=100)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    capacity = serializers.IntegerField(min_value=1)
    length_m = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    width_m = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    area_sqm = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    facilities = serializers.CharField(required=False, allow_blank=True)
    security_info = serializers.CharField(required=False, allow_blank=True)


class PropertyMediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    type = serializers.ChoiceField(choices=PropertyMedia.MediaType.choices, required=False)


class RoomMediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    type = serializers.ChoiceField(choices=RoomMedia.MediaType.choices, required=False)


class PropertyMediaCreateSerializer(serializers.Serializer):
    property_id = serializers.IntegerField()
    file = serializers.FileField(allow_empty_file=False)
    type = serializers.ChoiceField(choices=PropertyMedia.MediaType.choices, required=False)


class RoomMediaCreateSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    file = serializers.FileField(allow_empty_file=False)
    type = serializers.ChoiceField(choices=RoomMedia.MediaType.choices, required=False)


class VerificationDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class VerificationSubmitSerializer(VerificationDocumentUploadSerializer):
    pass


class VerificationDocumentCreateSerializer(VerificationDocumentUploadSerializer):
    pass


class VerificationReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=255, required=False, allow_blank=True)


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = "__all__"


class PropertyMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyMedia
        fields = ("id", "property", "type", "file_path", "file_url", "created_at")
        read_only_fields = ("id", "created_at", "file_url")

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj):
        if not obj.file_path:
            return None
        try:
            url = default_storage.url(obj.file_path)
        except (NotImplementedError, ValueError):
            url = f"{settings.MEDIA_URL}{obj.file_path}"
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class RoomMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = RoomMedia
        fields = ("id", "room", "type", "file_path", "file_url", "created_at")
        read_only_fields = ("id", "created_at", "file_url")

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj):
        if not obj.file_path:
            return None
        try:
            url = default_storage.url(obj.file_path)
        except (NotImplementedError, ValueError):
            url = f"{settings.MEDIA_URL}{obj.file_path}"
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class VerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Verification
        fields = "__all__"


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = "__all__"
