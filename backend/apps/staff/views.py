from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.storage import default_storage
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema

from api.v1.permissions import CanManageStaff, CanModerateReviews, CanReviewReports, CanReviewVerification, IsStaff
from api.v1.serializers.properties import (
    VerificationDocumentSerializer,
    VerificationReviewSerializer,
    VerificationSerializer,
)
from api.v1.serializers.staff import (
    PermissionSerializer,
    RoleSerializer,
    StaffCreateSerializer,
    StaffRoleAssignmentSerializer,
    StaffSerializer,
    StaffStatusUpdateSerializer,
)
from api.v1.serializers.customers import (
    ReportReviewSerializer,
    ReportSerializer,
    ReviewModerationSerializer,
    ReviewSerializer,
)
from api.v1.utils import audit_staff_action, raise_api_validation
from apps.properties.models import Verification, VerificationDocument
from apps.customers.models import Report, Review
from apps.staff.models import Permission, Role, Staff
from services.staff import StaffService
from services.verifications import VerificationService


class StaffCatalogViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsStaff,)


class StaffSelfView(APIView):
    permission_classes = (IsStaff,)

    @extend_schema(responses={200: StaffSerializer}, operation_id="staff_self_retrieve")
    def get(self, request):
        return Response(StaffSerializer(request.user.account).data)


