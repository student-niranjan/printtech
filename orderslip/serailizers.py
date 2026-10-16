from  rest_framework import serializers
from .models import (
    Order,
    SlipItem,
    WorkStage,
    Invoice,
)
from django.contrib.auth import get_user_model
from orderslip.models import Order

User = get_user_model()
# orderslip/serializers.py

class StaffMiniSerializer(serializers.ModelSerializer):
    """Minimal staff info for nested display."""
    
    class Meta:
        model = User
        fields = ["id", "username", "role"]
        read_only_fields = fields

from customers.models import Customer
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name","contact_no","address","pan_no"]


class OrderSerializer(serializers.ModelSerializer):
    customer_details = CustomerSerializer(
        source="customer",
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "tenant",
            "slip_no",
            "customer",
            "customer_details",
            "prepared_by",
            "project_name",
            "print_details_full",
            "description",
            "priority",
            "slip_date",
            "delivery_date",
            "proof_method",
            "work_stage",
            "total_amount",
            "balance",
            "paid_amount",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slip_no",
            "total_amount",
            "balance",
            "paid_amount",
            "created_at",
            "updated_at",
        ]

        

class SlipItemSerializer(serializers.ModelSerializer):
        designing_person_details = StaffMiniSerializer(
                source="Designing_person",
                read_only=True
            )
        printing_person_details = StaffMiniSerializer(
                source="printing_person",  
                read_only=True      
            )
        binding_person_details = StaffMiniSerializer(
                source="binding_person",
                read_only=True
            )

        class Meta:
            model = SlipItem
            fields = ["id", "order", "item_description", "quantity", "rate", "subtotal", "paper_type", "size", "maso", "Designing_person", "printing_person", "binding_person", "work_type", "designing_person_details", "printing_person_details", "binding_person_details","designing_status","printing_status","binding_status"]
            read_only_fields = ["id", "subtotal"]


class WorkStageSerializer(serializers.ModelSerializer):
        class Meta:
            model = WorkStage
            fields = ["id", "slip_item", "stage_type", "status"]
            read_only_fields = ["id",]


class InvoiceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Invoice
            fields = ["id", "order", "amount","tenant","status","payment_method", "created_at"]
            read_only_fields = ["id","tenant"]



# orderslip/serializers.py
class SlipItemstaffSerializer(serializers.ModelSerializer):
    order_details=OrderSerializer(source="order" ,read_only=True)
    designing_person_details = StaffMiniSerializer(source="Designing_person", read_only=True)
    printing_person_details = StaffMiniSerializer(source="printing_person", read_only=True)
    binding_person_details = StaffMiniSerializer(source="binding_person", read_only=True)

    class Meta:
        model = SlipItem
        fields = [
        "id",
        "order",
        "order_details",
        "item_description",         
        "quantity",
        "rate",
        "subtotal",
        "paper_type",
        "size",
        "maso",
        "band_type",
        "work_type",
        "Designing_person",
        "designing_person_details",
        "designing_status",
        "printing_person",
        "printing_person_details",
        "printing_status",
        "binding_person",
        "binding_person_details",
        "binding_status",
    ]

    extra_kwargs = {
        "designing_status": {"required": False},
        "printing_status": {"required": False},
        "binding_status": {"required": False},
    }