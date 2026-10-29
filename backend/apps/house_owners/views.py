from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.permissions import IsOwner
from api.v1.serializers.authenication import OwnerRegistrationSerializer
from api.v1.serializers.house_owners import OwnerProfileSerializer
from api.v1.serializers.properties import (
    OwnerPropertyCreateSerializer,
    OwnerPropertyUpdateSerializer,
    OwnerRoomCreateSerializer,
    PropertyMediaSerializer,
    PropertyMediaUploadSerializer,
    PropertySerializer,
    RoomMediaSerializer,
    RoomMediaUploadSerializer,
    RoomSerializer,
    VerificationDocumentCreateSerializer,
    VerificationDocumentSerializer,
    VerificationSerializer,
    VerificationSubmitSerializer,
)
from api.v1.utils import raise_api_validation
from apps.authentication.authentication import create_token_pair
from apps.authentication.models import PasswordReset
from apps.properties.models import Property, PropertyMedia, Room, RoomMedia, Verification
from services.house_owners import AccommodationOwnerService
from services.properties import PropertyService
from services.verifications import VerificationService


class OwnerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = OwnerProfileSerializer
    permission_classes = (IsOwner,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user.account


class OwnerDashboardView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={200: {"type": "object", "additionalProperties": True}}, operation_id="owner_dashboard_retrieve")
    def get(self, request):
        stats = AccommodationOwnerService.get_owner_dashboard_stats(owner_id=request.user.pk)
        return Response(stats)


class OwnerRegistrationView(generics.CreateAPIView):
    serializer_class = OwnerRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        access_token, refresh_token = create_token_pair(account, PasswordReset.UserType.OWNER)
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "Bearer",
            "account_type": PasswordReset.UserType.OWNER,
            "account": {"id": account.pk, "email": account.email},
        }, status=status.HTTP_201_CREATED)


class OwnerPropertyListView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={200: PropertySerializer(many=True)}, operation_id="owner_properties_list")
    def get(self, request):
        properties = Property.objects.filter(owner_id=request.user.pk)
        return Response(PropertySerializer(properties, many=True).data)

    @extend_schema(request=OwnerPropertyCreateSerializer, responses={201: PropertySerializer}, operation_id="owner_properties_create")
    def post(self, request):
        serializer = OwnerPropertyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        property_instance = Property.objects.create(
            owner=request.user.account,
            **serializer.validated_data,
        )
        return Response(PropertySerializer(property_instance).data, status=status.HTTP_201_CREATED)


