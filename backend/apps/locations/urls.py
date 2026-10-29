from rest_framework.routers import DefaultRouter
from apps.locations.views import (
    DistrictViewSet,
    RegionViewSet,
    StreetViewSet,
    WardViewSet,
)

router = DefaultRouter()
router.register("regions", RegionViewSet, basename="region")
router.register("districts", DistrictViewSet, basename="district")
router.register("wards", WardViewSet, basename="ward")
router.register("streets", StreetViewSet, basename="street")

urlpatterns = router.urls
