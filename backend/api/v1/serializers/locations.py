from rest_framework import serializers

from apps.locations.models import District, Region, Street, Ward


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = "__all__"


class StreetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Street
        fields = "__all__"