from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Sum

from apps.house_owners.models import AccommodationOwner
from services.authentication import revoke_account_sessions


class AccommodationOwnerService:
    @staticmethod
    def create_owner(*, password, **owner_data):
        if not password:
            raise ValidationError({"password": "A password is required."})
        validate_password(password)
        owner_data["password"] = make_password(password)
        return AccommodationOwner.objects.create(**owner_data)

    @staticmethod
    def set_status(*, owner_id, status):
        if status not in AccommodationOwner.Status.values:
            raise ValidationError({"status": "Choose a valid owner status."})
        owner = AccommodationOwner.objects.get(pk=owner_id)
        owner.status = status
        owner.save(update_fields=("status", "updated_at"))
        if status != AccommodationOwner.Status.ACTIVE:
            revoke_account_sessions(user_type="owner", user_id=owner.pk)
        return owner

    @staticmethod
    def get_owner_dashboard_stats(*, owner_id):
        from apps.bookings.models import Booking
        from apps.customers.models import Review
        from apps.payments.models import Payment
        from apps.properties.models import Property, Room

        properties = Property.objects.filter(owner_id=owner_id)
        total_properties = properties.count()
        verified_properties = properties.filter(verification_status=Property.VerificationStatus.VERIFIED).count()
        pending_properties = properties.filter(verification_status=Property.VerificationStatus.PENDING).count()
        rejected_properties = properties.filter(verification_status=Property.VerificationStatus.REJECTED).count()

        rooms = Room.objects.filter(property__owner_id=owner_id)
        total_rooms = rooms.count()
        available_rooms = rooms.filter(status=Room.Status.AVAILABLE).count()
        occupied_rooms = rooms.filter(status=Room.Status.OCCUPIED).count()
        reserved_rooms = rooms.filter(status=Room.Status.RESERVED).count()
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 2) if total_rooms > 0 else 0.0

        bookings = Booking.objects.filter(room__property__owner_id=owner_id)
        total_bookings = bookings.count()
        pending_bookings = bookings.filter(status=Booking.Status.PENDING).count()
        confirmed_bookings = bookings.filter(status=Booking.Status.CONFIRMED).count()
        cancelled_bookings = bookings.filter(status=Booking.Status.CANCELLED).count()
        rejected_bookings = bookings.filter(status=Booking.Status.REJECTED).count()
        expired_bookings = bookings.filter(status=Booking.Status.EXPIRED).count()

        completed_payments = Payment.objects.filter(
            booking__room__property__owner_id=owner_id,
            status=Payment.Status.COMPLETED,
        )
        rev_agg = completed_payments.aggregate(
            rental_revenue=Sum("rental_amount"),
            total_revenue=Sum("total_amount"),
            count=Count("id"),
        )
        total_revenue = float(rev_agg["rental_revenue"] or 0)
        total_gross_revenue = float(rev_agg["total_revenue"] or 0)
        total_paid_transactions = rev_agg["count"] or 0

        reviews = Review.objects.filter(
            property__owner_id=owner_id,
            status=Review.Status.APPROVED,
        )
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"]
        average_rating = round(float(avg_rating), 2) if avg_rating is not None else 0.0
        rating_breakdown = {
            str(star): reviews.filter(rating=star).count() for star in range(1, 6)
        }

        property_summaries = []
        for prop in properties:
            p_rooms = rooms.filter(property=prop)
            p_total_rooms = p_rooms.count()
            p_occupied_rooms = p_rooms.filter(status=Room.Status.OCCUPIED).count()
            p_occupancy = round((p_occupied_rooms / p_total_rooms) * 100, 2) if p_total_rooms > 0 else 0.0
            p_bookings = bookings.filter(room__property=prop).count()
            p_payments = completed_payments.filter(booking__room__property=prop)
            p_revenue = float(p_payments.aggregate(rev=Sum("rental_amount"))["rev"] or 0)
            p_reviews = reviews.filter(property=prop)
            p_avg_rating = p_reviews.aggregate(avg=Avg("rating"))["avg"]
            property_summaries.append({
                "id": prop.pk,
                "name": prop.name,
                "verification_status": prop.verification_status,
                "total_rooms": p_total_rooms,
                "available_rooms": p_rooms.filter(status=Room.Status.AVAILABLE).count(),
                "occupied_rooms": p_occupied_rooms,
                "occupancy_rate": p_occupancy,
                "total_bookings": p_bookings,
                "total_revenue": p_revenue,
                "total_reviews": p_reviews.count(),
                "average_rating": round(float(p_avg_rating), 2) if p_avg_rating is not None else 0.0,
            })

        return {
            "summary": {
                "total_properties": total_properties,
                "total_rooms": total_rooms,
                "available_rooms": available_rooms,
                "occupied_rooms": occupied_rooms,
                "reserved_rooms": reserved_rooms,
                "occupancy_rate": occupancy_rate,
                "total_bookings": total_bookings,
                "total_revenue": total_revenue,
                "total_reviews": total_reviews,
                "average_rating": average_rating,
            },
            "properties": {
                "total": total_properties,
                "verified": verified_properties,
                "pending": pending_properties,
                "rejected": rejected_properties,
            },
            "rooms": {
                "total": total_rooms,
                "available": available_rooms,
                "occupied": occupied_rooms,
                "reserved": reserved_rooms,
                "occupancy_rate": occupancy_rate,
            },
            "bookings": {
                "total": total_bookings,
                "pending": pending_bookings,
                "confirmed": confirmed_bookings,
                "cancelled": cancelled_bookings,
                "rejected": rejected_bookings,
                "expired": expired_bookings,
            },
            "revenue": {
                "total_revenue": total_revenue,
                "gross_revenue": total_gross_revenue,
                "completed_transactions": total_paid_transactions,
            },
            "reviews": {
                "total": total_reviews,
                "average_rating": average_rating,
                "rating_breakdown": rating_breakdown,
            },
            "property_summaries": property_summaries,
        }
