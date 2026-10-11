# prints/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, PasswordResetOTP, PasswordResetToken


class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""

    list_display  = ('username', 'email', 'phone_no', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_no')
    list_filter   = ('is_staff', 'is_active', 'is_superuser')

    # Add phone_no to the user edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_no',)}),
    )

    # Add phone_no to the user creation form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone_no', 'email')}),
    )


class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display  = ('user', 'target', 'channel', 'created_at', 'is_used')
    search_fields = ('user__username', 'user__email', 'target')
    list_filter   = ('channel', 'is_used', 'created_at')


class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ('user', 'created_at', 'is_used')
    search_fields = ('user__username', 'user__email', 'token')
    list_filter   = ('is_used', 'created_at')


# Register the models
admin.site.register(User, CustomUserAdmin)
admin.site.register(PasswordResetOTP, PasswordResetOTPAdmin)
admin.site.register(PasswordResetToken, PasswordResetTokenAdmin)
