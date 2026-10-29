from django.db import models

# Create your models here.


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    permissions = models.ManyToManyField(
        "Permission",
        through="RolePermission",
        related_name="roles",
    )

    class Meta:
        db_table = "roles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "permissions"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class Rank(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "ranks"
        ordering = ["name"]

    def __str__(self):
        return self.name





class Department(models.Model):
    name = models.CharField(max_length=100)
    hod = models.ForeignKey(
        "Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_department",
    )

    class Meta:
        db_table = "departments"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Staff(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DEACTIVATED = "deactivated", "Deactivated"

    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    photo = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    password = models.CharField(max_length=255)

    branch = models.CharField(max_length=100)

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="staff_members",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
    )

    rank = models.ForeignKey(
        Rank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff"
        ordering = ["firstname", "lastname"]

    def __str__(self):
        return f"{self.firstname} {self.lastname}"
