from django.contrib import admin
from apps.house_owners.models import AccommodationOwner


@admin.register(AccommodationOwner)
class AccommodationOwnerAdmin(admin.ModelAdmin):
    list_display = ("id", "firstname", "lastname", "email", "phone", "status")
    list_filter = ("status",)
    search_fields = ("firstname", "lastname", "email", "phone")
