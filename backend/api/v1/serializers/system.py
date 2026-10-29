from rest_framework import serializers

from apps.system.models import AuditLog, SystemSettings, VisitorLog


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = "__all__"


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class VisitorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorLog
        fields = "__all__"