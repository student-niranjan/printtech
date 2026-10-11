from rest_framework import serializers
# pyrefly: ignore [missing-import]
from .models import Customer
from tenantsapp.models import Tenant
from tenantsapp.serializers import TenantSerializer


class CustomerSerializer(serializers.ModelSerializer):
    tenant_name = serializers.ReadOnlyField(source='tenant.shop_name')

    class Meta:
        model = Customer
        fields = [
            'id',
            'uuid',
            'tenant',
            'tenant_name',
            'name',
            'customer_type',
            'company_name',
            'address',
            'contact_no',
            'pan_no',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'tenant']
    