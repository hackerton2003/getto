from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.staff.views import (
    PermissionViewSet,
    RoleViewSet,
    StaffManagementView,
    StaffRoleAssignmentView,
    StaffSelfView,
    StaffStatusUpdateView,
    StaffVerificationReviewView,
    VerificationDocumentDownloadView,
    VerificationDocumentViewSet,
    VerificationViewSet,
)

router = DefaultRouter()
router.register("staff/roles", RoleViewSet, basename="role")
router.register("staff/permissions", PermissionViewSet, basename="permission")
router.register("staff/verifications", VerificationViewSet, basename="verification")
router.register("staff/verification-documents", VerificationDocumentViewSet, basename="verification-document")

urlpatterns = [
    path("staff/me/", StaffSelfView.as_view(), name="staff-profile"),
    path("staff/accounts/", StaffManagementView.as_view(), name="staff-accounts"),
    path("staff/accounts/<int:staff_id>/role/", StaffRoleAssignmentView.as_view(), name="staff-role-assignment"),
    path("staff/accounts/<int:staff_id>/status/", StaffStatusUpdateView.as_view(), name="staff-status-update"),
    path("staff/verifications/<int:verification_id>/approve/", StaffVerificationReviewView.as_view(), {"decision": "approve"}, name="staff-verification-approve"),
    path("staff/verifications/<int:verification_id>/reject/", StaffVerificationReviewView.as_view(), {"decision": "reject"}, name="staff-verification-reject"),
    path("verifications/documents/<int:document_id>/download/", VerificationDocumentDownloadView.as_view(), name="verification-document-download"),
] + router.urls
