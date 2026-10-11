from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import status,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.db import models
from tenantsapp.models import Tenant
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PasswordResetOTP
from .serializer import (
    RESET_TOKEN_SALT,
    StaffCreateSerializer,
    ForgotPasswordRequestSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyOTPSerializer,
    changepasswordSerializer,
    StaffDetailSerializer,
   
)
import secrets

User = get_user_model()

OTP_VALID_MINUTES = 10  # must match PasswordResetOTP.is_valid()


# ---------- helpers ----------

def user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone_no": user.phone_no,
        "role": user.role,
        "company_name": Tenant.objects.get(id=user.tenant_id).shop_name if user.tenant_id else None

    }


def mask_target(target, channel):
    """Hide most of the email/phone in the API response."""
    if channel == "email" and "@" in target:
        name, domain = target.split("@", 1)
        return f"{name[:2]}***@{domain}"
    return f"{'*' * max(len(target) - 4, 0)}{target[-4:]}"


def send_otp(channel, target, otp_code):
    message = (
        f"Your password reset code is {otp_code}. "
        f"It expires in {OTP_VALID_MINUTES} minutes. "
        "Do not share it with anyone."
    )

    if channel == "email":
        send_mail(
            subject="Password reset code",
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[target],
            fail_silently=False,
        )
    elif channel == "phone":
        # Plug in your SMS provider here (Twilio, Sparrow SMS, Aakash SMS, ...)
        raise NotImplementedError("Connect an SMS provider in send_otp().")
    else:
        raise ValueError(f"Unsupported delivery channel: {channel}")


def invalid_response(serializer):
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- views ----------

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_response(serializer)

        user = serializer.save()
        return Response(
            {"message": "Registration successful.", "user": user_payload(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_response(serializer)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                
                "user": user_payload(user),
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    """Blacklists the refresh token so it can't be used again."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return invalid_response(serializer)

        serializer.save()  # blacklists the token
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_request"

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return invalid_response(serializer)

        user = serializer.validated_data["user"]
        channel = serializer.validated_data["actual_channel"]
        target = serializer.validated_data["target"]

        with transaction.atomic():
            # Invalidate previous unused OTPs
            PasswordResetOTP.objects.filter(
                user=user,
                target=target,
                is_used=False,
            ).update(
                is_used=True
            )

            # Generate a new OTP
            otp_code = str(secrets.randbelow(900000) + 100000)
            otp_record = PasswordResetOTP.objects.create(
                user=user,
                otp_code=otp_code,
                target=target,
                channel=channel,
            )

            try:
                send_otp(
                    channel,
                    target,
                    otp_record.otp_code,
                )
            except Exception:
                transaction.set_rollback(True)
                return Response(
                    {
                        "message": "Could not send OTP. Please try again later."
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {
                "message": f"OTP sent via {channel}.",
                "target": mask_target(target, channel),
                "expires_in_minutes": PasswordResetOTP.OTP_TTL_MINUTES,
            },
            status=status.HTTP_200_OK,
        )

class VerifyOTPAPIView(APIView):
    """Step 2: check the OTP and hand back a short-lived, signed reset_token."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_response(serializer)

        user = serializer.validated_data["user"]
        otp_record = serializer.validated_data["otp_record"]

        # Stateless token: no extra DB column needed. The OTP stays unused
        # until the password is actually reset, which makes the token single-use.
        reset_token = signing.dumps(
            {"uid": str(user.pk), "otp": otp_record.pk},
            salt=RESET_TOKEN_SALT,
        )

        return Response(
            {
                "message": "OTP verified.",
                "reset_token": reset_token,
                "expires_in_minutes": OTP_VALID_MINUTES,
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPIView(APIView):
    """Step 3: reset_token + new password."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_response(serializer)

        otp_id = serializer.validated_data["otp_record"].pk
        new_password = serializer.validated_data["new_password"]

        with transaction.atomic():
            # Lock the row so two parallel requests can't both use the same token
            otp_record = (
                PasswordResetOTP.objects.select_for_update()
                .select_related("user")
                .filter(pk=otp_id, is_used=False)
                .first()
            )
            if otp_record is None:
                return Response(
                    {"reset_token": ["Invalid or expired reset token."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = otp_record.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])

            # Sign the user out everywhere: blacklist all their refresh tokens
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )

class StaffCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get (self, request):
        # Only admins can view staff
        if request.user.role != "admin":
            return Response(
                {"message": "Only admins can view staff."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Require company setup first
        if request.user.tenant_id is None:
            return Response(
                {"message": "Complete company setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        staff_members = User.objects.filter(tenant_id=request.user.tenant_id, role="staff")
        staff_data = [
            {
                "id": staff.id,
                "username": staff.username,
                "email": staff.email,
                "phone_no": staff.phone_no,
                "role": staff.role,
                "tenant_id": str(staff.tenant_id),
            }
            for staff in staff_members
        ]

        return Response(
            {
                "message": "Staff members retrieved successfully.",
                "staff_members": staff_data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        authentication_classes = [JWTAuthentication]

        # Only admins can create staff
        if request.user.role != "admin":
            return Response(
                {"message": "Only admins can create staff."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Require company setup first
        if request.user.tenant_id is None:
            return Response(
                {"message": "Complete company setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StaffCreateSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        staff = serializer.save()

        return Response(
            {
                "message": "Staff created successfully.",
                "staff": {
                    "id": staff.id,
                    "username": staff.username,
                    "email": staff.email,
                    "phone_no": staff.phone_no,
                    "role": staff.role,
                    "tenant_id": str(staff.tenant_id),
                },
            },
            status=status.HTTP_201_CREATED,
        )

    
class StaffDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_staff(self, request, pk):
        # Only admins can manage staff
        if request.user.role != "admin":
            return None, Response(
                {"message": "Only admins can manage staff."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Require company setup first
        if request.user.tenant_id is None:
            return None, Response(
                {"message": "Complete company setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            staff = User.objects.get(
                pk=pk,
                tenant_id=request.user.tenant_id,
                role="staff",
            )
            return staff, None

        except User.DoesNotExist:
            return None, Response(
                {"message": "Staff member not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # GET: View staff details
    def get(self, request, pk):
        staff, error = self.get_staff(request, pk)
        if error:
            return error

        serializer = StaffDetailSerializer(staff)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT: Fully update staff details
    def put(self, request, pk):
        staff, error = self.get_staff(request, pk)
        if error:
            return error

        serializer = StaffDetailSerializer(
            staff,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    # PATCH: Partially update staff details
    def patch(self, request, pk):
        staff, error = self.get_staff(request, pk)
        if error:
            return error

        serializer = StaffDetailSerializer(
            staff,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    # DELETE: Delete a staff member
    def delete(self, request, pk):
        staff, error = self.get_staff(request, pk)
        if error:
            return error

        staff.delete()

        return Response(
            {"message": "Staff member deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
    
class changepassworAPIview(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = changepasswordSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Blacklist all refresh tokens
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

        





         