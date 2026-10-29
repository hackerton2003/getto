from django.urls import path
from apps.authentication.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="api-login"),
    path("refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("logout/", LogoutView.as_view(), name="api-logout"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]
