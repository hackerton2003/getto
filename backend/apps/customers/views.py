from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.permissions import IsCustomer
from api.v1.serializers.authenication import CustomerRegistrationSerializer
from api.v1.serializers.customers import (
    CustomerPreferenceSerializer,
    CustomerPreferencesInputSerializer,
    CustomerProfileSerializer,
    FavouriteCreateSerializer,
    FavouriteSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ReviewCreateSerializer,
    ReviewUpdateSerializer,
    ReviewSerializer,
)
from api.v1.utils import raise_api_validation
from apps.authentication.authentication import create_token_pair
from apps.authentication.models import PasswordReset
from apps.customers.models import CustomerPreference, Favourite, Review
from services.customers import CustomerService


class CustomerRegistrationView(generics.CreateAPIView):
    serializer_class = CustomerRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        access_token, refresh_token = create_token_pair(account, PasswordReset.UserType.CUSTOMER)
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "Bearer",
            "account_type": PasswordReset.UserType.CUSTOMER,
            "account": {"id": account.pk, "email": account.email},
        }, status=status.HTTP_201_CREATED)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = (IsCustomer,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user.account


class CustomerPreferencesView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: CustomerPreferenceSerializer}, operation_id="customer_preferences_retrieve")
    def get(self, request):
        preferences = get_object_or_404(CustomerPreference, customer_id=request.user.pk)
        return Response(CustomerPreferenceSerializer(preferences).data)

    @extend_schema(request=CustomerPreferencesInputSerializer, responses={200: CustomerPreferenceSerializer}, operation_id="customer_preferences_replace")
    def put(self, request):
        return self._save(request, partial=False)

    @extend_schema(request=CustomerPreferencesInputSerializer, responses={200: CustomerPreferenceSerializer}, operation_id="customer_preferences_update")
    def patch(self, request):
        return self._save(request, partial=True)

    def _save(self, request, *, partial):
        serializer = CustomerPreferencesInputSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            preferences = CustomerService.save_preferences(
                customer_id=request.user.pk,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        result_serializer = CustomerPreferenceSerializer(preferences)
        return Response(result_serializer.data)


class FavouriteListCreateView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={200: FavouriteSerializer(many=True)}, operation_id="customer_favourites_list")
    def get(self, request):
        favourites = Favourite.objects.filter(customer_id=request.user.pk).select_related("property")
        serializer = FavouriteSerializer(favourites, many=True)
        return Response(serializer.data)

    @extend_schema(request=FavouriteCreateSerializer, responses={201: FavouriteSerializer}, operation_id="customer_favourites_create")
    def post(self, request):
        serializer = FavouriteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            favourite = CustomerService.add_favourite(
                customer_id=request.user.pk,
                property_id=serializer.validated_data["property_id"].pk,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(
            FavouriteSerializer(favourite).data,
            status=status.HTTP_201_CREATED,
        )


class FavouriteDetailView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(responses={204: None}, operation_id="customer_favourites_delete")
    def delete(self, request, property_id):
        removed = CustomerService.remove_favourite(
            customer_id=request.user.pk,
            property_id=property_id,
        )
        if not removed:
            raise NotFound("Favourite not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewListCreateView(APIView):
    def get_permissions(self):
        return (IsCustomer(),) if self.request.method == "POST" else (AllowAny(),)

    @extend_schema(responses={200: ReviewSerializer(many=True)}, operation_id="reviews_list")
    def get(self, request):
        queryset = Review.objects.filter(status=Review.Status.APPROVED).select_related("customer", "property")
        property_id = request.query_params.get("property_id")
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        serializer = ReviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer}, operation_id="reviews_create")
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review = CustomerService.submit_review(
                customer_id=request.user.pk,
                property_id=serializer.validated_data["property_id"].pk,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment"),
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    permission_classes = (IsCustomer,)

    @extend_schema(request=ReviewUpdateSerializer, responses={200: ReviewSerializer}, operation_id="reviews_update")
    def patch(self, request, review_id):
        serializer = ReviewUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review = CustomerService.update_review(
                review_id=review_id,
                customer_id=request.user.pk,
                changes=serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        if review is None:
            raise NotFound("Review not found.")
        return Response(ReviewSerializer(review).data)

    @extend_schema(responses={204: None}, operation_id="reviews_delete")
    def delete(self, request, review_id):
        if not CustomerService.delete_review(review_id=review_id, customer_id=request.user.pk):
            raise NotFound("Review not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportCreateSerializer
    permission_classes = (IsCustomer,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report = CustomerService.report_property(
                customer_id=request.user.pk,
                property_id=serializer.validated_data["property_id"].pk,
                reason=serializer.validated_data["reason"],
                description=serializer.validated_data.get("description"),
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
