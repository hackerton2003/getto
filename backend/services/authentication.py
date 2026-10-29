import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import AuthSession, PasswordReset
from apps.customers.models import Customer
from apps.house_owners.models import AccommodationOwner
from apps.staff.models import Staff


def hash_password_reset_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_account_sessions(*, user_type, user_id):
    return AuthSession.objects.filter(
        user_type=user_type,
        user_id=user_id,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


class AccountAuthenticationService:
    USER_MODELS = {
        PasswordReset.UserType.CUSTOMER: Customer,
        PasswordReset.UserType.OWNER: AccommodationOwner,
        PasswordReset.UserType.STAFF: Staff,
    }

    @classmethod
    def authenticate(cls, *, user_type, email, password):
        user_model = cls.USER_MODELS.get(user_type)
        if user_model is None:
            raise ValidationError({"detail": "Invalid account type, email, or password."})
        user = user_model.objects.filter(email__iexact=email).first()
        if (
            user is None
            or user.status != user_model.Status.ACTIVE
            or not check_password(password, user.password)
        ):
            raise ValidationError({"detail": "Invalid account type, email, or password."})
        return user


class PasswordResetService:
    USER_MODELS = {
        PasswordReset.UserType.CUSTOMER: Customer,
        PasswordReset.UserType.OWNER: AccommodationOwner,
        PasswordReset.UserType.STAFF: Staff,
    }

    @classmethod
    def request_reset(cls, *, user_type, email, lifetime=timedelta(hours=1)):
        user_model = cls.USER_MODELS.get(user_type)
        if user_model is None:
            raise ValidationError({"user_type": "Choose a valid account type."})
        user = user_model.objects.filter(email__iexact=email).first()
        if user is None or user.status != user_model.Status.ACTIVE:
            return None

        with transaction.atomic():
            PasswordReset.objects.filter(user_type=user_type, user_id=user.pk).delete()
            raw_token = secrets.token_urlsafe(32)
            reset = PasswordReset.objects.create(
                user_type=user_type,
                user_id=user.pk,
                token_hash=hash_password_reset_token(raw_token),
                expires_at=timezone.now() + lifetime,
            )
            # Keep the raw token only on this in-memory instance so the caller
            # can deliver it once. It is never persisted to the database.
            reset.raw_token = raw_token
            return reset

    @classmethod
    def reset_password(cls, *, token, new_password):
        validate_password(new_password)
        invalid_reset = False
        with transaction.atomic():
            reset = PasswordReset.objects.select_for_update().filter(
                token_hash=hash_password_reset_token(token)
            ).first()
            if reset is None:
                raise ValidationError({"token": "Reset token is invalid or expired."})
            if reset.expires_at <= timezone.now():
                reset.delete()
                invalid_reset = True
            else:
                user_model = cls.USER_MODELS[reset.user_type]
                user = user_model.objects.select_for_update().filter(pk=reset.user_id).first()
                if user is None or user.status != user_model.Status.ACTIVE:
                    reset.delete()
                    invalid_reset = True
                else:
                    user.password = make_password(new_password)
                    user.save(update_fields=("password", "updated_at"))
                    revoke_account_sessions(user_type=reset.user_type, user_id=reset.user_id)
                    reset.delete()
                    return user

        if invalid_reset:
            raise ValidationError({"token": "Reset token is invalid or expired."})
