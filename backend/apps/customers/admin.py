from django.contrib import admin
from apps.customers.models import Customer, CustomerPreference, Favourite, Report, Review


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "firstname",
        "lastname",
        "email",
        "phone",
        "university",
        "campus",
        "status",
    )
    list_filter = ("status", "university")
    search_fields = ("firstname", "lastname", "email", "phone")


@admin.register(CustomerPreference)
class CustomerPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "region",
        "district",
        "ward",
        "preferred_room_type",
        "min_price",
        "max_price",
    )
    search_fields = ("customer__firstname", "customer__lastname", "customer__email")


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "property", "created_at")
    list_filter = ("created_at",)
    search_fields = ("customer__email", "property__name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "property", "rating", "status", "reviewed_by_staff", "created_at")
    list_filter = ("status", "rating", "created_at")
    search_fields = ("customer__email", "property__name", "comment")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "property", "reason", "status", "reviewed_by_staff", "created_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("customer__email", "property__name", "description")
