from django.urls import path

# pyrefly: ignore [missing-import]
from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    ForgotPasswordAPIView,
    VerifyOTPAPIView,
    ResetPasswordAPIView,
    StaffCreateAPIView,
    StaffDetailAPIView,
    changepassworAPIview,
)


urlpatterns = [
    path("register/",        RegisterAPIView.as_view(),       name="register"),
    path("login/",           LoginAPIView.as_view(),          name="login"),
    path("logout/",          LogoutAPIView.as_view(),         name="logout"),

    # Step 1-4: User requests OTP
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot-password"),

    # Step 5-7: User submits OTP → receives reset_token
    path("verify-otp/",      VerifyOTPAPIView.as_view(),      name="verify-otp"),

    # Step 8-11: User submits reset_token + new password
    path("reset-password/",  ResetPasswordAPIView.as_view(),  name="reset-password"),

   path(
    "staff/",
    StaffCreateAPIView.as_view(),
    name="staff-create",
), 



    path("staff/<int:pk>/", StaffDetailAPIView.as_view(), name="staff-detail"),

    path("change_password/", changepassworAPIview.as_view(), name="change-password")
]
