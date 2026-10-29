from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.v1.pagination import StandardResultsSetPagination
from api.v1.serializers.properties import (
    PropertyMediaCreateSerializer,
    PropertyMediaSerializer,
    PropertySerializer,
    RoomMediaCreateSerializer,
    RoomMediaSerializer,
    RoomSerializer,
)
from api.v1.utils import PublicReadOnlyViewSet, raise_api_validation
from apps.properties.filters import PropertyFilter, RoomFilter
from apps.properties.models import Property, PropertyMedia, Room, RoomMedia
from services.properties import PropertyService


class PropertyViewSet(PublicReadOnlyViewSet):
    serializer_class = PropertySerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = PropertyFilter
    search_fields = (
        "name",
        "description",
        "street__name",
        "street__ward__name",
        "street__ward__district__name",
        "street__ward__district__region__name",
    )
    ordering_fields = (
        "name",
        "created_at",
        "total_rooms",
        "available_rooms",
        "id",
    )
    ordering = ("name",)

    def get_queryset(self):
        return Property.objects.filter(
            verification_status=Property.VerificationStatus.VERIFIED,
        ).select_related(
            "owner",
            "street",
            "street__ward",
            "street__ward__district",
            "street__ward__district__region",
        ).distinct()


class RoomViewSet(PublicReadOnlyViewSet):
    serializer_class = RoomSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = RoomFilter
    search_fields = (
        "room_type",
        "facilities",
        "security_info",
        "property__name",
        "property__street__name",
    )
    ordering_fields = (
        "price",
        "capacity",
        "area_sqm",
        "created_at",
        "id",
    )
    ordering = ("price",)

    def get_queryset(self):
        return Room.objects.filter(
            status=Room.Status.AVAILABLE,
            property__verification_status=Property.VerificationStatus.VERIFIED,
        ).select_related("property", "property__street")


class PropertyMediaViewSet(ModelViewSet):
    serializer_class = PropertyMediaSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return (AllowAny(),)
        return (IsAuthenticated(),)

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            if getattr(user, "account_type", None) == "staff":
                queryset = PropertyMedia.objects.all()
            elif getattr(user, "account_type", None) == "owner":
                queryset = PropertyMedia.objects.filter(
                    Q(property__verification_status=Property.VerificationStatus.VERIFIED)
                    | Q(property__owner_id=user.pk)
                )
            else:
                queryset = PropertyMedia.objects.filter(
                    property__verification_status=Property.VerificationStatus.VERIFIED
                )
        else:
            queryset = PropertyMedia.objects.filter(
                property__verification_status=Property.VerificationStatus.VERIFIED
            )
        queryset = queryset.select_related("property")
        property_id = self.request.query_params.get("property_id")
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        return queryset

    def create(self, request, *args, **kwargs):
        if getattr(request.user, "account_type", None) not in ("owner", "staff"):
            return Response(
                {"detail": "Only property owners and staff can upload property media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PropertyMediaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_staff = request.user.account_type == "staff"
        owner_id = None if is_staff else request.user.pk
        try:
            media = PropertyService.upload_property_media(
                property_id=serializer.validated_data["property_id"],
                uploaded_file=serializer.validated_data["file"],
                media_type=serializer.validated_data.get("type"),
                owner_id=owner_id,
                is_staff=is_staff,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(
            PropertyMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        if getattr(request.user, "account_type", None) not in ("owner", "staff"):
            return Response(
                {"detail": "Only property owners and staff can delete property media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        media_id = kwargs.get("pk")
        is_staff = request.user.account_type == "staff"
        owner_id = None if is_staff else request.user.pk
        try:
            PropertyService.delete_property_media(
                media_id=media_id,
                owner_id=owner_id,
                is_staff=is_staff,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomMediaViewSet(ModelViewSet):
    serializer_class = RoomMediaSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return (AllowAny(),)
        return (IsAuthenticated(),)

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            if getattr(user, "account_type", None) == "staff":
                queryset = RoomMedia.objects.all()
            elif getattr(user, "account_type", None) == "owner":
                queryset = RoomMedia.objects.filter(
                    Q(room__property__verification_status=Property.VerificationStatus.VERIFIED)
                    | Q(room__property__owner_id=user.pk)
                )
            else:
                queryset = RoomMedia.objects.filter(
                    room__status=Room.Status.AVAILABLE,
                    room__property__verification_status=Property.VerificationStatus.VERIFIED,
                )
        else:
            queryset = RoomMedia.objects.filter(
                room__status=Room.Status.AVAILABLE,
                room__property__verification_status=Property.VerificationStatus.VERIFIED,
            )
        queryset = queryset.select_related("room", "room__property")
        room_id = self.request.query_params.get("room_id")
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            queryset = queryset.filter(room__property_id=property_id)
        return queryset

    def create(self, request, *args, **kwargs):
        if getattr(request.user, "account_type", None) not in ("owner", "staff"):
            return Response(
                {"detail": "Only property owners and staff can upload room media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RoomMediaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_staff = request.user.account_type == "staff"
        owner_id = None if is_staff else request.user.pk
        try:
            media = PropertyService.upload_room_media(
                room_id=serializer.validated_data["room_id"],
                uploaded_file=serializer.validated_data["file"],
                media_type=serializer.validated_data.get("type"),
                owner_id=owner_id,
                is_staff=is_staff,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(
            RoomMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        if getattr(request.user, "account_type", None) not in ("owner", "staff"):
            return Response(
                {"detail": "Only property owners and staff can delete room media."},
                status=status.HTTP_403_FORBIDDEN,
            )
        media_id = kwargs.get("pk")
        is_staff = request.user.account_type == "staff"
        owner_id = None if is_staff else request.user.pk
        try:
            PropertyService.delete_room_media(
                media_id=media_id,
                owner_id=owner_id,
                is_staff=is_staff,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
