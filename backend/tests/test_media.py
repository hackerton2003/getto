import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from api.v1.authentication import create_access_token
from apps.customers.models import Customer
from apps.house_owners.models import AccommodationOwner
from apps.locations.models import District, Region, Street, Ward
from apps.properties.models import Property, PropertyMedia, Room, RoomMedia
from apps.staff.models import Role, Staff
from apps.universities.models import University
from services.properties import PropertyService


class MediaWorkflowTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(name="Media Test Region")
        self.district = District.objects.create(region=self.region, name="Media Test District")
        self.ward = Ward.objects.create(district=self.district, name="Media Test Ward")
        self.street = Street.objects.create(ward=self.ward, name="Media Test Street")
        self.university = University.objects.create(name="Media Test University")

        self.owner = AccommodationOwner.objects.create(
            firstname="Media",
            lastname="Owner",
            phone="+255733333331",
            email="media-owner@example.test",
            password="hashed-password",
        )
        self.other_owner = AccommodationOwner.objects.create(
            firstname="Other",
            lastname="Owner",
            phone="+255733333332",
            email="other-media-owner@example.test",
            password="hashed-password",
        )
        self.customer = Customer.objects.create(
            firstname="Customer",
            lastname="User",
            phone="+255733333333",
            email="media-customer@example.test",
            password="hashed-password",
            university=self.university,
        )
        self.role = Role.objects.create(name="Staff Role")
        self.staff = Staff.objects.create(
            firstname="Staff",
            lastname="User",
            phone="+255733333334",
            email="media-staff@example.test",
            password="hashed-password",
            branch="Main",
            role=self.role,
        )

        self.property = Property.objects.create(
            owner=self.owner,
            name="Sunrise Hostel",
            description="Nice hostel",
            street=self.street,
            latitude=Decimal("-6.7924000"),
            longitude=Decimal("39.2083000"),
            verification_status=Property.VerificationStatus.VERIFIED,
        )
        self.room = Room.objects.create(
            property=self.property,
            room_type="Single Room",
            price=Decimal("150000.00"),
            capacity=1,
            status=Room.Status.AVAILABLE,
        )

        self.owner_client = self.client_for(self.owner, "owner")
        self.other_owner_client = self.client_for(self.other_owner, "owner")
        self.customer_client = self.client_for(self.customer, "customer")
        self.staff_client = self.client_for(self.staff, "staff")
        self.anon_client = APIClient()

        self.media_directory = tempfile.mkdtemp(prefix="getto-media-test-")
        self.media_settings = override_settings(MEDIA_ROOT=self.media_directory)
        self.media_settings.enable()

    def tearDown(self):
        self.media_settings.disable()
        shutil.rmtree(self.media_directory, ignore_errors=True)

    @staticmethod
    def client_for(account, account_type):
        client = APIClient()
        token = create_access_token(account, account_type)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    @staticmethod
    def sample_jpeg(name="photo.jpg"):
        return SimpleUploadedFile(
            name,
            b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50,
            content_type="image/jpeg",
        )

    @staticmethod
    def sample_png(name="image.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 40,
            content_type="image/png",
        )

    @staticmethod
    def sample_mp4(name="clip.mp4"):
        return SimpleUploadedFile(
            name,
            b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 40,
            content_type="video/mp4",
        )

    def test_service_uploads_image_and_video_for_property(self):
        jpeg_file = self.sample_jpeg()
        media = PropertyService.upload_property_media(
            property_id=self.property.pk,
            uploaded_file=jpeg_file,
            owner_id=self.owner.pk,
        )
        self.assertEqual(media.type, PropertyMedia.MediaType.IMAGE)
        self.assertEqual(media.property_id, self.property.pk)
        self.assertTrue(default_storage.exists(media.file_path))

        mp4_file = self.sample_mp4()
        video_media = PropertyService.upload_property_media(
            property_id=self.property.pk,
            uploaded_file=mp4_file,
            owner_id=self.owner.pk,
        )
        self.assertEqual(video_media.type, PropertyMedia.MediaType.VIDEO)
        self.assertTrue(default_storage.exists(video_media.file_path))

    def test_service_uploads_and_deletes_room_media(self):
        png_file = self.sample_png()
        room_media = PropertyService.upload_room_media(
            room_id=self.room.pk,
            uploaded_file=png_file,
            owner_id=self.owner.pk,
        )
        self.assertEqual(room_media.type, RoomMedia.MediaType.IMAGE)
        self.assertTrue(default_storage.exists(room_media.file_path))

        # Delete media
        deleted = PropertyService.delete_room_media(
            media_id=room_media.pk,
            owner_id=self.owner.pk,
        )
        self.assertTrue(deleted)
        self.assertFalse(RoomMedia.objects.filter(pk=room_media.pk).exists())
        self.assertFalse(default_storage.exists(room_media.file_path))

    def test_service_rejects_unauthorized_owner(self):
        jpeg_file = self.sample_jpeg()
        with self.assertRaises(ValidationError):
            PropertyService.upload_property_media(
                property_id=self.property.pk,
                uploaded_file=jpeg_file,
                owner_id=self.other_owner.pk,
            )

    def test_service_rejects_invalid_file_signature(self):
        fake_jpeg = SimpleUploadedFile(
            "fake.jpg",
            b"not-a-real-jpeg-header-data",
            content_type="image/jpeg",
        )
        with self.assertRaises(ValidationError):
            PropertyService.upload_property_media(
                property_id=self.property.pk,
                uploaded_file=fake_jpeg,
                owner_id=self.owner.pk,
            )

    def test_owner_property_media_api_endpoints(self):
        # 1. Owner uploads property media
        url = reverse("owner-property-media", kwargs={"property_id": self.property.pk})
        response = self.owner_client.post(
            url,
            {"file": self.sample_jpeg()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        media_id = response.data["id"]
        self.assertEqual(response.data["type"], "image")
        self.assertIn("file_url", response.data)
        self.assertIsNotNone(response.data["file_url"])

        # 2. Owner lists property media
        list_response = self.owner_client.get(url)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], media_id)

        # 3. Other owner cannot delete it
        detail_url = reverse(
            "owner-property-media-detail",
            kwargs={"property_id": self.property.pk, "media_id": media_id},
        )
        forbidden = self.other_owner_client.delete(detail_url)
        self.assertEqual(forbidden.status_code, 404)

        # 4. Owner deletes their property media
        delete_response = self.owner_client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(PropertyMedia.objects.count(), 0)

    def test_owner_room_media_api_endpoints(self):
        # 1. Owner uploads room media
        url = reverse("owner-room-media", kwargs={"room_id": self.room.pk})
        response = self.owner_client.post(
            url,
            {"file": self.sample_png()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        media_id = response.data["id"]
        self.assertEqual(response.data["type"], "image")
        self.assertIn("file_url", response.data)

        # 2. Owner lists room media
        list_response = self.owner_client.get(url)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)

        # 3. Owner deletes room media
        detail_url = reverse(
            "owner-room-media-detail",
            kwargs={"room_id": self.room.pk, "media_id": media_id},
        )
        delete_response = self.owner_client.delete(detail_url)
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(RoomMedia.objects.count(), 0)

    def test_property_media_viewset_public_and_owner_actions(self):
        # 1. Upload media via owner
        media = PropertyService.upload_property_media(
            property_id=self.property.pk,
            uploaded_file=self.sample_jpeg(),
            owner_id=self.owner.pk,
        )

        # 2. Public can view media for verified property
        public_url = reverse("property-media-list")
        res = self.anon_client.get(f"{public_url}?property_id={self.property.pk}")
        self.assertEqual(res.status_code, 200)
        results = res.data.get("results", res.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], media.pk)

        # 3. Customer cannot upload media to /properties/media/
        cust_upload = self.customer_client.post(
            public_url,
            {"property_id": self.property.pk, "file": self.sample_jpeg()},
            format="multipart",
        )
        self.assertEqual(cust_upload.status_code, 403)

        # 4. Owner CAN upload to /properties/media/
        owner_upload = self.owner_client.post(
            public_url,
            {"property_id": self.property.pk, "file": self.sample_png()},
            format="multipart",
        )
        self.assertEqual(owner_upload.status_code, 201)
        new_media_id = owner_upload.data["id"]

        # 5. Owner can delete from /properties/media/{id}/
        item_url = reverse("property-media-detail", kwargs={"pk": new_media_id})
        del_res = self.owner_client.delete(item_url)
        self.assertEqual(del_res.status_code, 204)
