from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.v1.serializers.authenication import (
    LoginRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshTokenSerializer,
    DetailResponseSerializer,
    TokenPairSerializer,
)
from api.v1.throttling import LoginRateThrottle, PasswordResetRateThrottle
from api.v1.utils import raise_api_validation
from apps.authentication.authentication import (
    create_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)
from services.authentication import AccountAuthenticationService, PasswordResetService


class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)

    @extend_schema(request=LoginRequestSerializer, responses={200: TokenPairSerializer}, operation_id="auth_login")
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            account = AccountAuthenticationService.authenticate(
                user_type=data["account_type"],
                email=data["email"],
                password=data["password"],
            )
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        access_token, refresh_token = create_token_pair(account, data["account_type"])
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "Bearer",
            "account_type": data["account_type"],
            "account": {"id": account.pk, "email": account.email},
        })


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetRateThrottle,)

    @extend_schema(request=PasswordResetRequestSerializer, responses={202: DetailResponseSerializer}, operation_id="auth_password_reset_request")
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset = PasswordResetService.request_reset(
            user_type=serializer.validated_data["account_type"],
            email=serializer.validated_data["email"],
        )
        if reset is not None:
            send_mail(
                "Password reset",
                f"Use this one-time token to reset your password: {reset.raw_token}",
                settings.DEFAULT_FROM_EMAIL,
                [serializer.validated_data["email"]],
                fail_silently=True,
            )
        return Response(
            {"detail": "If the account exists, password reset instructions will be sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetRateThrottle,)

    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None}, operation_id="auth_password_reset_confirm")
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PasswordResetService.reset_password(**serializer.validated_data)
        except DjangoValidationError as exc:
            raise_api_validation(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(request=RefreshTokenSerializer, responses={200: TokenPairSerializer}, operation_id="auth_token_refresh")
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account, account_type, access_token, refresh_token = rotate_refresh_token(
            serializer.validated_data["refresh_token"]
        )
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "token_type": "Bearer",
            "account_type": account_type,
            "account": {"id": account.pk, "email": account.email},
        })


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=RefreshTokenSerializer, responses={204: None}, operation_id="auth_logout")
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revoked = revoke_refresh_token(
            serializer.validated_data["refresh_token"],
            session_id=request.user.session_id,
            account_type=request.user.account_type,
            account_id=request.user.pk,
        )
        if not revoked:
            raise ValidationError({"refresh_token": "Refresh token is invalid or already revoked."})
        return Response(status=status.HTTP_204_NO_CONTENT)
