from uuid import uuid4
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from rest_framework import serializers

from apps.customers.models import Customer, CustomerPreference, Favourite, Report, Review
from apps.locations.models import District, Region, Ward
from apps.properties.models import Property
from api.v1.serializers.common import PasswordHashingModelSerializer


class CustomerProfileSerializer(serializers.ModelSerializer):
    photo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    photo_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Customer
        fields = (
            "id",
            "firstname",
            "lastname",
            "photo",
            "photo_file",
            "phone",
            "email",
            "university",
            "campus",
            "admission_info",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")

    def to_internal_value(self, data):
        if hasattr(data, "get"):
            photo_val = data.get("photo")
            if photo_val and hasattr(photo_val, "read"):
                mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
                mutable_data["photo_file"] = photo_val
                mutable_data.pop("photo", None)
                data = mutable_data
        return super().to_internal_value(data)

    def validate(self, attrs):
        university = attrs.get("university", getattr(self.instance, "university", None))
        campus = attrs.get("campus", getattr(self.instance, "campus", None))
        if campus and university and campus.university_id != university.pk:
            raise serializers.ValidationError({"campus": "Campus must belong to the selected university."})
        return attrs

    def update(self, instance, validated_data):
        photo_file = validated_data.pop("photo_file", None)
        if photo_file:
            storage_name = f"profiles/customers/{uuid4().hex}_{get_valid_filename(photo_file.name)}"
            stored_path = default_storage.save(storage_name, photo_file)
            validated_data["photo"] = stored_path
        return super().update(instance, validated_data)


class CustomerPreferencesInputSerializer(serializers.Serializer):
    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), required=False, allow_null=True
    )
    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), required=False, allow_null=True
    )
    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(), required=False, allow_null=True
    )
    preferred_room_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class FavouriteCreateSerializer(serializers.Serializer):
    property_id = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())


class ReviewCreateSerializer(serializers.Serializer):
    property_id = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)


class ReviewUpdateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one field to update.")
        return attrs


class ReportReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        (Report.Status.REVIEWED, "Reviewed"),
        (Report.Status.DISMISSED, "Dismissed"),
    ))
    resolution_note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ReviewModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        (Review.Status.APPROVED, "Approved"),
        (Review.Status.REJECTED, "Rejected"),
    ))


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"


class ReportCreateSerializer(serializers.Serializer):
    property_id = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    reason = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class CustomerSerializer(PasswordHashingModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}


class CustomerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPreference
        fields = "__all__"


class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourite
        fields = "__all__"
        read_only_fields = ("created_at",)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ("created_at",)
