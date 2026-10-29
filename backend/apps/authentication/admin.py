from django.contrib import admin
from apps.authentication.models import AuthSession, PasswordReset


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ("id", "user_type", "user_id", "token_hash", "expires_at", "created_at")
    list_filter = ("user_type",)
    search_fields = ("user_id", "token_hash")
    readonly_fields = ("token_hash", "created_at")


@admin.register(AuthSession)
class AuthSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_type",
        "user_id",
        "access_token_id",
        "refresh_expires_at",
        "revoked_at",
        "created_at",
    )
    list_filter = ("user_type", "revoked_at")
    search_fields = ("user_id", "access_token_id")
    readonly_fields = ("refresh_token_hash", "created_at")
