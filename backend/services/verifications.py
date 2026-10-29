import hashlib
import os
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.utils import timezone

from apps.properties.models import Property, Verification, VerificationDocument
from apps.staff.models import Staff
from services.webhooks import WebhookService
from services.notifications import NotificationService


class VerificationService:
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {
        "application/pdf": ((".pdf",), b"%PDF-"),
        "image/jpeg": ((".jpg", ".jpeg"), b"\xff\xd8\xff"),
        "image/png": ((".png",), b"\x89PNG\r\n\x1a\n"),
    }

    @staticmethod
    def _validate_documents(documents):
        if not documents:
            raise ValidationError({"documents": "At least one verification document is required."})
        normalized = []
        for index, document in enumerate(documents):
            if not isinstance(document, dict):
                raise ValidationError({f"documents[{index}]": "Document details must be an object."})
            uploaded_file = document.get("file")
            if uploaded_file is None or not hasattr(uploaded_file, "chunks"):
                raise ValidationError({f"documents[{index}].file": "Upload a document file."})
            content_type = uploaded_file.content_type or ""
            allowed = VerificationService.ALLOWED_CONTENT_TYPES.get(content_type)
            extension = os.path.splitext(uploaded_file.name)[1].lower()
            if allowed is None or extension not in allowed[0]:
                raise ValidationError({
                    f"documents[{index}].file": "Only PDF, JPEG, and PNG documents are accepted."
                })
            if uploaded_file.size <= 0 or uploaded_file.size > VerificationService.MAX_DOCUMENT_SIZE:
                raise ValidationError({
                    f"documents[{index}].file": "File must be between 1 byte and 10 MB."
                })
            first_bytes = uploaded_file.read(len(allowed[1]))
            uploaded_file.seek(0)
            if not first_bytes.startswith(allowed[1]):
                raise ValidationError({f"documents[{index}].file": "File content does not match its type."})
            description = document.get("description")
            if description is not None and not isinstance(description, str):
                raise ValidationError({f"documents[{index}].description": "Description must be text."})
            if description and len(description) > 255:
                raise ValidationError({f"documents[{index}].description": "Description is too long."})
            normalized.append({
                "file": uploaded_file,
                "description": (description or "").strip() or None,
                "original_filename": os.path.basename(uploaded_file.name)[:255],
                "content_type": content_type,
                "file_size": uploaded_file.size,
            })
        return normalized

    @staticmethod
    def _persist_document(verification, owner_id, document):
        uploaded_file = document.pop("file")
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        uploaded_file.seek(0)
        document["sha256"] = digest.hexdigest()
        safe_name = get_valid_filename(document["original_filename"])[:150]
        storage_name = f"verification-documents/{owner_id}/{uuid4().hex}-{safe_name}"
        stored_name = default_storage.save(storage_name, uploaded_file)
        if len(stored_name) > 255:
            default_storage.delete(stored_name)
            raise ValidationError({"file": "Generated storage path exceeds the supported length."})
        document["file_path"] = stored_name
        try:
            return VerificationDocument.objects.create(verification=verification, **document)
        except Exception:
            default_storage.delete(stored_name)
            raise

    @classmethod
    def submit(cls, *, property_id, owner_id, documents):
        normalized_documents = cls._validate_documents(documents)
        created_files = []
        try:
            with transaction.atomic():
                property_instance = Property.objects.select_for_update().get(
                    pk=property_id,
                    owner_id=owner_id,
                )
                if property_instance.verification_status == Property.VerificationStatus.VERIFIED:
                    raise ValidationError({"property": "A verified property cannot be resubmitted."})
                if property_instance.verifications.filter(status=Verification.Status.PENDING).exists():
                    raise ValidationError({"property": "This property already has a pending verification."})

                verification = Verification.objects.create(
                    property=property_instance,
                    status=Verification.Status.PENDING,
                    submitted_at=timezone.now(),
                )
                for document in normalized_documents:
                    created_document = cls._persist_document(verification, owner_id, document)
                    created_files.append(created_document.file_path)
                    WebhookService.publish(
                        owner_type="owner",
                        owner_id=owner_id,
                        event_type="verification.document.uploaded",
                        data={
                            "property_id": property_instance.pk,
                            "verification_id": verification.pk,
                            "document_id": created_document.pk,
                        },
                    )
                if property_instance.verification_status != Property.VerificationStatus.PENDING:
                    property_instance.verification_status = Property.VerificationStatus.PENDING
                    property_instance.save(update_fields=("verification_status", "updated_at"))
                WebhookService.publish(
                    owner_type="owner",
                    owner_id=owner_id,
                    event_type="verification.submitted",
                    data={
                        "property_id": property_instance.pk,
                        "verification_id": verification.pk,
                        "status": verification.status,
                    },
                )
                NotificationService.send(
                    recipient_type="owner",
                    recipient_id=owner_id,
                    title="Property verification submitted",
                    message=f"Verification for {property_instance.name} is pending review.",
                )
                return verification
        except Exception:
            for storage_name in created_files:
                default_storage.delete(storage_name)
            raise

    @classmethod
    def add_document(cls, *, verification_id, owner_id, file, description=None):
        normalized = cls._validate_documents([{
            "file": file,
            "description": description,
        }])[0]
        with transaction.atomic():
            verification = Verification.objects.select_for_update().select_related("property").get(
                pk=verification_id,
                property__owner_id=owner_id,
            )
            if verification.status != Verification.Status.PENDING:
                raise ValidationError({"verification": "Documents can only be added while verification is pending."})
            document = cls._persist_document(verification, owner_id, normalized)
            WebhookService.publish(
                owner_type="owner",
                owner_id=owner_id,
                event_type="verification.document.uploaded",
                data={
                    "property_id": verification.property_id,
                    "verification_id": verification.pk,
                    "document_id": document.pk,
                },
            )
            return document

    @staticmethod
    def review(*, verification_id, staff_id, decision, remarks=None):
        if decision not in (Verification.Status.APPROVED, Verification.Status.REJECTED):
            raise ValidationError({"decision": "Decision must be approved or rejected."})
        if remarks is not None and (not isinstance(remarks, str) or len(remarks) > 255):
            raise ValidationError({"remarks": "Remarks must be text of 255 characters or fewer."})
        if decision == Verification.Status.REJECTED and not (remarks and remarks.strip()):
            raise ValidationError({"remarks": "A reason is required when rejecting verification."})

        property_id = Verification.objects.values_list("property_id", flat=True).get(pk=verification_id)
        with transaction.atomic():
            property_instance = Property.objects.select_for_update().get(pk=property_id)
            verification = Verification.objects.select_for_update().get(
                pk=verification_id,
                property=property_instance,
            )
            staff = Staff.objects.get(pk=staff_id)
            if staff.status != Staff.Status.ACTIVE:
                raise ValidationError({"staff": "Only active staff can review verifications."})
            if verification.status != Verification.Status.PENDING:
                raise ValidationError({"verification": "Only pending verifications can be reviewed."})

            now = timezone.now()
            verification.status = decision
            verification.reviewed_by_staff = staff
            verification.reviewed_at = now
            verification.remarks = (remarks or "").strip() or None
            verification.save(update_fields=(
                "status",
                "reviewed_by_staff",
                "reviewed_at",
                "remarks",
            ))

            property_instance.verification_status = (
                Property.VerificationStatus.VERIFIED
                if decision == Verification.Status.APPROVED
                else Property.VerificationStatus.REJECTED
            )
            property_instance.save(update_fields=("verification_status", "updated_at"))
            WebhookService.publish(
                owner_type="owner",
                owner_id=property_instance.owner_id,
                event_type=(
                    "verification.approved"
                    if decision == Verification.Status.APPROVED
                    else "verification.rejected"
                ),
                data={
                    "property_id": property_instance.pk,
                    "verification_id": verification.pk,
                    "status": verification.status,
                    "remarks": verification.remarks,
                },
            )
            NotificationService.send(
                recipient_type="owner",
                recipient_id=property_instance.owner_id,
                title=f"Property verification {verification.status}",
                message=(
                    f"Verification for {property_instance.name} was {verification.status}. "
                    f"{verification.remarks or ''}"
                ).strip(),
            )
            return verification
