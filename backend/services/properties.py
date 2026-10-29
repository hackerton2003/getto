import os
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q
from django.utils.text import get_valid_filename

from apps.properties.models import Property, PropertyMedia, Room, RoomMedia


class PropertyService:
    OWNER_EDITABLE_FIELDS = {"name", "description", "street", "latitude", "longitude"}

    MAX_IMAGE_SIZE = 15 * 1024 * 1024  # 15 MB
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".mov"}

    @classmethod
    def validate_and_classify_media(cls, uploaded_file, requested_type=None):
        if not uploaded_file or not hasattr(uploaded_file, "chunks"):
            raise ValidationError({"file": "Upload a valid media file."})

        extension = os.path.splitext(uploaded_file.name)[1].lower()
        if extension not in cls.IMAGE_EXTENSIONS and extension not in cls.VIDEO_EXTENSIONS:
            raise ValidationError({
                "file": "Unsupported file extension. Allowed formats: JPG, PNG, WEBP, MP4, WEBM, MOV."
            })

        header = uploaded_file.read(32)
        uploaded_file.seek(0)

        detected_type = None
        if (
            header.startswith(b"\xff\xd8\xff")  # JPEG
            or header.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
            or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")  # WEBP
        ):
            detected_type = PropertyMedia.MediaType.IMAGE
        elif (
            header.startswith(b"\x1a\x45\xdf\xa3")  # WEBM
            or b"ftyp" in header  # MP4 / QuickTime
            or header[4:8] in (b"ftyp", b"moov", b"wide", b"mdat")
        ):
            detected_type = PropertyMedia.MediaType.VIDEO

        if detected_type is None:
            raise ValidationError({"file": "File signature does not match any supported image or video format."})

        if detected_type == PropertyMedia.MediaType.IMAGE:
            if extension not in cls.IMAGE_EXTENSIONS:
                raise ValidationError({"file": "File content is an image, but extension is invalid."})
            if uploaded_file.size <= 0 or uploaded_file.size > cls.MAX_IMAGE_SIZE:
                raise ValidationError({"file": f"Image file size must be between 1 byte and {cls.MAX_IMAGE_SIZE // (1024*1024)} MB."})
        elif detected_type == PropertyMedia.MediaType.VIDEO:
            if extension not in cls.VIDEO_EXTENSIONS:
                raise ValidationError({"file": "File content is a video, but extension is invalid."})
            if uploaded_file.size <= 0 or uploaded_file.size > cls.MAX_VIDEO_SIZE:
                raise ValidationError({"file": f"Video file size must be between 1 byte and {cls.MAX_VIDEO_SIZE // (1024*1024)} MB."})

        if requested_type and requested_type != detected_type:
            raise ValidationError({"type": f"Declared media type '{requested_type}' does not match uploaded file ({detected_type})."})

        return detected_type

    @classmethod
    def upload_property_media(cls, *, property_id, uploaded_file, media_type=None, owner_id=None, is_staff=False):
        classified_type = cls.validate_and_classify_media(uploaded_file, media_type)

        property_instance = Property.objects.filter(pk=property_id).first()
        if not property_instance:
            raise ValidationError({"property": "Property not found."})

        if not is_staff:
            if owner_id is None or property_instance.owner_id != owner_id:
                raise ValidationError({"property": "You do not have permission to manage media for this property."})

        safe_name = get_valid_filename(uploaded_file.name)[:150]
        storage_name = f"property-media/{property_id}/{uuid4().hex}-{safe_name}"
        stored_path = default_storage.save(storage_name, uploaded_file)

        try:
            return PropertyMedia.objects.create(
                property=property_instance,
                type=classified_type,
                file_path=stored_path,
            )
        except Exception:
            if default_storage.exists(stored_path):
                default_storage.delete(stored_path)
            raise

    @classmethod
    def delete_property_media(cls, *, media_id, owner_id=None, is_staff=False):
        with transaction.atomic():
            media = PropertyMedia.objects.select_for_update().select_related("property").filter(pk=media_id).first()
            if not media:
                raise ValidationError({"media": "Property media not found."})

            if not is_staff:
                if owner_id is None or media.property.owner_id != owner_id:
                    raise ValidationError({"media": "You do not have permission to delete this property media."})

            file_path = media.file_path
            media.delete()

        if file_path and default_storage.exists(file_path):
            default_storage.delete(file_path)

        return True

    @classmethod
    def upload_room_media(cls, *, room_id, uploaded_file, media_type=None, owner_id=None, is_staff=False):
        classified_type = cls.validate_and_classify_media(uploaded_file, media_type)

        room = Room.objects.select_related("property").filter(pk=room_id).first()
        if not room:
            raise ValidationError({"room": "Room not found."})

        if not is_staff:
            if owner_id is None or room.property.owner_id != owner_id:
                raise ValidationError({"room": "You do not have permission to manage media for this room."})

        safe_name = get_valid_filename(uploaded_file.name)[:150]
        storage_name = f"room-media/{room_id}/{uuid4().hex}-{safe_name}"
        stored_path = default_storage.save(storage_name, uploaded_file)

        try:
            return RoomMedia.objects.create(
                room=room,
                type=classified_type,
                file_path=stored_path,
            )
        except Exception:
            if default_storage.exists(stored_path):
                default_storage.delete(stored_path)
            raise

    @classmethod
    def delete_room_media(cls, *, media_id, owner_id=None, is_staff=False):
        with transaction.atomic():
            media = RoomMedia.objects.select_for_update().select_related("room", "room__property").filter(pk=media_id).first()
            if not media:
                raise ValidationError({"media": "Room media not found."})

            if not is_staff:
                if owner_id is None or media.room.property.owner_id != owner_id:
                    raise ValidationError({"media": "You do not have permission to delete this room media."})

            file_path = media.file_path
            media.delete()

        if file_path and default_storage.exists(file_path):
            default_storage.delete(file_path)

        return True

    @classmethod
    def update_owner_property(cls, *, property_id, owner_id, changes):
        unexpected_fields = set(changes) - cls.OWNER_EDITABLE_FIELDS
        if unexpected_fields:
            raise ValidationError({"fields": "One or more fields cannot be edited by the owner."})
        if not changes:
            raise ValidationError({"detail": "Provide at least one field to update."})

        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(
                pk=property_id,
                owner_id=owner_id,
            )
            for field_name, value in changes.items():
                setattr(property_instance, field_name, value)
            property_instance.verification_status = Property.VerificationStatus.PENDING
            property_instance.save(update_fields=(*changes.keys(), "verification_status", "updated_at"))
            return property_instance

    @staticmethod
    def _sync_locked_room_counts(property_instance):
        counts = Room.objects.filter(property=property_instance).aggregate(
            total=Count("id"),
            available=Count("id", filter=Q(status=Room.Status.AVAILABLE)),
        )
        property_instance.total_rooms = counts["total"]
        property_instance.available_rooms = counts["available"]
        property_instance.save(update_fields=("total_rooms", "available_rooms", "updated_at"))
        return property_instance

    @classmethod
    def sync_room_counts(cls, property_id):
        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            return cls._sync_locked_room_counts(property_instance)

    @classmethod
    def create_room(cls, *, property_id, **room_fields):
        if "property" in room_fields or "status" in room_fields:
            raise ValidationError("Set the property and initial room status through the service.")

        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            room = Room.objects.create(property=property_instance, **room_fields)
            cls._sync_locked_room_counts(property_instance)
            return room

    @classmethod
    def set_room_status(cls, *, room_id, status):
        if status not in Room.Status.values:
            raise ValidationError({"status": "Choose a valid room status."})

        property_id = Room.objects.values_list("property_id", flat=True).get(pk=room_id)
        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            room = Room.objects.select_for_update().get(pk=room_id, property=property_instance)
            if room.status != status:
                room.status = status
                room.save(update_fields=("status", "updated_at"))
                cls._sync_locked_room_counts(property_instance)
            return room