from  rest_framework import serializers
from .models import (
    Order,
    SlipItem,
    WorkStage,
    Invoice,
)

from customers.models import Customer
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name"]


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
        class Meta:
            model = SlipItem
            fields = ["id", "order", "item_description", "quantity", "rate", "subtotal", "paper_type", "size", "maso", "Designing_person", "printing_person", "binding_person", "work_type" ]
            read_only_fields = ["id", "subtotal"]


class WorkStageSerializer(serializers.ModelSerializer):
        class Meta:
            model = WorkStage
            fields = ["id", "slip_item", "stage_type", "status"]
            read_only_fields = ["id",]


class InvoiceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Invoice
            fields = ["id", "order", "amount", "tenant"]
            read_only_fields = ["id", "tenant"]