class OwnerPropertyDetailView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(request=OwnerPropertyUpdateSerializer, responses={200: PropertySerializer}, operation_id="owner_properties_update")
    def patch(self, request, property_id):
        serializer = OwnerPropertyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            property_instance = PropertyService.update_owner_property(
                property_id=property_id,
                owner_id=request.user.pk,
                changes=serializer.validated_data,
            )
        except Property.DoesNotExist as exc:
            raise NotFound("Property not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(PropertySerializer(property_instance).data)


class OwnerRoomCreateView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(request=OwnerRoomCreateSerializer, responses={201: RoomSerializer}, operation_id="owner_rooms_create")
    def post(self, request, property_id):
        property_instance = get_object_or_404(
            Property,
            pk=property_id,
            owner_id=request.user.pk,
        )
        serializer = OwnerRoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room = PropertyService.create_room(
                property_id=property_instance.pk,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class OwnerPropertyMediaView(APIView):
    permission_classes = (IsOwner,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(responses={200: PropertyMediaSerializer(many=True)}, operation_id="owner_property_media_list")
    def get(self, request, property_id):
        property_instance = get_object_or_404(
            Property,
            pk=property_id,
            owner_id=request.user.pk,
        )
        media = property_instance.media.all()
        return Response(PropertyMediaSerializer(media, many=True, context={"request": request}).data)

    @extend_schema(request=PropertyMediaUploadSerializer, responses={201: PropertyMediaSerializer}, operation_id="owner_property_media_create")
    def post(self, request, property_id):
        property_instance = get_object_or_404(
            Property,
            pk=property_id,
            owner_id=request.user.pk,
        )
        serializer = PropertyMediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            media = PropertyService.upload_property_media(
                property_id=property_instance.pk,
                uploaded_file=serializer.validated_data["file"],
                media_type=serializer.validated_data.get("type"),
                owner_id=request.user.pk,
                is_staff=False,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(
            PropertyMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OwnerPropertyMediaDetailView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={204: None}, operation_id="owner_property_media_delete")
    def delete(self, request, property_id, media_id):
        get_object_or_404(Property, pk=property_id, owner_id=request.user.pk)
        media = get_object_or_404(PropertyMedia, pk=media_id, property_id=property_id)
        try:
            PropertyService.delete_property_media(
                media_id=media.pk,
                owner_id=request.user.pk,
                is_staff=False,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnerRoomMediaView(APIView):
    permission_classes = (IsOwner,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(responses={200: RoomMediaSerializer(many=True)}, operation_id="owner_room_media_list")
    def get(self, request, room_id):
        room = get_object_or_404(
            Room,
            pk=room_id,
            property__owner_id=request.user.pk,
        )
        media = room.media.all()
        return Response(RoomMediaSerializer(media, many=True, context={"request": request}).data)

    @extend_schema(request=RoomMediaUploadSerializer, responses={201: RoomMediaSerializer}, operation_id="owner_room_media_create")
    def post(self, request, room_id):
        room = get_object_or_404(
            Room,
            pk=room_id,
            property__owner_id=request.user.pk,
        )
        serializer = RoomMediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            media = PropertyService.upload_room_media(
                room_id=room.pk,
                uploaded_file=serializer.validated_data["file"],
                media_type=serializer.validated_data.get("type"),
                owner_id=request.user.pk,
                is_staff=False,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(
            RoomMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OwnerRoomMediaDetailView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={204: None}, operation_id="owner_room_media_delete")
    def delete(self, request, room_id, media_id):
        room = get_object_or_404(
            Room,
            pk=room_id,
            property__owner_id=request.user.pk,
        )
        media = get_object_or_404(RoomMedia, pk=media_id, room_id=room.pk)
        try:
            PropertyService.delete_room_media(
                media_id=media.pk,
                owner_id=request.user.pk,
                is_staff=False,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OwnerVerificationListView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={200: VerificationSerializer(many=True)}, operation_id="owner_verifications_list")
    def get(self, request):
        verifications = Verification.objects.filter(
            property__owner_id=request.user.pk,
        ).select_related("property").prefetch_related("documents")
        return Response(VerificationSerializer(verifications, many=True).data)


class OwnerVerificationSubmitView(APIView):
    permission_classes = (IsOwner,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(request=VerificationSubmitSerializer, responses={201: VerificationSerializer}, operation_id="owner_verifications_create")
    def post(self, request, property_id):
        property_instance = get_object_or_404(
            Property,
            pk=property_id,
            owner_id=request.user.pk,
        )
        serializer = VerificationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            verification = VerificationService.submit(
                property_id=property_instance.pk,
                owner_id=request.user.pk,
                documents=[serializer.validated_data],
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(VerificationSerializer(verification).data, status=status.HTTP_201_CREATED)


class OwnerVerificationDocumentsView(APIView):
    permission_classes = (IsOwner,)

    @extend_schema(responses={200: VerificationDocumentSerializer(many=True)}, operation_id="owner_verification_documents_list")
    def get(self, request, verification_id):
        verification = get_object_or_404(
            Verification,
            pk=verification_id,
            property__owner_id=request.user.pk,
        )
        documents = verification.documents.all()
        return Response(VerificationDocumentSerializer(documents, many=True).data)

    @extend_schema(request=VerificationDocumentCreateSerializer, responses={201: VerificationDocumentSerializer}, operation_id="owner_verification_documents_create")
    def post(self, request, verification_id):
        serializer = VerificationDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = VerificationService.add_document(
                verification_id=verification_id,
                owner_id=request.user.pk,
                **serializer.validated_data,
            )
        except Verification.DoesNotExist as exc:
            raise NotFound("Verification not found.") from exc
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(VerificationDocumentSerializer(document).data, status=status.HTTP_201_CREATED)
