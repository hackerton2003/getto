from rest_framework.routers import DefaultRouter
from apps.universities.views import (
    CampusViewSet,
    DepartmentViewSet,
    RankViewSet,
    UniversityViewSet,
)

router = DefaultRouter()
router.register("universities", UniversityViewSet, basename="university")
router.register("campuses", CampusViewSet, basename="campus")
router.register("departments", DepartmentViewSet, basename="department")
router.register("ranks", RankViewSet, basename="rank")

urlpatterns = router.urls
