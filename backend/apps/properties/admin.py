from django.contrib import admin
from apps.properties.models import (
    Property,
    PropertyMedia,
    Room,
    RoomMedia,
    Verification,
    VerificationDocument,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "owner",
        "street",
        "total_rooms",
        "available_rooms",
        "verification_status",
        "created_at",
    )
    list_filter = ("verification_status",)
    search_fields = ("name", "description", "owner__firstname", "owner__lastname")


@admin.register(PropertyMedia)
class PropertyMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "type", "file_path", "created_at")
    list_filter = ("type",)
    search_fields = ("property__name", "file_path")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "room_type", "price", "capacity", "status")
    list_filter = ("status", "room_type")
    search_fields = ("room_type", "property__name")


@admin.register(RoomMedia)
class RoomMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "type", "file_path", "created_at")
    list_filter = ("type",)
    search_fields = ("room__room_type", "file_path")


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "status",
        "reviewed_by_staff",
        "submitted_at",
        "reviewed_at",
    )
    list_filter = ("status",)
    search_fields = ("property__name",)


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "verification",
        "original_filename",
        "content_type",
        "file_size",
        "sha256",
    )
    search_fields = ("original_filename", "verification__property__name")
