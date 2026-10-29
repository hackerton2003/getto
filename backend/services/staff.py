from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.staff.models import Department, Permission, Role, Staff
from services.authentication import revoke_account_sessions


class StaffService:
    @staticmethod
    def _validate_role_grant(*, actor_id, role):
        actor = Staff.objects.select_related("role").get(pk=actor_id)
        if actor.status != Staff.Status.ACTIVE:
            raise ValidationError({"actor": "Only active staff can manage staff accounts."})
        actor_permissions = set(actor.role.permissions.values_list("name", flat=True))
        granted_permissions = set(role.permissions.values_list("name", flat=True))
        if not granted_permissions.issubset(actor_permissions):
            raise ValidationError({"role": "You cannot grant permissions that you do not hold."})
        return actor

    @staticmethod
    def create_staff(*, password, assigned_by_staff_id, **staff_data):
        if not password:
            raise ValidationError({"password": "A password is required."})
        validate_password(password)
        role = staff_data.get("role")
        if role is None:
            raise ValidationError({"role": "A staff role is required."})
        StaffService._validate_role_grant(actor_id=assigned_by_staff_id, role=role)
        staff_data["password"] = make_password(password)
        return Staff.objects.create(**staff_data)

    @classmethod
    def assign_role(cls, *, staff_id, role_id, assigned_by_staff_id):
        if staff_id == assigned_by_staff_id:
            raise ValidationError({"staff_id": "You cannot change your own role."})
        with transaction.atomic():
            actor = Staff.objects.select_for_update().select_related("role").get(pk=assigned_by_staff_id)
            target = Staff.objects.select_for_update().get(pk=staff_id)
            role = Role.objects.select_for_update().get(pk=role_id)
            if actor.status != Staff.Status.ACTIVE:
                raise ValidationError({"actor": "Only active staff can manage staff accounts."})
            actor_permissions = set(actor.role.permissions.values_list("name", flat=True))
            granted_permissions = set(role.permissions.values_list("name", flat=True))
            if not granted_permissions.issubset(actor_permissions):
                raise ValidationError({"role": "You cannot grant permissions that you do not hold."})
            target.role = role
            target.save(update_fields=("role", "updated_at"))
            return target

    @staticmethod
    @transaction.atomic
    def replace_role_permissions(*, role_id, permission_ids):
        role = Role.objects.select_for_update().get(pk=role_id)
        unique_ids = set(permission_ids)
        found_ids = set(Permission.objects.filter(pk__in=unique_ids).values_list("pk", flat=True))
        if found_ids != unique_ids:
            raise ValidationError({"permission_ids": "One or more permissions do not exist."})
        role.permissions.set(unique_ids)
        return role

    @staticmethod
    @transaction.atomic
    def assign_department_head(*, department_id, staff_id):
        department = Department.objects.select_for_update().get(pk=department_id)
        staff = Staff.objects.select_for_update().get(pk=staff_id)
        if staff.department_id != department.pk:
            raise ValidationError({"staff_id": "Department head must belong to this department."})
        if staff.status != Staff.Status.ACTIVE:
            raise ValidationError({"staff_id": "Department head must be active."})
        department.hod = staff
        department.save(update_fields=("hod",))
        return department

    @staticmethod
    def set_status(*, staff_id, status):
        if status not in Staff.Status.values:
            raise ValidationError({"status": "Choose a valid staff status."})
        staff = Staff.objects.get(pk=staff_id)
        staff.status = status
        staff.save(update_fields=("status", "updated_at"))
        if status != Staff.Status.ACTIVE:
            revoke_account_sessions(user_type="staff", user_id=staff.pk)
        return staff