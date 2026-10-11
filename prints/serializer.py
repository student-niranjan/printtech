import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PasswordResetOTP

User = get_user_model()

RESET_TOKEN_SALT = "password-reset"
RESET_TOKEN_MAX_AGE = 10 * 60  # seconds, same as the OTP lifetime

PHONE_RE = re.compile(r"^\+?\d{7,15}$")

# Roles a person may pick for themselves at signup. Edit to match your project.
BLOCKED_SIGNUP_ROLES = {"admin", "superadmin", "superuser", "staff"}


# ---------- helpers ----------

def normalize_phone(value):
    return re.sub(r"[\s\-()]", "", value or "")


def find_user(identifier):
    """Look up a user by email, phone number or username."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    return User.objects.filter(
        Q(email__iexact=identifier)
        | Q(username__iexact=identifier)
        | Q(phone_no=normalize_phone(identifier))
    ).first()


def run_password_validators(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))


# ---------- auth ----------

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "phone_no", "role", "password", "confirm_password"]
        extra_kwargs = {"role": {"required": False}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_no(self, value):
        value = normalize_phone(value)
        if not PHONE_RE.match(value):
            raise serializers.ValidationError("Enter a valid phone number.")
        if User.objects.filter(phone_no=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_role(self, value):
        if str(value).lower() in BLOCKED_SIGNUP_ROLES:
            raise serializers.ValidationError("This role cannot be chosen at signup.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        candidate = User(
            username=attrs.get("username"),
            email=attrs.get("email"),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email, phone number or username")
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = find_user(attrs["identifier"])

        # Same message for "no user" and "wrong password" so accounts can't be probed
        if user is None or not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError:
            raise serializers.ValidationError("Invalid or expired refresh token.")

        # A user may only log out their own token
        if str(token.get("user_id")) != str(self.context["request"].user.pk):
            raise serializers.ValidationError("This token does not belong to you.")

        self._token = token
        return value

    def save(self, **kwargs):
        try:
            self._token.blacklist()
        except TokenError:
            pass  # already blacklisted: logout is idempotent


# ---------- password reset ----------

class ForgotPasswordRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email, phone number or username")
    channel = serializers.ChoiceField(
        choices=["email", "phone"],
        required=False,
        help_text="Where to send the OTP. Defaults to the way the identifier was given.",
    )

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        user = find_user(identifier)
        if user is None:
            raise serializers.ValidationError({"identifier": "No account found."})

        channel = attrs.get("channel")
        if not channel:
            if "@" in identifier:
                channel = "email"
            elif PHONE_RE.match(normalize_phone(identifier)):
                channel = "phone"
            else:  # username: use whatever the account has
                channel = "email" if user.email else "phone"

        target = user.email if channel == "email" else user.phone_no
        if not target:
            raise serializers.ValidationError(
                {"channel": f"This account has no {channel} on file."}
            )

        attrs["user"] = user
        attrs["actual_channel"] = channel
        attrs["target"] = target
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    target = serializers.CharField(help_text="The email or phone the OTP was sent to")
    otp_code = serializers.CharField(max_length=10)

    def validate(self, attrs):
        target = attrs["target"].strip()

        otp_record = (
            PasswordResetOTP.objects.select_related("user")
            .filter(target__iexact=target, is_used=False)
            .order_by("-created_at")
            .first()
        )

        # One generic error for every failure so nothing about accounts leaks
        if (
            otp_record is None
            or not otp_record.is_valid()
            or not constant_time_compare(otp_record.otp_code, attrs["otp_code"].strip())
        ):
            raise serializers.ValidationError({"otp_code": "Invalid or expired OTP."})

        attrs["user"] = otp_record.user
        attrs["otp_record"] = otp_record
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        try:
            payload = signing.loads(
                attrs["reset_token"],
                salt=RESET_TOKEN_SALT,
                max_age=RESET_TOKEN_MAX_AGE,
            )
        except signing.BadSignature:  # also covers SignatureExpired
            raise serializers.ValidationError({"reset_token": "Invalid or expired reset token."})

        otp_record = (
            PasswordResetOTP.objects.select_related("user")
            .filter(pk=payload.get("otp"), user_id=payload.get("uid"), is_used=False)
            .first()
        )
        if otp_record is None:
            raise serializers.ValidationError({"reset_token": "Invalid or expired reset token."})

        try:
            validate_password(attrs["new_password"], user=otp_record.user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        attrs["user"] = otp_record.user
        attrs["otp_record"] = otp_record
        return attrs

class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Password for the new staff member.",)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_no",
            "password",
        ]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )
        return value

    def validate_phone_no(self, value):
        value = normalize_phone(value)
        if not PHONE_RE.match(value):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )
        if User.objects.filter(phone_no=value).exists():
            raise serializers.ValidationError(
                "This phone number is already registered."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        request = self.context["request"]

        staff = User(**validated_data)
        staff.set_password(password)
        staff.role = "staff"
        staff.tenant = request.user.tenant
        staff.save()

        return staff

class StaffDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_no",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]
    def update(self, instance, validated_data):
        # Update the staff member's details
        instance.username = validated_data.get("username", instance.username)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()
        return instance


class changepasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({
                "old_password": "Incorrect old password."
            })

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        try:
            validate_password(
                attrs["new_password"],
                user=user
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                "new_password": list(exc.messages)
            })

        return attrs