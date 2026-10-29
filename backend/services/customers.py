from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.customers.models import Customer, CustomerPreference, Favourite, Report, Review
from services.authentication import revoke_account_sessions


class CustomerService:
    @staticmethod
    def create_customer(*, password, **customer_data):
        if not password:
            raise ValidationError({"password": "A password is required."})
        validate_password(password)
        university = customer_data.get("university")
        campus = customer_data.get("campus")
        if campus and university and campus.university_id != university.pk:
            raise ValidationError({"campus": "Campus must belong to the selected university."})
        customer_data["password"] = make_password(password)
        return Customer.objects.create(**customer_data)

    @staticmethod
    def save_preferences(*, customer_id, **preference_data):
        min_price = CustomerService._price(preference_data.get("min_price"), "min_price")
        max_price = CustomerService._price(preference_data.get("max_price"), "max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError({"min_price": "Minimum price cannot exceed maximum price."})

        region = preference_data.get("region")
        district = preference_data.get("district")
        ward = preference_data.get("ward")
        if district and region and district.region_id != region.pk:
            raise ValidationError({"district": "District must belong to the selected region."})
        if ward and district and ward.district_id != district.pk:
            raise ValidationError({"ward": "Ward must belong to the selected district."})
        if ward and region and ward.district.region_id != region.pk:
            raise ValidationError({"ward": "Ward must belong to the selected region."})

        customer = Customer.objects.get(pk=customer_id)
        preference_data["min_price"] = min_price
        preference_data["max_price"] = max_price
        with transaction.atomic():
            preferences, _ = CustomerPreference.objects.update_or_create(
                customer=customer,
                defaults=preference_data,
            )
            return preferences

    @staticmethod
    def _price(value, field_name):
        if value is None:
            return None
        try:
            price = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: "Enter a valid price."}) from None
        if not price.is_finite() or price < 0:
            raise ValidationError({field_name: "Price cannot be negative."})
        return price

    @staticmethod
    def add_favourite(*, customer_id, property_id):
        favourite, _ = Favourite.objects.get_or_create(
            customer_id=customer_id,
            property_id=property_id,
        )
        return favourite

    @staticmethod
    def remove_favourite(*, customer_id, property_id):
        deleted, _ = Favourite.objects.filter(
            customer_id=customer_id,
            property_id=property_id,
        ).delete()
        return deleted > 0

    @staticmethod
    def submit_review(*, customer_id, property_id, rating, comment=None):
        from apps.bookings.models import Booking

        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValidationError({"rating": "Rating must be an integer from 1 to 5."})
        if not Booking.objects.filter(
            customer_id=customer_id,
            room__property_id=property_id,
            status=Booking.Status.CONFIRMED,
        ).exists():
            raise ValidationError({"booking": "A confirmed booking is required to review this property."})
        review, created = Review.objects.get_or_create(
            customer_id=customer_id,
            property_id=property_id,
            defaults={"rating": rating, "comment": comment},
        )
        if not created:
            raise ValidationError({"property": "You have already reviewed this property."})
        return review

    @staticmethod
    def update_review(*, review_id, customer_id, changes):
        review = Review.objects.filter(pk=review_id, customer_id=customer_id).first()
        if review is None:
            return None
        if "rating" in changes and (isinstance(changes["rating"], bool) or not 1 <= changes["rating"] <= 5):
            raise ValidationError({"rating": "Rating must be an integer from 1 to 5."})
        for field, value in changes.items():
            setattr(review, field, value)
        review.status = Review.Status.PENDING
        review.reviewed_by_staff = None
        review.reviewed_at = None
        review.save(update_fields=(*changes.keys(), "status", "reviewed_by_staff", "reviewed_at", "updated_at"))
        return review

    @staticmethod
    def delete_review(*, review_id, customer_id):
        deleted, _ = Review.objects.filter(pk=review_id, customer_id=customer_id).delete()
        return deleted > 0

    @staticmethod
    def report_property(*, customer_id, property_id, reason, description=None):
        if not reason or not reason.strip():
            raise ValidationError({"reason": "A report reason is required."})
        return Report.objects.create(
            customer_id=customer_id,
            property_id=property_id,
            reason=reason.strip(),
            description=description,
        )

    @staticmethod
    def set_status(*, customer_id, status):
        if status not in Customer.Status.values:
            raise ValidationError({"status": "Choose a valid customer status."})
        customer = Customer.objects.get(pk=customer_id)
        customer.status = status
        customer.save(update_fields=("status", "updated_at"))
        if status != Customer.Status.ACTIVE:
            revoke_account_sessions(user_type="customer", user_id=customer.pk)
        return customer
