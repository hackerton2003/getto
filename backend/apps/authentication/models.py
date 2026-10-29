from django.db import models

# Create your models here.

class PasswordReset(models.Model):
    class UserType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        OWNER = "owner", "Accommodation Owner"
        STAFF = "staff", "Staff"

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
    )
    user_id = models.BigIntegerField()
    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_resets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_type} - {self.user_id}"


class AuthSession(models.Model):
    class UserType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        OWNER = "owner", "Accommodation Owner"
        STAFF = "staff", "Staff"

    user_type = models.CharField(max_length=20, choices=UserType.choices)
    user_id = models.BigIntegerField()
    access_token_id = models.CharField(max_length=64)
    refresh_token_hash = models.CharField(max_length=64, unique=True)
    refresh_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_sessions"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=("user_type", "user_id", "revoked_at"))]

    def __str__(self):
        return f"{self.user_type} - {self.user_id}"
