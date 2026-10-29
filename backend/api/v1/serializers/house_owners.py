from uuid import uuid4
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from rest_framework import serializers

from apps.house_owners.models import AccommodationOwner
from api.v1.serializers.common import PasswordHashingModelSerializer


class AccommodationOwnerSerializer(PasswordHashingModelSerializer):
    class Meta:
        model = AccommodationOwner
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}


class OwnerProfileSerializer(serializers.ModelSerializer):
    photo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    photo_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = AccommodationOwner
        fields = (
            "id",
            "firstname",
            "lastname",
            "photo",
            "photo_file",
            "phone",
            "email",
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

    def update(self, instance, validated_data):
        photo_file = validated_data.pop("photo_file", None)
        if photo_file:
            storage_name = f"profiles/owners/{uuid4().hex}_{get_valid_filename(photo_file.name)}"
            stored_path = default_storage.save(storage_name, photo_file)
            validated_data["photo"] = stored_path
        return super().update(instance, validated_data)