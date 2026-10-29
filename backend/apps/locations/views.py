from api.v1.serializers.locations import DistrictSerializer, RegionSerializer, StreetSerializer, WardSerializer
from api.v1.utils import PublicReadOnlyViewSet
from apps.locations.models import District, Region, Street, Ward


class RegionViewSet(PublicReadOnlyViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer


class DistrictViewSet(PublicReadOnlyViewSet):
    serializer_class = DistrictSerializer

    def get_queryset(self):
        queryset = District.objects.select_related("region")
        region_id = self.request.query_params.get("region_id")
        return queryset.filter(region_id=region_id) if region_id else queryset


class WardViewSet(PublicReadOnlyViewSet):
    serializer_class = WardSerializer

    def get_queryset(self):
        queryset = Ward.objects.select_related("district", "district__region")
        district_id = self.request.query_params.get("district_id")
        return queryset.filter(district_id=district_id) if district_id else queryset


class StreetViewSet(PublicReadOnlyViewSet):
    serializer_class = StreetSerializer

    def get_queryset(self):
        queryset = Street.objects.select_related("ward", "ward__district")
        ward_id = self.request.query_params.get("ward_id")
        return queryset.filter(ward_id=ward_id) if ward_id else queryset
