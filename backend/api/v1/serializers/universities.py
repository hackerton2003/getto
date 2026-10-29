from rest_framework import serializers

from apps.universities.models import Campus, University


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = "__all__"


class CampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = "__all__"