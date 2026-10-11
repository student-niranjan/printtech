from django.contrib import admin

# Register your models here.
from .models import Tenant

class TenantAdmin(admin.ModelAdmin):
    readonly_fields = ("uid",)
    list_display = ("shop_name", "uid", "contact_phone", "pan_no")

admin.site.register(Tenant, TenantAdmin)