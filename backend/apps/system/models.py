from django.db import models

# Create your models here.

class SystemSettings(models.Model):
    class PanelTheme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    class EnduserTheme(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    company_name = models.CharField(
        max_length=150,
    )
    logo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    slogan = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    ads = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    address = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    location = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )
    service_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
    )
    panel_theme = models.CharField(
        max_length=10,
        choices=PanelTheme.choices,
        default=PanelTheme.LIGHT,
    )
    enduser_theme = models.CharField(
        max_length=10,
        choices=EnduserTheme.choices,
        default=EnduserTheme.LIGHT,
    )

    class Meta:
        db_table = "system_settings"

    def __str__(self):
        return self.company_name
        
        
        
class AuditLog(models.Model):
    class ActorType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        OWNER = "owner", "Owner"
        STAFF = "staff", "Staff"
        SYSTEM = "system", "System"

    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
    )
    actor_id = models.BigIntegerField(
        null=True,
        blank=True,
    )
    actor_lastname = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    actor_phone = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )
    action = models.CharField(
        max_length=150,
    )
    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField()

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor_type} - {self.action}"
        
        
        
class VisitorLog(models.Model):
    id = models.BigAutoField(
        primary_key=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    location_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
    )
    visited_at = models.DateTimeField()

    class Meta:
        db_table = "visitor_logs"
        ordering = ["-visited_at"]

    def __str__(self):
        return f"{self.ip_address} - {self.location_name}"
