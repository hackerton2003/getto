from rest_framework.routers import DefaultRouter
from apps.properties.views import (
    PropertyMediaViewSet,
    PropertyViewSet,
    RoomMediaViewSet,
    RoomViewSet,
)

router = DefaultRouter()
router.register("properties/media", PropertyMediaViewSet, basename="property-media")
router.register("properties", PropertyViewSet, basename="property")
router.register("rooms/media", RoomMediaViewSet, basename="room-media")
router.register("rooms", RoomViewSet, basename="room")

urlpatterns = router.urls
