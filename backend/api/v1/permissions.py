from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAccountType(BasePermission):
    account_type = None

    def has_permission(self, request, view):
        return (
            bool(request.user and request.user.is_authenticated)
            and request.user.account_type == self.account_type
        )


class IsCustomer(IsAccountType):
    account_type = "customer"


class IsOwner(IsAccountType):
    account_type = "owner"


class IsStaff(IsAccountType):
    account_type = "staff"


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.account_type == "staff"
        )


class IsStaffWithPermission(IsStaff):
    permission_name = None

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if self.permission_name is None:
            return True
        return request.user.role.permissions.filter(name=self.permission_name).exists()


class CanManageStaff(IsStaffWithPermission):
    permission_name = "staff.manage"


class CanReviewVerification(IsStaffWithPermission):
    permission_name = "property.verification.review"


class CanReviewReports(IsStaffWithPermission):
    permission_name = "property.report.review"


class CanModerateReviews(IsStaffWithPermission):
    permission_name = "property.review.moderate"
