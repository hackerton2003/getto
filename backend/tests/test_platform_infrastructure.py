from decimal import Decimal
from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.authentication.models import AuthSession, PasswordReset
from apps.bookings.models import Booking
from apps.customers.models import Customer, CustomerPreference, Favourite, Report, Review
from apps.house_owners.models import AccommodationOwner
from apps.locations.models import District, Region, Street, Ward
from apps.notifications.models import Notification, WebhookDelivery, WebhookSubscription
from apps.payments.models import Payment, Receipt
from apps.properties.models import Property, PropertyMedia, Room, RoomMedia, Verification, VerificationDocument
from apps.staff.models import Department, Permission, Rank, Role, RolePermission, Staff
from apps.system.models import AuditLog, SystemSettings, VisitorLog
from apps.universities.models import Campus, University


class PlatformInfrastructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_all_models_registered_in_django_admin(self):
        models = [
            PasswordReset, AuthSession,
            Customer, CustomerPreference, Favourite, Review, Report,
            AccommodationOwner,
            Role, Permission, RolePermission, Rank, Department, Staff,
            Property, PropertyMedia, Room, RoomMedia, Verification, VerificationDocument,
            Region, District, Ward, Street,
            University, Campus,
            Booking,
            Payment, Receipt,
            Notification, WebhookSubscription, WebhookDelivery,
            SystemSettings, AuditLog, VisitorLog,
        ]
        registered_models = admin.site._registry.keys()
        for model in models:
            self.assertIn(
                model,
                registered_models,
                f"Model {model.__name__} is not registered in Django admin.",
            )

    def test_api_documentation_endpoints(self):
        # 1. OpenAPI schema
        schema_res = self.client.get(reverse("schema"))
        self.assertEqual(schema_res.status_code, 200)

        # 2. Swagger UI
        swagger_res = self.client.get(reverse("swagger-ui"))
        self.assertEqual(swagger_res.status_code, 200)

        # 3. ReDoc
        redoc_res = self.client.get(reverse("redoc"))
        self.assertEqual(redoc_res.status_code, 200)

    def test_visitor_tracking_middleware(self):
        initial_count = VisitorLog.objects.count()
        response = self.client.get(
            reverse("schema"),
            HTTP_USER_AGENT="TestBrowser/1.0",
            REMOTE_ADDR="192.168.1.100",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(VisitorLog.objects.count(), initial_count + 1)
        visit = VisitorLog.objects.latest("id")
        self.assertEqual(visit.ip_address, "192.168.1.100")
        self.assertEqual(visit.user_agent, "TestBrowser/1.0")

    def test_property_pagination(self):
        region = Region.objects.create(name="Pagination Region")
        district = District.objects.create(region=region, name="Pagination District")
        ward = Ward.objects.create(district=district, name="Pagination Ward")
        street = Street.objects.create(ward=ward, name="Pagination Street")
        owner = AccommodationOwner.objects.create(
            firstname="Page",
            lastname="Owner",
            phone="+255755555551",
            email="page-owner@example.test",
            password="hashed",
        )
        Property.objects.create(
            owner=owner,
            name="Paginated Property",
            street=street,
            latitude=Decimal("-6.8000000"),
            longitude=Decimal("39.2800000"),
            verification_status=Property.VerificationStatus.VERIFIED,
        )

        res = self.client.get(reverse("property-list"))
        self.assertEqual(res.status_code, 200)
        # Should return paginated response structure
        self.assertIn("count", res.data)
        self.assertIn("results", res.data)
        self.assertIn("next", res.data)
        self.assertIn("previous", res.data)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(len(res.data["results"]), 1)
