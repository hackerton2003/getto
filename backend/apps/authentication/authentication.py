from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone as django_timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.authentication.models import AuthSession
from apps.customers.models import Customer
from apps.house_owners.models import AccommodationOwner
from apps.staff.models import Staff


ACCOUNT_MODELS = {
    "customer": Customer,
    "owner": AccommodationOwner,
    "staff": Staff,
}


class AccountPrincipal:
    is_authenticated = True
    is_anonymous = False

    def __init__(self, account, account_type, session):
        self.account = account
        self.account_type = account_type
        self.pk = account.pk
        self.session_id = session.pk

    def __getattr__(self, name):
        return getattr(self.account, name)


def _refresh_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_access_token(account, account_type, session, lifetime):
    issued_at = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(account.pk),
            "account_type": account_type,
            "sid": session.pk,
            "jti": session.access_token_id,
            "iat": issued_at,
            "exp": issued_at + lifetime,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_token_pair(
    account,
    account_type,
    *,
    access_lifetime=timedelta(minutes=15),
    refresh_lifetime=timedelta(days=30),
):
    refresh_token = secrets.token_urlsafe(48)
    session = AuthSession.objects.create(
        user_type=account_type,
        user_id=account.pk,
        access_token_id=secrets.token_urlsafe(24),
        refresh_token_hash=_refresh_hash(refresh_token),
        refresh_expires_at=django_timezone.now() + refresh_lifetime,
    )
    access_token = _encode_access_token(account, account_type, session, access_lifetime)
    return access_token, refresh_token


def create_access_token(account, account_type, *, lifetime=timedelta(minutes=15)):
    access_token, _ = create_token_pair(account, account_type, access_lifetime=lifetime)
    return access_token


def rotate_refresh_token(refresh_token, *, access_lifetime=timedelta(minutes=15)):
    token_hash = _refresh_hash(refresh_token)
    unavailable = False
    with transaction.atomic():
        session = AuthSession.objects.select_for_update().filter(
            refresh_token_hash=token_hash,
            revoked_at__isnull=True,
            refresh_expires_at__gt=django_timezone.now(),
        ).first()
        if session is None:
            raise AuthenticationFailed("Refresh token is invalid, expired, or already used.")
        account_model = ACCOUNT_MODELS.get(session.user_type)
        account = account_model.objects.filter(pk=session.user_id).first() if account_model else None
        if account is None or account.status != account_model.Status.ACTIVE:
            session.revoked_at = django_timezone.now()
            session.save(update_fields=("revoked_at",))
            unavailable = True
        else:
            next_refresh_token = secrets.token_urlsafe(48)
            session.refresh_token_hash = _refresh_hash(next_refresh_token)
            session.access_token_id = secrets.token_urlsafe(24)
            session.save(update_fields=("refresh_token_hash", "access_token_id"))
            access_token = _encode_access_token(account, session.user_type, session, access_lifetime)

    if unavailable:
        raise AuthenticationFailed("Account is unavailable.")
    return account, session.user_type, access_token, next_refresh_token


def revoke_refresh_token(refresh_token, *, session_id, account_type, account_id):
    with transaction.atomic():
        session = AuthSession.objects.select_for_update().filter(
            pk=session_id,
            user_type=account_type,
            user_id=account_id,
            refresh_token_hash=_refresh_hash(refresh_token),
            revoked_at__isnull=True,
        ).first()
        if session is None:
            return False
        session.revoked_at = django_timezone.now()
        session.save(update_fields=("revoked_at",))
        return True


class AccountJWTAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != self.keyword:
            raise AuthenticationFailed("Use the Bearer token authorization scheme.")

        try:
            payload = jwt.decode(
                header[1],
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["sub", "account_type", "sid", "jti", "iat", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Access token is invalid or expired.") from exc

        account_type = payload.get("account_type")
        account_model = ACCOUNT_MODELS.get(account_type)
        if account_model is None:
            raise AuthenticationFailed("Access token account type is invalid.")
        session = AuthSession.objects.filter(
            pk=payload.get("sid"),
            user_type=account_type,
            user_id=payload.get("sub"),
            access_token_id=payload.get("jti"),
            revoked_at__isnull=True,
            refresh_expires_at__gt=django_timezone.now(),
        ).first()
        if session is None:
            raise AuthenticationFailed("Access token session is invalid or revoked.")
        account = account_model.objects.filter(pk=payload.get("sub")).first()
        if account is None or account.status != account_model.Status.ACTIVE:
            raise AuthenticationFailed("Account is unavailable.")
        return AccountPrincipal(account, account_type, session), payload


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class AccountJWTScheme(OpenApiAuthenticationExtension):
        target_class = "apps.authentication.authentication.AccountJWTAuthentication"
        name = "jwtAuth"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
except ImportError:
    pass