class StaffManagementView(APIView):
    permission_classes = (CanManageStaff,)

    @extend_schema(responses={200: StaffSerializer(many=True)}, operation_id="staff_list")
    def get(self, request):
        staff_members = Staff.objects.select_related("role", "department", "rank")
        return Response(StaffSerializer(staff_members, many=True).data)

    @extend_schema(request=StaffCreateSerializer, responses={201: StaffSerializer}, operation_id="staff_create")
    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        password = data.pop("password")
        try:
            staff = StaffService.create_staff(
                password=password,
                assigned_by_staff_id=request.user.pk,
                **data,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        audit_staff_action(request, "staff_account_created", f"Created staff account {staff.pk}")
        return Response(StaffSerializer(staff).data, status=status.HTTP_201_CREATED)


class StaffRoleAssignmentView(APIView):
    permission_classes = (CanManageStaff,)

    @extend_schema(request=StaffRoleAssignmentSerializer, responses={200: StaffSerializer}, operation_id="staff_assign_role")
    def patch(self, request, staff_id):
        serializer = StaffRoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            staff = StaffService.assign_role(
                staff_id=staff_id,
                role_id=serializer.validated_data["role_id"].pk,
                assigned_by_staff_id=request.user.pk,
            )
        except Staff.DoesNotExist as exc:
            raise NotFound("Staff account not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        audit_staff_action(request, "staff_role_assigned", f"Assigned role to staff account {staff.pk}")
        return Response(StaffSerializer(staff).data)


class StaffStatusUpdateView(APIView):
    permission_classes = (CanManageStaff,)

    @extend_schema(request=StaffStatusUpdateSerializer, responses={200: StaffSerializer}, operation_id="staff_update_status")
    def patch(self, request, staff_id):
        if staff_id == request.user.pk:
            raise ValidationError({"staff_id": "You cannot change your own account status."})
        serializer = StaffStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            staff = StaffService.set_status(
                staff_id=staff_id,
                status=serializer.validated_data["status"],
            )
        except Staff.DoesNotExist as exc:
            raise NotFound("Staff account not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        audit_staff_action(request, "staff_status_updated", f"Updated status for staff account {staff.pk}")
        return Response(StaffSerializer(staff).data)


class RoleViewSet(StaffCatalogViewSet):
    queryset = Role.objects.prefetch_related("permissions")
    serializer_class = RoleSerializer


class PermissionViewSet(StaffCatalogViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class VerificationViewSet(StaffCatalogViewSet):
    queryset = Verification.objects.select_related("property", "reviewed_by_staff")
    serializer_class = VerificationSerializer


class VerificationDocumentViewSet(StaffCatalogViewSet):
    queryset = VerificationDocument.objects.select_related("verification", "verification__property")
    serializer_class = VerificationDocumentSerializer


class VerificationDocumentDownloadView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={(200, "application/octet-stream"): bytes}, operation_id="verification_document_download")
    def get(self, request, document_id):
        document = get_object_or_404(
            VerificationDocument.objects.select_related("verification", "verification__property"),
            pk=document_id,
        )
        if request.user.account_type == "owner":
            if document.verification.property.owner_id != request.user.pk:
                raise NotFound("Document not found.")
        elif request.user.account_type != "staff":
            raise NotFound("Document not found.")
        if not default_storage.exists(document.file_path):
            raise NotFound("Document file is unavailable.")
        file_handle = default_storage.open(document.file_path, "rb")
        response = FileResponse(
            file_handle,
            content_type=document.content_type,
            as_attachment=True,
            filename=document.original_filename,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StaffVerificationReviewView(APIView):
    permission_classes = (CanReviewVerification,)

    @extend_schema(request=VerificationReviewSerializer, responses={200: VerificationSerializer})
    def post(self, request, verification_id, decision):
        if decision not in ("approve", "reject"):
            raise NotFound("Verification action not found.")
        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_value = (
            Verification.Status.APPROVED
            if decision == "approve"
            else Verification.Status.REJECTED
        )
        try:
            verification = VerificationService.review(
                verification_id=verification_id,
                staff_id=request.user.pk,
                decision=status_value,
                remarks=serializer.validated_data.get("remarks"),
            )
        except Verification.DoesNotExist as exc:
            raise NotFound("Verification not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        audit_staff_action(
            request,
            f"property_verification_{'approved' if decision == 'approve' else 'rejected'}",
            f"Verification {verification.pk} for property {verification.property_id}",
        )
        return Response(VerificationSerializer(verification).data)


class StaffReportManagementView(APIView):
    permission_classes = (CanReviewReports,)

    @extend_schema(responses={200: ReportSerializer(many=True)})
    def get(self, request):
        reports = Report.objects.select_related("customer", "property", "reviewed_by_staff")
        status_filter = request.query_params.get("status")
        if status_filter:
            reports = reports.filter(status=status_filter)
        return Response(ReportSerializer(reports, many=True).data)

    @extend_schema(request=ReportReviewSerializer, responses={200: ReportSerializer})
    def patch(self, request, report_id):
        serializer = ReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = get_object_or_404(Report, pk=report_id)
        report.status = serializer.validated_data["status"]
        report.resolution_note = serializer.validated_data.get("resolution_note", "").strip()
        report.reviewed_by_staff = request.user.account
        report.reviewed_at = timezone.now()
        report.save(update_fields=("status", "resolution_note", "reviewed_by_staff", "reviewed_at"))
        audit_staff_action(request, "property_report_reviewed", f"Reviewed report {report.pk}: {report.status}")
        return Response(ReportSerializer(report).data)


class StaffReviewModerationView(APIView):
    permission_classes = (CanModerateReviews,)

    @extend_schema(responses={200: ReviewSerializer(many=True)})
    def get(self, request):
        reviews = Review.objects.select_related("customer", "property", "reviewed_by_staff")
        status_filter = request.query_params.get("status", Review.Status.PENDING)
        if status_filter:
            reviews = reviews.filter(status=status_filter)
        return Response(ReviewSerializer(reviews, many=True).data)

    @extend_schema(request=ReviewModerationSerializer, responses={200: ReviewSerializer})
    def patch(self, request, review_id):
        serializer = ReviewModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = get_object_or_404(Review, pk=review_id)
        if review.status != Review.Status.PENDING:
            raise ValidationError({"review": "Only pending reviews can be moderated."})
        review.status = serializer.validated_data["status"]
        review.reviewed_by_staff = request.user.account
        review.reviewed_at = timezone.now()
        review.save(update_fields=("status", "reviewed_by_staff", "reviewed_at"))
        audit_staff_action(request, "property_review_moderated", f"Moderated review {review.pk}: {review.status}")
        return Response(ReviewSerializer(review).data)
