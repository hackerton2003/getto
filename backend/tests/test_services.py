from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import PasswordReset
from apps.bookings.models import Booking
from apps.customers.models import Customer, CustomerPreference, Favourite
from apps.house_owners.models import AccommodationOwner
from apps.locations.models import District, Region, Street, Ward
from apps.properties.models import Property, Room
from apps.staff.models import Department, Permission, Role, Staff
from apps.system.models import AuditLog, SystemSettings
from apps.universities.models import Campus, University
from services.authentication import PasswordResetService
from services.authentication import hash_password_reset_token
from services.customers import CustomerService
from services.house_owners import AccommodationOwnerService
from services.locations import LocationService
from services.staff import StaffService
from services.system import SystemService
from services.universities import UniversityService


class DomainServiceTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(name="Test Region")
        self.district = District.objects.create(region=self.region, name="Test District")
        self.other_region = Region.objects.create(name="Other Region")
        self.other_district = District.objects.create(region=self.other_region, name="Other District")
        self.ward = Ward.objects.create(district=self.district, name="Test Ward")
        self.street = Street.objects.create(ward=self.ward, name="Test Street")
        self.university = University.objects.create(name="Test University", district=self.district)
        self.customer = Customer.objects.create(
            firstname="Test",
            lastname="Customer",
            phone="+255700000001",
            email="customer@example.test",
            password="already-hashed",
            university=self.university,
        )
        self.owner = AccommodationOwner.objects.create(
            firstname="Test",
            lastname="Owner",
            phone="+255700000002",
            email="owner@example.test",
            password="already-hashed",
        )
        self.property = Property.objects.create(
            owner=self.owner,
            name="Test Property",
            street=self.street,
            latitude="-6.8000000",
            longitude="39.2000000",
        )

    def test_customer_preferences_validate_hierarchy_and_price_range(self):
        registered_customer = CustomerService.create_customer(
            firstname="New",
            lastname="Customer",
            phone="+255700000010",
            email="new-customer@example.test",
            university=self.university,
            password="Unique-account-password-839!",
        )
        self.assertTrue(check_password("Unique-account-password-839!", registered_customer.password))

        preferences = CustomerService.save_preferences(
            customer_id=self.customer.pk,
            region=self.region,
            district=self.district,
            ward=self.ward,
            min_price=Decimal("100.00"),
            max_price=Decimal("500.00"),
        )
        self.assertEqual(preferences.customer_id, self.customer.pk)
        self.assertEqual(preferences.min_price, Decimal("100.00"))
        self.assertEqual(CustomerPreference.objects.count(), 1)

        with self.assertRaises(ValidationError):
            CustomerService.save_preferences(
                customer_id=self.customer.pk,
                region=self.other_region,
                district=self.district,
            )
        with self.assertRaises(ValidationError):
            CustomerService.save_preferences(
                customer_id=self.customer.pk,
                min_price=Decimal("500.00"),
                max_price=Decimal("100.00"),
            )

    def test_customer_favourites_are_idempotent_and_reviews_validate_rating(self):
        first = CustomerService.add_favourite(
            customer_id=self.customer.pk,
            property_id=self.property.pk,
        )
        second = CustomerService.add_favourite(
            customer_id=self.customer.pk,
            property_id=self.property.pk,
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Favourite.objects.count(), 1)
        self.assertTrue(CustomerService.remove_favourite(
            customer_id=self.customer.pk,
            property_id=self.property.pk,
        ))
        self.assertFalse(CustomerService.remove_favourite(
            customer_id=self.customer.pk,
            property_id=self.property.pk,
        ))

        now = timezone.now()
        room = Room.objects.create(
            property=self.property,
            room_type="Single",
            price=Decimal("250000.00"),
            capacity=1,
            status=Room.Status.OCCUPIED,
        )
        Booking.objects.create(
            customer=self.customer,
            room=room,
            reference_no="BK-REVIEW-TEST-1",
            request_date=now,
            status=Booking.Status.CONFIRMED,
            confirmed_at=now,
            created_at=now,
            updated_at=now,
        )

        with self.assertRaises(ValidationError):
            CustomerService.submit_review(
                customer_id=self.customer.pk,
                property_id=self.property.pk,
                rating=6,
            )
        review = CustomerService.submit_review(
            customer_id=self.customer.pk,
            property_id=self.property.pk,
            rating=5,
        )
        self.assertEqual(review.rating, 5)

    def test_owner_creation_hashes_password_and_status_is_validated(self):
        owner = AccommodationOwnerService.create_owner(
            firstname="New",
            lastname="Owner",
            phone="+255700000003",
            email="new-owner@example.test",
            password="owner-password",
        )
        self.assertTrue(check_password("owner-password", owner.password))
        updated = AccommodationOwnerService.set_status(
            owner_id=owner.pk,
            status=AccommodationOwner.Status.SUSPENDED,
        )
        self.assertEqual(updated.status, AccommodationOwner.Status.SUSPENDED)
        with self.assertRaises(ValidationError):
            AccommodationOwnerService.set_status(owner_id=owner.pk, status="unknown")

    def test_location_path_creation_is_idempotent(self):
        first = LocationService.create_location_path(
            region_name="Imported Region",
            district_name="Imported District",
            ward_name="Imported Ward",
            street_name="Imported Street",
        )
        second = LocationService.create_location_path(
            region_name="Imported Region",
            district_name="Imported District",
            ward_name="Imported Ward",
            street_name="Imported Street",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Region.objects.filter(name="Imported Region").count(), 1)
        with self.assertRaises(ValidationError):
            LocationService.create_location_path(
                region_name=" ",
                district_name="District",
                ward_name="Ward",
                street_name="Street",
            )

    def test_staff_permissions_and_department_head_rules(self):
        role = Role.objects.create(name="Manager")
        permission_a = Permission.objects.create(name="property.read")
        permission_b = Permission.objects.create(name="property.review")
        StaffService.replace_role_permissions(
            role_id=role.pk,
            permission_ids=[permission_a.pk, permission_b.pk, permission_a.pk],
        )
        self.assertSetEqual(set(role.permissions.values_list("pk", flat=True)), {permission_a.pk, permission_b.pk})

        department = Department.objects.create(name="Operations")
        staff = Staff.objects.create(
            firstname="Department",
            lastname="Head",
            phone="+255700000004",
            email="staff@example.test",
            password="already-hashed",
            branch="Main",
            role=role,
            department=department,
        )
        updated_department = StaffService.assign_department_head(
            department_id=department.pk,
            staff_id=staff.pk,
        )
        self.assertEqual(updated_department.hod_id, staff.pk)

        other_department = Department.objects.create(name="Other")
        with self.assertRaises(ValidationError):
            StaffService.assign_department_head(
                department_id=other_department.pk,
                staff_id=staff.pk,
            )

    def test_staff_role_assignment_cannot_escalate_privileges_or_self_change(self):
        manager_role = Role.objects.create(name="Limited Manager")
        manager_permission = Permission.objects.create(name="staff.manage")
        manager_role.permissions.add(manager_permission)
        actor = Staff.objects.create(
            firstname="Authorized",
            lastname="Manager",
            phone="+255700000040",
            email="authorized-manager@example.test",
            password="already-hashed",
            branch="Main",
            role=manager_role,
        )
        target_role = Role.objects.create(name="Target Staff")
        target = Staff.objects.create(
            firstname="Target",
            lastname="Staff",
            phone="+255700000041",
            email="target-staff@example.test",
            password="already-hashed",
            branch="Main",
            role=target_role,
        )
        escalation_role = Role.objects.create(name="System Administrator")
        elevated_permission = Permission.objects.create(name="system.settings.manage")
        escalation_role.permissions.add(manager_permission, elevated_permission)

        updated = StaffService.assign_role(
            staff_id=target.pk,
            role_id=manager_role.pk,
            assigned_by_staff_id=actor.pk,
        )
        self.assertEqual(updated.role_id, manager_role.pk)
        with self.assertRaises(ValidationError):
            StaffService.assign_role(
                staff_id=target.pk,
                role_id=escalation_role.pk,
                assigned_by_staff_id=actor.pk,
            )
        with self.assertRaises(ValidationError):
            StaffService.assign_role(
                staff_id=actor.pk,
                role_id=target_role.pk,
                assigned_by_staff_id=actor.pk,
            )

    def test_campus_coordinates_are_bounded(self):
        campus = UniversityService.create_campus(
            university_id=self.university.pk,
            name="Main Campus",
            latitude="-6.8000000",
            longitude="39.2000000",
            ward=self.ward,
        )
        self.assertEqual(campus.latitude, Decimal("-6.8000000"))
        with self.assertRaises(ValidationError):
            UniversityService.create_campus(
                university_id=self.university.pk,
                name="Invalid Campus",
                latitude="91",
                longitude="0",
            )
        self.assertEqual(Campus.objects.count(), 1)

    def test_password_reset_is_expiring_one_time_and_hashes_password(self):
        reset = PasswordResetService.request_reset(
            user_type=PasswordReset.UserType.CUSTOMER,
            email=self.customer.email,
        )
        self.assertIsNotNone(reset)
        self.assertNotEqual(reset.token_hash, reset.raw_token)
        self.assertEqual(reset.token_hash, hash_password_reset_token(reset.raw_token))
        updated_customer = PasswordResetService.reset_password(
            token=reset.raw_token,
            new_password="Fresh-password-938!",
        )
        self.assertTrue(check_password("Fresh-password-938!", updated_customer.password))
        self.assertFalse(PasswordReset.objects.filter(pk=reset.pk).exists())
        with self.assertRaises(ValidationError):
            PasswordResetService.reset_password(
                token=reset.raw_token,
                new_password="Another-password-938!",
            )

        expired_reset = PasswordReset.objects.create(
            user_type=PasswordReset.UserType.CUSTOMER,
            user_id=self.customer.pk,
            token_hash=hash_password_reset_token("expired-test-token"),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        with self.assertRaises(ValidationError):
            PasswordResetService.reset_password(
                token="expired-test-token",
                new_password="Fresh-password-938!",
            )
        self.assertFalse(PasswordReset.objects.filter(pk=expired_reset.pk).exists())

    def test_system_settings_audit_and_coordinate_validation(self):
        settings = SystemSettings.objects.create(company_name="Getto")
        updated = SystemService.update_settings(
            settings_id=settings.pk,
            service_fee_percentage="12.50",
            panel_theme=SystemSettings.PanelTheme.DARK,
        )
        self.assertEqual(updated.service_fee_percentage, Decimal("12.50"))
        self.assertEqual(updated.panel_theme, SystemSettings.PanelTheme.DARK)
        with self.assertRaises(ValidationError):
            SystemService.update_settings(settings_id=settings.pk, service_fee_percentage="101")
        with self.assertRaises(ValidationError):
            SystemService.update_settings(settings_id=settings.pk, service_fee_percentage="NaN")

        audit = SystemService.record_audit(
            actor_type=AuditLog.ActorType.CUSTOMER,
            actor_id=self.customer.pk,
            action="view_property",
        )
        self.assertEqual(audit.actor_id, self.customer.pk)
        visit = SystemService.record_visit(
            ip_address="192.0.2.10",
            latitude="-6.8",
            longitude="39.2",
        )
        self.assertEqual(visit.ip_address, "192.0.2.10")
        with self.assertRaises(ValidationError):
            SystemService.record_visit(latitude="-91")
        with self.assertRaises(ValidationError):
            SystemService.record_visit(longitude="Infinity")
