from django.contrib import admin
from apps.staff.models import Department, Permission, Rank, Role, RolePermission, Staff


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "role", "permission")
    list_filter = ("role",)


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "hod")
    search_fields = ("name",)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "firstname",
        "lastname",
        "email",
        "phone",
        "role",
        "department",
        "rank",
        "status",
    )
    list_filter = ("status", "role", "department")
    search_fields = ("firstname", "lastname", "email", "phone")
