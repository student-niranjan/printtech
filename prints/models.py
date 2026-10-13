# models.py

import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Import the Tenant model from your tenants app.
from tenantsapp.models import Tenant

class User(AbstractUser):
    """Custom User model with phone number, tenant association, and user role"""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Staff'

    phone_no = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,   
        default=Role.ADMIN,
        help_text="Role of the user within the shop/tenant"
    )

    # Tenant foreign key – nullable so superusers can have no tenant.
    # on_delete=SET_NULL: if tenant is deleted, user keeps existing data but tenant becomes null.
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Which shop/tenant this user belongs to"
    )

    
    def __str__(self):
        return f"{self.username} - {self.role}"


class PasswordResetOTP(models.Model):
    CHANNEL_CHOICES = (
        ('email', 'Email'),
        ('phone', 'Phone'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes'
    )
    # Stores a bcrypt hash of the OTP – must be long enough for the digest
    otp_code = models.CharField(max_length=128)
    target = models.CharField(max_length=255)   # email or phone that was used
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    OTP_TTL_MINUTES = 10

    def is_valid(self):
        """Returns True when the OTP is unused and still within the TTL window."""
        if self.is_used:
            return False
        return timezone.now() <= self.created_at + timedelta(minutes=self.OTP_TTL_MINUTES)

    def __str__(self):
        return f"OTP for {self.user.username} via {self.channel}"


class PasswordResetToken(models.Model):
    """
    Short-lived token issued *after* OTP verification (step 7).
    Consumed when the user submits a new password (step 9).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reset_tokens'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    TOKEN_TTL_MINUTES = 15

    def is_valid(self):
        if self.is_used:
            return False
        return timezone.now() <= self.created_at + timedelta(minutes=self.TOKEN_TTL_MINUTES)

    def __str__(self):
        return f"ResetToken for {self.user.username}"


    