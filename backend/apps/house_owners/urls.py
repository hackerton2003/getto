from django.urls import path
from apps.house_owners.views import (
    OwnerDashboardView,
    OwnerProfileView,
    OwnerPropertyDetailView,
    OwnerPropertyListView,
    OwnerPropertyMediaDetailView,
    OwnerPropertyMediaView,
    OwnerRegistrationView,
    OwnerRoomCreateView,
    OwnerRoomMediaDetailView,
    OwnerRoomMediaView,
    OwnerVerificationDocumentsView,
    OwnerVerificationListView,
    OwnerVerificationSubmitView,
)

urlpatterns = [
    path("register/", OwnerRegistrationView.as_view(), name="owner-register"),
    path("me/", OwnerProfileView.as_view(), name="owner-profile"),
    path("me/dashboard/", OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("properties/", OwnerPropertyListView.as_view(), name="owner-properties"),
    path("properties/<int:property_id>/", OwnerPropertyDetailView.as_view(), name="owner-property-detail"),
    path("properties/<int:property_id>/media/", OwnerPropertyMediaView.as_view(), name="owner-property-media"),
    path("properties/<int:property_id>/media/<int:media_id>/", OwnerPropertyMediaDetailView.as_view(), name="owner-property-media-detail"),
    path("properties/<int:property_id>/rooms/", OwnerRoomCreateView.as_view(), name="owner-property-rooms"),
    path("rooms/<int:room_id>/media/", OwnerRoomMediaView.as_view(), name="owner-room-media"),
    path("rooms/<int:room_id>/media/<int:media_id>/", OwnerRoomMediaDetailView.as_view(), name="owner-room-media-detail"),
    path("verifications/", OwnerVerificationListView.as_view(), name="owner-verifications"),
    path("properties/<int:property_id>/verifications/", OwnerVerificationSubmitView.as_view(), name="owner-verification-submit"),
    path("verifications/<int:verification_id>/documents/", OwnerVerificationDocumentsView.as_view(), name="owner-verification-documents"),
]
