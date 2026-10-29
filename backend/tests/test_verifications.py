import os
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.test.utils import override_settings

from api.v1.authentication import create_access_token
from apps.house_owners.models import AccommodationOwner
from apps.locations.models import District, Region, Street, Ward
from apps.notifications.models import WebhookDelivery, WebhookSubscription
from apps.properties.models import Property, Verification, VerificationDocument
from apps.staff.models import Permission, Role, Staff
from services.verifications import VerificationService


class VerificationWorkflowTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(name="Verification Region")
        self.district = District.objects.create(region=self.region, name="Verification District")
        self.ward = Ward.objects.create(district=self.district, name="Verification Ward")
        self.street = Street.objects.create(ward=self.ward, name="Verification Street")
        self.owner = self.create_owner("owner", "+255722222221")
        self.other_owner = self.create_owner("other-owner", "+255722222222")
        self.property = self.create_property(self.owner, "Owner Property")
        self.other_property = self.create_property(self.other_owner, "Other Property")
        role = Role.objects.create(name="Verification Staff")
        verification_permission = Permission.objects.create(name="property.verification.review")
        role.permissions.add(verification_permission)
        self.staff = Staff.objects.create(
            firstname="Review",
            lastname="Staff",
            phone="+255722222223",
            email="review-staff@example.test",
            password="unused-test-password",
            branch="Main",
            role=role,
        )
        self.owner_client = self.client_for(self.owner, "owner")
        self.other_owner_client = self.client_for(self.other_owner, "owner")
        self.staff_client = self.client_for(self.staff, "staff")
        self.media_directory = tempfile.mkdtemp(prefix="getto-test-media-")
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory)
        self.media_settings.enable()

    def tearDown(self):
        self.media_settings.disable()
        shutil.rmtree(self.media_directory, ignore_errors=True)

    @staticmethod
    def create_owner(prefix, phone):
        return AccommodationOwner.objects.create(
            firstname=prefix,
            lastname="Owner",
            phone=phone,
            email=f"{prefix}@example.test",
            password="unused-test-password",
        )

    def create_property(self, owner, name):
        return Property.objects.create(
            owner=owner,
            name=name,
            street=self.street,
            latitude="-6.8000000",
            longitude="39.2000000",
        )

    @staticmethod
    def client_for(account, account_type):
        client = APIClient()
        token = create_access_token(account, account_type)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    @staticmethod
    def upload_file(name="title-deed.pdf", content=b"%PDF-1.7 verification proof"):
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    def documents(self):
        return [{"file": self.upload_file(), "description": "Ownership proof"}]

    def submit(self, property_instance=None):
        return VerificationService.submit(
            property_id=(property_instance or self.property).pk,
            owner_id=self.owner.pk,
            documents=self.documents(),
        )

    def test_submission_creates_documents_and_blocks_duplicate_pending_record(self):
        verification = self.submit()
        self.property.refresh_from_db()
        self.assertEqual(verification.status, Verification.Status.PENDING)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.PENDING)
        document = VerificationDocument.objects.get(verification=verification)
        self.assertEqual(document.original_filename, "title-deed.pdf")
        self.assertEqual(document.content_type, "application/pdf")
        self.assertGreater(document.file_size, 0)
        self.assertEqual(len(document.sha256), 64)
        from django.core.files.storage import default_storage
        with default_storage.open(document.file_path, "rb") as stored_file:
            self.assertEqual(stored_file.read(), b"%PDF-1.7 verification proof")
        with self.assertRaises(ValidationError):
            self.submit()
        self.assertEqual(Verification.objects.filter(property=self.property).count(), 1)

    def test_approval_updates_verification_and_property_and_is_terminal(self):
        verification = self.submit()
        reviewed = VerificationService.review(
            verification_id=verification.pk,
            staff_id=self.staff.pk,
            decision=Verification.Status.APPROVED,
        )
        self.property.refresh_from_db()
        self.assertEqual(reviewed.status, Verification.Status.APPROVED)
        self.assertEqual(reviewed.reviewed_by_staff_id, self.staff.pk)
        self.assertIsNotNone(reviewed.reviewed_at)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.VERIFIED)
        with self.assertRaises(ValidationError):
            VerificationService.review(
                verification_id=verification.pk,
                staff_id=self.staff.pk,
                decision=Verification.Status.REJECTED,
                remarks="Too late",
            )

    def test_owner_property_edit_requires_reverification(self):
        verification = self.submit()
        VerificationService.review(
            verification_id=verification.pk,
            staff_id=self.staff.pk,
            decision=Verification.Status.APPROVED,
        )
        response = self.owner_client.patch(
            reverse("owner-property-detail", kwargs={"property_id": self.property.pk}),
            {"name": "Updated property name"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.name, "Updated property name")
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.PENDING)

    def test_verification_changes_create_owner_callback_deliveries(self):
        WebhookSubscription.objects.create(
            owner_type="owner",
            owner_id=self.owner.pk,
            target_url="https://hooks.example.com/getto",
            secret="test-secret",
            event_types=["verification.submitted", "verification.approved"],
        )
        verification = self.submit()
        deliveries = WebhookDelivery.objects.filter(subscription__owner_id=self.owner.pk)
        self.assertTrue(deliveries.filter(event_type="verification.submitted").exists())
        self.assertEqual(deliveries.count(), 1)

        VerificationService.review(
            verification_id=verification.pk,
            staff_id=self.staff.pk,
            decision=Verification.Status.APPROVED,
        )
        self.assertTrue(deliveries.filter(event_type="verification.approved").exists())
        self.assertEqual(deliveries.count(), 2)

    def test_rejection_requires_remarks_and_allows_resubmission(self):
        verification = self.submit()
        with self.assertRaises(ValidationError):
            VerificationService.review(
                verification_id=verification.pk,
                staff_id=self.staff.pk,
                decision=Verification.Status.REJECTED,
            )
        self.assertEqual(verification.status, Verification.Status.PENDING)

        rejected = VerificationService.review(
            verification_id=verification.pk,
            staff_id=self.staff.pk,
            decision=Verification.Status.REJECTED,
            remarks="Please provide a clearer ownership document.",
        )
        self.property.refresh_from_db()
        self.assertEqual(rejected.status, Verification.Status.REJECTED)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.REJECTED)

        replacement = self.submit()
        self.property.refresh_from_db()
        self.assertEqual(replacement.status, Verification.Status.PENDING)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.PENDING)

    def test_owner_submission_and_documents_are_scoped_to_their_property(self):
        submit_url = reverse("owner-verification-submit", kwargs={"property_id": self.property.pk})
        response = self.owner_client.post(
            submit_url,
            {"file": self.upload_file(), "description": "Ownership proof"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        verification_id = response.data["id"]

        foreign_submit = self.owner_client.post(
            reverse("owner-verification-submit", kwargs={"property_id": self.other_property.pk}),
            {"file": self.upload_file(), "description": "Ownership proof"},
            format="multipart",
        )
        self.assertEqual(foreign_submit.status_code, 404)

        documents_url = reverse(
            "owner-verification-documents",
            kwargs={"verification_id": verification_id},
        )
        own_documents = self.owner_client.get(documents_url)
        self.assertEqual(own_documents.status_code, 200)
        self.assertEqual(len(own_documents.data), 1)

        foreign_documents = self.other_owner_client.get(documents_url)
        self.assertEqual(foreign_documents.status_code, 404)

        added_document = self.owner_client.post(
            documents_url,
            {"file": self.upload_file("site-plan.pdf", b"%PDF-1.5 site plan"), "description": "Site plan"},
            format="multipart",
        )
        self.assertEqual(added_document.status_code, 201)
        self.assertEqual(VerificationDocument.objects.filter(verification_id=verification_id).count(), 2)

    def test_document_download_is_scoped_to_owner_or_staff(self):
        verification = self.submit()
        document = VerificationDocument.objects.get(verification=verification)
        download_url = reverse("verification-document-download", kwargs={"document_id": document.pk})

        own_download = self.owner_client.get(download_url)
        self.assertEqual(own_download.status_code, 200)
        self.assertEqual(b"".join(own_download.streaming_content), b"%PDF-1.7 verification proof")

        foreign_download = self.other_owner_client.get(download_url)
        self.assertEqual(foreign_download.status_code, 404)

        staff_download = self.staff_client.get(download_url)
        self.assertEqual(staff_download.status_code, 200)
        self.assertEqual(b"".join(staff_download.streaming_content), b"%PDF-1.7 verification proof")

    def test_upload_rejects_mismatched_file_signature(self):
        with self.assertRaises(ValidationError):
            VerificationService.submit(
                property_id=self.property.pk,
                owner_id=self.owner.pk,
                documents=[{
                    "file": self.upload_file("fake.pdf", b"not a pdf"),
                    "description": "Invalid upload",
                }],
            )
        self.assertEqual(Verification.objects.filter(property=self.property).count(), 0)

    def test_only_staff_can_review_and_review_action_persists_state(self):
        verification = self.submit()
        approve_url = reverse(
            "staff-verification-approve",
            kwargs={"verification_id": verification.pk},
        )
        owner_attempt = self.owner_client.post(approve_url, {}, format="json")
        self.assertEqual(owner_attempt.status_code, 403)
        verification.refresh_from_db()
        self.assertEqual(verification.status, Verification.Status.PENDING)

        staff_response = self.staff_client.post(approve_url, {}, format="json")
        self.assertEqual(staff_response.status_code, 200)
        verification.refresh_from_db()
        self.property.refresh_from_db()
        self.assertEqual(verification.status, Verification.Status.APPROVED)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.VERIFIED)

    def test_staff_rejection_endpoint_requires_remarks(self):
        verification = self.submit()
        reject_url = reverse(
            "staff-verification-reject",
            kwargs={"verification_id": verification.pk},
        )
        missing_remarks = self.staff_client.post(reject_url, {}, format="json")
        self.assertEqual(missing_remarks.status_code, 400)
        verification.refresh_from_db()
        self.assertEqual(verification.status, Verification.Status.PENDING)

        rejected = self.staff_client.post(
            reject_url,
            {"remarks": "Ownership document is unreadable."},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(rejected.data["status"], Verification.Status.REJECTED)
        self.assertEqual(self.property.verification_status, Property.VerificationStatus.REJECTED)