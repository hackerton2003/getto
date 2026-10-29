from django.contrib import admin
from apps.locations.models import District, Region, Street, Ward


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "region")
    list_filter = ("region",)
    search_fields = ("name", "region__name")


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "district")
    list_filter = ("district__region",)
    search_fields = ("name", "district__name")


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "ward")
    search_fields = ("name", "ward__name")
