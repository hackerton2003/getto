from django.contrib import admin
from apps.universities.models import Campus, University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "district")
    search_fields = ("name",)


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "university", "ward")
    list_filter = ("university",)
    search_fields = ("name", "university__name")
