from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.authentication.models import PasswordReset
from apps.customers.models import Customer
from apps.house_owners.models import AccommodationOwner
from apps.universities.models import Campus, University
from services.customers import CustomerService
from services.house_owners import AccommodationOwnerService


class LoginRequestSerializer(serializers.Serializer):
	account_type = serializers.ChoiceField(choices=PasswordReset.UserType.choices)
	email = serializers.EmailField()
	password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordValidationMixin:
	def validate_password(self, value):
		try:
			validate_password(value)
		except DjangoValidationError as exc:
			raise serializers.ValidationError(exc.messages) from exc
		return value


class CustomerRegistrationSerializer(PasswordValidationMixin, serializers.Serializer):
	firstname = serializers.CharField(max_length=100)
	lastname = serializers.CharField(max_length=100)
	phone = serializers.CharField(
		max_length=20,
		validators=[UniqueValidator(queryset=Customer.objects.all(), message="A customer with this phone already exists.")],
	)
	email = serializers.EmailField(
		max_length=150,
		validators=[UniqueValidator(queryset=Customer.objects.all(), message="A customer with this email already exists.")],
	)
	password = serializers.CharField(write_only=True, trim_whitespace=False)
	university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
	campus = serializers.PrimaryKeyRelatedField(
		queryset=Campus.objects.all(),
		required=False,
		allow_null=True,
	)
	admission_info = serializers.CharField(max_length=255, required=False, allow_blank=True)

	def validate(self, attrs):
		campus = attrs.get("campus")
		if campus and campus.university_id != attrs["university"].pk:
			raise serializers.ValidationError({"campus": "Campus must belong to the selected university."})
		return attrs

	def create(self, validated_data):
		password = validated_data.pop("password")
		return CustomerService.create_customer(password=password, **validated_data)


class OwnerRegistrationSerializer(PasswordValidationMixin, serializers.Serializer):
	firstname = serializers.CharField(max_length=100)
	lastname = serializers.CharField(max_length=100)
	phone = serializers.CharField(
		max_length=20,
		validators=[UniqueValidator(queryset=AccommodationOwner.objects.all(), message="An owner with this phone already exists.")],
	)
	email = serializers.EmailField(
		max_length=150,
		validators=[UniqueValidator(queryset=AccommodationOwner.objects.all(), message="An owner with this email already exists.")],
	)
	password = serializers.CharField(write_only=True, trim_whitespace=False)

	def create(self, validated_data):
		password = validated_data.pop("password")
		return AccommodationOwnerService.create_owner(password=password, **validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
	account_type = serializers.ChoiceField(choices=PasswordReset.UserType.choices)
	email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
	token = serializers.CharField(write_only=True)
	new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshTokenSerializer(serializers.Serializer):
	refresh_token = serializers.CharField(write_only=True)


class TokenAccountSerializer(serializers.Serializer):
	id = serializers.IntegerField()
	email = serializers.EmailField()


class TokenPairSerializer(serializers.Serializer):
	access = serializers.CharField()
	refresh = serializers.CharField()
	token_type = serializers.ChoiceField(choices=("Bearer",))
	account_type = serializers.ChoiceField(choices=PasswordReset.UserType.choices)
	account = TokenAccountSerializer()


class DetailResponseSerializer(serializers.Serializer):
	detail = serializers.CharField()


class PasswordResetSerializer(serializers.ModelSerializer):
	class Meta:
		model = PasswordReset
		fields = ("id", "user_type", "user_id", "expires_at", "created_at")
		read_only_fields = ("id", "created_at")
