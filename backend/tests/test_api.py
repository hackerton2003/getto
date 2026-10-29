from django.contrib.auth.hashers import make_password, check_password
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from api.v1.authentication import create_access_token
from apps.customers.models import Customer
from apps.authentication.models import AuthSession, PasswordReset
from apps.locations.models import Region
from apps.staff.models import Permission, Role, Staff
from apps.universities.models import University
from services.authentication import PasswordResetService


class VersionedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.university = University.objects.create(name="API Test University")
        self.customer = Customer.objects.create(
            firstname="API",
            lastname="Customer",
            phone="+255711111111",
            email="api-customer@example.test",
            password=make_password("A-secure-test-password-938!"),
            university=self.university,
        )

    def test_login_returns_bearer_token_and_token_accesses_own_profile(self):
        response = self.client.post(
            reverse("api-login"),
            {
                "account_type": "customer",
                "email": self.customer.email,
                "password": "A-secure-test-password-938!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertEqual(response.data["account"]["id"], self.customer.pk)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get(reverse("customer-profile"))
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["email"], self.customer.email)
        self.assertNotIn("password", profile.data)

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            reverse("api-login"),
            {
                "account_type": "customer",
                "email": self.customer.email,
                "password": "incorrect-password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access", response.data)

    def test_refresh_rotates_tokens_and_logout_revokes_the_session(self):
        login = self.client.post(
            reverse("api-login"),
            {
                "account_type": "customer",
                "email": self.customer.email,
                "password": "A-secure-test-password-938!",
            },
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        old_access = login.data["access"]
        old_refresh = login.data["refresh"]
        session = AuthSession.objects.get(user_id=self.customer.pk)
        self.assertNotEqual(session.refresh_token_hash, old_refresh)

        refreshed = self.client.post(
            reverse("api-token-refresh"),
            {"refresh_token": old_refresh},
            format="json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(refreshed.data["refresh"], old_refresh)
        self.assertEqual(self.client.get(reverse("customer-profile"), HTTP_AUTHORIZATION=f"Bearer {old_access}").status_code, 401)

        replay = self.client.post(
            reverse("api-token-refresh"),
            {"refresh_token": old_refresh},
            format="json",
        )
        self.assertEqual(replay.status_code, 401)

        current_access = refreshed.data["access"]
        current_refresh = refreshed.data["refresh"]
        logout = self.client.post(
            reverse("api-logout"),
            {"refresh_token": current_refresh},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {current_access}",
        )
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(self.client.get(reverse("customer-profile"), HTTP_AUTHORIZATION=f"Bearer {current_access}").status_code, 401)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)

    def test_password_reset_revokes_existing_access_sessions(self):
        login = self.client.post(
            reverse("api-login"),
            {
                "account_type": "customer",
                "email": self.customer.email,
                "password": "A-secure-test-password-938!",
            },
            format="json",
        )
        access_token = login.data["access"]
        reset = PasswordResetService.request_reset(
            user_type="customer",
            email=self.customer.email,
        )
        PasswordResetService.reset_password(
            token=reset.raw_token,
            new_password="New-unique-secure-password-839!",
        )
        profile = self.client.get(
            reverse("customer-profile"),
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(profile.status_code, 401)

    def test_password_reset_request_accepts_account_type(self):
        response = self.client.post(
            reverse("password-reset-request"),
            {
                "account_type": "customer",
                "email": self.customer.email,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(PasswordReset.objects.filter(
            user_type="customer",
            user_id=self.customer.pk,
        ).count(), 1)

    def test_refresh_revokes_session_if_account_is_inactive(self):
        login = self.client.post(
            reverse("api-login"),
            {
                "account_type": "customer",
                "email": self.customer.email,
                "password": "A-secure-test-password-938!",
            },
            format="json",
        )
        session = AuthSession.objects.get(user_id=self.customer.pk)
        self.customer.status = Customer.Status.SUSPENDED
        self.customer.save(update_fields=("status",))
        response = self.client.post(
            reverse("api-token-refresh"),
            {"refresh_token": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)

    def test_customer_registration_creates_hashed_password(self):
        response = self.client.post(
            reverse("customer-register"),
            {
                "firstname": "New",
                "lastname": "Customer",
                "phone": "+255711111112",
                "email": "new-api-customer@example.test",
                "password": "A-different-secure-password-938!",
                "university": self.university.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        account = Customer.objects.get(email="new-api-customer@example.test")
        self.assertTrue(check_password("A-different-secure-password-938!", account.password))
        self.assertIn("access", response.data)

    def test_customer_registration_rejects_duplicate_phone(self):
        response = self.client.post(
            reverse("customer-register"),
            {
                "firstname": "Duplicate",
                "lastname": "Phone",
                "phone": self.customer.phone,
                "email": "duplicate-phone@example.test",
                "password": "A-different-secure-password-938!",
                "university": self.university.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)
        self.assertEqual(Customer.objects.filter(phone=self.customer.phone).count(), 1)

    def test_private_profile_requires_authentication(self):
        response = self.client.get(reverse("customer-profile"))
        self.assertEqual(response.status_code, 401)

    def test_reference_data_is_public(self):
        Region.objects.create(name="Public API Region")
        response = self.client.get("/api/v1/locations/regions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Public API Region")


class StaffManagementApiTests(TestCase):
    def setUp(self):
        self.manage_permission = Permission.objects.create(name="staff.manage")
        self.manager_role = Role.objects.create(name="API Staff Manager")
        self.manager_role.permissions.add(self.manage_permission)
        self.basic_role = Role.objects.create(name="API Basic Staff")
        self.elevated_role = Role.objects.create(name="API Elevated Staff")
        elevated_permission = Permission.objects.create(name="system.settings.manage")
        self.elevated_role.permissions.add(self.manage_permission, elevated_permission)
        self.manager = Staff.objects.create(
            firstname="API",
            lastname="Manager",
            phone="+255744444441",
            email="api-manager@example.test",
            password="already-hashed",
            branch="Main",
            role=self.manager_role,
        )
        self.target = Staff.objects.create(
            firstname="API",
            lastname="Target",
            phone="+255744444442",
            email="api-target@example.test",
            password="already-hashed",
            branch="Main",
            role=self.basic_role,
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.manager, 'staff')}"
        )

    def test_manager_can_assign_permitted_role_but_cannot_escalate_or_self_change(self):
        assign_url = reverse("staff-role-assignment", kwargs={"staff_id": self.target.pk})
        permitted = self.client.patch(assign_url, {"role_id": self.manager_role.pk}, format="json")
        self.assertEqual(permitted.status_code, 200)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role_id, self.manager_role.pk)

        escalation = self.client.patch(assign_url, {"role_id": self.elevated_role.pk}, format="json")
        self.assertEqual(escalation.status_code, 400)
        self_role = self.client.patch(
            reverse("staff-role-assignment", kwargs={"staff_id": self.manager.pk}),
            {"role_id": self.basic_role.pk},
            format="json",
        )
        self.assertEqual(self_role.status_code, 400)

    def test_staff_without_management_permission_cannot_create_staff(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {create_access_token(self.target, 'staff')}")
        response = client.post(
            reverse("staff-accounts"),
            {
                "firstname": "Blocked",
                "lastname": "Create",
                "phone": "+255744444443",
                "email": "blocked-create@example.test",
                "password": "Strong-unique-password-852!",
                "branch": "Main",
                "role": self.basic_role.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
