from rest_framework import serializers

from apps.staff.models import Department, Permission, Rank, Role, RolePermission, Staff
from api.v1.serializers.common import PasswordHashingModelSerializer


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = "__all__"


class RankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rank
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class StaffSerializer(PasswordHashingModelSerializer):
    class Meta:
        model = Staff
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}


class StaffCreateSerializer(serializers.Serializer):
    firstname = serializers.CharField(max_length=100)
    lastname = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    branch = serializers.CharField(max_length=100)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    rank = serializers.PrimaryKeyRelatedField(
        queryset=Rank.objects.all(), required=False, allow_null=True
    )


class StaffRoleAssignmentSerializer(serializers.Serializer):
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())


class StaffStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Staff.Status.choices)