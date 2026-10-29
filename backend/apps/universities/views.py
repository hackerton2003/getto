from api.v1.serializers.staff import DepartmentSerializer, RankSerializer
from api.v1.serializers.universities import CampusSerializer, UniversitySerializer
from api.v1.utils import PublicReadOnlyViewSet
from apps.staff.models import Department, Rank
from apps.universities.models import Campus, University
from api.v1.permissions import IsStaff
from rest_framework.viewsets import ReadOnlyModelViewSet


class UniversityViewSet(PublicReadOnlyViewSet):
    queryset = University.objects.select_related("district")
    serializer_class = UniversitySerializer


class CampusViewSet(PublicReadOnlyViewSet):
    serializer_class = CampusSerializer

    def get_queryset(self):
        queryset = Campus.objects.select_related("university", "ward")
        university_id = self.request.query_params.get("university_id")
        return queryset.filter(university_id=university_id) if university_id else queryset


class StaffCatalogViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsStaff,)


class DepartmentViewSet(StaffCatalogViewSet):
    queryset = Department.objects.select_related("hod")
    serializer_class = DepartmentSerializer


class RankViewSet(StaffCatalogViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer
