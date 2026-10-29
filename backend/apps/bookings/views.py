from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.permissions import IsCustomer, IsOwner, IsStaff
from api.v1.serializers.bookings import (
    BookingCreateRequestSerializer,
    BookingSerializer,
    StaleBookingExpirySerializer,
    StaleBookingExpiryResponseSerializer,
)
from api.v1.utils import raise_api_validation
from apps.bookings.models import Booking
from services.bookings import BookingService


class BookingCreateView(APIView):
    """Legacy view for booking creation."""
    @extend_schema(request=BookingCreateRequestSerializer, responses={201: BookingSerializer}, operation_id="legacy_booking_create")
    def post(self, request):
        request_serializer = BookingCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        try:
            booking = BookingService.create_booking(
                customer_id=validated_data["customer"].pk,
                room_id=validated_data["room"].pk,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)

        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class BookingListCreateView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: BookingSerializer(many=True)}, operation_id="bookings_list")
    def get(self, request):
        bookings = Booking.objects.filter(customer_id=request.user.pk).select_related("room", "room__property")
        return Response(BookingSerializer(bookings, many=True).data)

    @extend_schema(request=BookingCreateRequestSerializer, responses={201: BookingSerializer}, operation_id="bookings_create")
    def post(self, request):
        serializer = BookingCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = BookingService.create_booking(
                customer_id=request.user.pk,
                room_id=serializer.validated_data["room_id"].pk,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: BookingSerializer}, operation_id="bookings_retrieve")
    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("room", "room__property"),
            pk=booking_id,
            customer_id=request.user.pk,
        )
        return Response(BookingSerializer(booking).data)


class BookingCancelView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(request=None, responses={200: BookingSerializer}, operation_id="bookings_cancel")
    def post(self, request, booking_id):
        get_object_or_404(Booking, pk=booking_id, customer_id=request.user.pk)
        try:
            booking = BookingService.transition(
                booking_id=booking_id,
                status=Booking.Status.CANCELLED,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(BookingSerializer(booking).data)


class BookingDecisionView(APIView):
    permission_classes = (IsStaff,)

    @extend_schema(request=None, responses={200: BookingSerializer}, operation_id="bookings_staff_decision")
    def post(self, request, booking_id, decision):
        if decision not in ("confirm", "reject"):
            raise NotFound("Booking decision not found.")
        try:
            booking = BookingService.transition(
                booking_id=booking_id,
                status=(Booking.Status.CONFIRMED if decision == "confirm" else Booking.Status.REJECTED),
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(BookingSerializer(booking).data)


class OwnerBookingListView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={200: BookingSerializer(many=True)}, operation_id="owner_bookings_list")
    def get(self, request):
        bookings = Booking.objects.filter(
            room__property__owner_id=request.user.pk,
        ).select_related("customer", "room", "room__property")
        status_filter = request.query_params.get("status")
        if status_filter:
            bookings = bookings.filter(status=status_filter)
        return Response(BookingSerializer(bookings, many=True).data)


class OwnerBookingDecisionView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(request=None, responses={200: BookingSerializer}, operation_id="owner_bookings_decision")
    def post(self, request, booking_id, decision):
        if decision not in ("confirm", "reject"):
            raise NotFound("Booking decision not found.")
        booking = get_object_or_404(
            Booking.objects.select_related("room__property"),
            pk=booking_id,
            room__property__owner_id=request.user.pk,
        )
        try:
            booking = BookingService.transition(
                booking_id=booking.pk,
                status=(Booking.Status.CONFIRMED if decision == "confirm" else Booking.Status.REJECTED),
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingExpireStaleView(APIView):
    permission_classes = (IsStaff,)

    @extend_schema(request=StaleBookingExpirySerializer, responses={200: StaleBookingExpiryResponseSerializer}, operation_id="staff_expire_stale_bookings")
    def post(self, request):
        serializer = StaleBookingExpirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expired = BookingService.expire_stale_bookings(
            expiry_hours=serializer.validated_data["hours"],
            limit=serializer.validated_data.get("limit"),
        )
        return Response({
            "expired_count": len(expired),
            "expired_booking_ids": [b.id for b in expired],
        }, status=status.HTTP_200_OK)
