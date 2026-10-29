from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api.v1.authentication import create_access_token
from apps.bookings.models import Booking
from apps.customers.models import Customer
from apps.house_owners.models import AccommodationOwner
from apps.locations.models import District, Region, Street, Ward
from apps.properties.models import Property, Room
from apps.staff.models import Role, Staff
from apps.universities.models import University
from services.bookings import BookingService


class BookingCreateApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.region = Region.objects.create(name="Test Region")
		self.district = District.objects.create(region=self.region, name="Test District")
		self.ward = Ward.objects.create(district=self.district, name="Test Ward")
		self.street = Street.objects.create(ward=self.ward, name="Test Street")
		self.university = University.objects.create(name="Test University")
		self.customer = Customer.objects.create(
			firstname="Test",
			lastname="Customer",
			phone="+255700000001",
			email="customer@example.test",
			password="not-a-real-password-hash",
			university=self.university,
		)
		self.owner = AccommodationOwner.objects.create(
			firstname="Test",
			lastname="Owner",
			phone="+255700000002",
			email="owner@example.test",
			password="not-a-real-password-hash",
		)
		self.property = Property.objects.create(
			owner=self.owner,
			name="Test Property",
			street=self.street,
			latitude="-6.8000000",
			longitude="39.2000000",
		)
		self.room = Room.objects.create(
			property=self.property,
			room_type="Single",
			price="250000.00",
			capacity=1,
			status=Room.Status.AVAILABLE,
		)
		self.url = reverse("booking-create")
		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.customer, 'customer')}"
		)

	def test_create_booking_reserves_room_and_updates_property_counts(self):
		response = self.client.post(
			self.url,
			{"room_id": self.room.pk},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.data["status"], Booking.Status.PENDING)
		self.assertTrue(response.data["reference_no"].startswith("BK-"))
		self.room.refresh_from_db()
		self.property.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.RESERVED)
		self.assertEqual(self.property.total_rooms, 1)
		self.assertEqual(self.property.available_rooms, 0)
		self.assertEqual(Booking.objects.count(), 1)

	def test_create_booking_rejects_unavailable_room(self):
		self.room.status = Room.Status.UNAVAILABLE
		self.room.save(update_fields=("status",))

		response = self.client.post(
			self.url,
			{"room_id": self.room.pk},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(Booking.objects.count(), 0)
		self.room.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.UNAVAILABLE)

	def test_create_booking_rejects_inactive_customer(self):
		self.customer.status = Customer.Status.SUSPENDED
		self.customer.save(update_fields=("status",))

		response = self.client.post(
			self.url,
			{"room_id": self.room.pk},
			format="json",
		)

		self.assertEqual(response.status_code, 401)
		self.assertEqual(Booking.objects.count(), 0)
		self.room.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.AVAILABLE)

	def test_expire_stale_bookings_service(self):
		booking = BookingService.create_booking(
			customer_id=self.customer.pk,
			room_id=self.room.pk,
		)
		self.room.refresh_from_db()
		self.property.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.RESERVED)
		self.assertEqual(self.property.available_rooms, 0)

		# Fast forward booking created_at to 36 hours ago
		old_time = timezone.now() - timedelta(hours=36)
		Booking.objects.filter(pk=booking.pk).update(created_at=old_time)

		expired = BookingService.expire_stale_bookings(expiry_hours=24)
		self.assertEqual(len(expired), 1)

		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.EXPIRED)

		self.room.refresh_from_db()
		self.property.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.AVAILABLE)
		self.assertEqual(self.property.available_rooms, 1)

	def test_cleanup_stale_bookings_management_command(self):
		booking = BookingService.create_booking(
			customer_id=self.customer.pk,
			room_id=self.room.pk,
		)
		old_time = timezone.now() - timedelta(hours=48)
		Booking.objects.filter(pk=booking.pk).update(created_at=old_time)

		out = StringIO()
		# Dry run first
		call_command("cleanup_stale_bookings", hours=24, dry_run=True, stdout=out)
		self.assertIn("[DRY RUN]", out.getvalue())

		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.PENDING)

		# Real run
		out = StringIO()
		call_command("cleanup_stale_bookings", hours=24, stdout=out)
		self.assertIn("Successfully expired 1 stale booking(s)", out.getvalue())

		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.EXPIRED)
		self.room.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.AVAILABLE)

	def test_staff_booking_expire_stale_api(self):
		booking = BookingService.create_booking(
			customer_id=self.customer.pk,
			room_id=self.room.pk,
		)
		old_time = timezone.now() - timedelta(hours=30)
		Booking.objects.filter(pk=booking.pk).update(created_at=old_time)

		role = Role.objects.create(name="Staff Role")
		staff = Staff.objects.create(
			firstname="Admin",
			lastname="Staff",
			phone="+255700000099",
			email="staff-cleanup@example.test",
			password="hashed-password",
			branch="Main",
			role=role,
		)
		staff_client = APIClient()
		staff_client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {create_access_token(staff, 'staff')}"
		)

		url = reverse("staff-booking-expire-stale")
		response = staff_client.post(url, {"hours": 24}, format="json")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["expired_count"], 1)

		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.EXPIRED)
		self.room.refresh_from_db()
		self.assertEqual(self.room.status, Room.Status.AVAILABLE)

