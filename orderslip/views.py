# orderslip/views.py
from django.db import transaction
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404

from .models import Order, SlipItem, WorkStage, Invoice

from .serailizers import (
    OrderSerializer,
    SlipItemSerializer,
    InvoiceSerializer,
    SlipItemstaffSerializer,
    WorkStageSerializer,
)
from customers.models import Customer


# ============================================
# Order Slip List
# ============================================
class OrderSlipList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        # Show orders belonging only to the logged-in user's tenant
        orders = (
            Order.objects
            .filter(tenant=request.user.tenant)
            .select_related(
                "customer",
                "tenant",
                "prepared_by",
            )
            .order_by("-created_at")
        )

        serializer = OrderSerializer(orders, many=True)

        return Response({
            "orders": serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        data = request.data.copy()

        # 1. Get tenant and staff from the authenticated user
        tenant = request.user.tenant
        prepared_by = request.user

        # 2. Get customer ID from request data
        customer_id = data.get("customer")

        # 3. If customer ID is missing, select the newest
        # customer belonging to the current tenant
        if not customer_id:
            customer = (
                Customer.objects
                .filter(tenant=tenant)
                .order_by("-created_at")
                .first()
            )

            if not customer:
                return Response(
                    {
                        "customer": [
                            "No customer available for your tenant. "
                            "Please add a customer first."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # 4. Verify the submitted customer belongs to this tenant
            customer = Customer.objects.filter(
                pk=customer_id,
                tenant=tenant,
            ).first()

            if not customer:
                return Response(
                    {
                        "customer": [
                            "Invalid customer or customer does not "
                            "belong to your tenant."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 5. Ignore tenant and prepared_by values supplied by the client
        data["tenant"] = tenant.pk
        data["prepared_by"] = prepared_by.pk
        data["customer"] = customer.pk

        # 6. Validate request data
        serializer = OrderSerializer(data=data)

        if serializer.is_valid():
            # Assign trusted relationships explicitly
            order = serializer.save(
                tenant=tenant,
                prepared_by=prepared_by,
                customer=customer,
            )

            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================
# Order Slip Detail
# ============================================
class OrderSlipDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Order.objects.select_related(
                "customer",
                "tenant",
                "prepared_by",
            ).get(pk=pk)
        except Order.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        order_slip = self.get_object(pk)
        serializer = OrderSerializer(order_slip)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        order_slip = self.get_object(pk)
        serializer = OrderSerializer(
            order_slip,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk, format=None):
        order_slip = self.get_object(pk)
        serializer = OrderSerializer(
            order_slip,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk, format=None):
        order_slip = self.get_object(pk)
        order_slip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================
# Work Stage List
# ============================================
class WorkStageList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        work_stages = WorkStage.objects.select_related(
            "slip_item",
            "slip_item__order",
        ).all()

        serializer = WorkStageSerializer(
            work_stages,
            many=True,
        )
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = WorkStageSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================
# Work Stage Detail
# ============================================
class WorkStageDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return WorkStage.objects.get(pk=pk)
        except WorkStage.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        work_stage = self.get_object(pk)
        serializer = WorkStageSerializer(work_stage)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        work_stage = self.get_object(pk)
        serializer = WorkStageSerializer(
            work_stage,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk, format=None):
        work_stage = self.get_object(pk)
        serializer = WorkStageSerializer(
            work_stage,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk, format=None):
        work_stage = self.get_object(pk)
        work_stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================
# Invoice List
# ============================================
class InvoiceList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        """GET /orderslipapi/invoices/ — list invoices for user's tenant."""
        invoices = (
            Invoice.objects
            .select_related("order", "tenant")
            .filter(tenant=request.user.tenant)
            .order_by("-created_at")
        )
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        print("\n========== INVOICE DEBUG START ==========")
        print("REQUEST DATA:", request.data)

        order_id = request.data.get("order")
        print("RECEIVED ORDER ID:", order_id)

        if not order_id:
            print("ERROR: ORDER ID IS MISSING")
            return Response(
                {"order": ["Order is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(pk=order_id)
            print("FOUND ORDER ID:", order.id)
            print("ORDER TENANT ID:", order.tenant_id)

        except (Order.DoesNotExist, ValueError, TypeError):
            print("ERROR: ORDER NOT FOUND")
            return Response(
                {"order": ["Order not found."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InvoiceSerializer(data=request.data)

        if serializer.is_valid():
            print(
                "SERIALIZER VALIDATED DATA:",
                serializer.validated_data,
            )

            try:
                invoice = serializer.save(tenant=order.tenant, order=order)

                print("INVOICE CREATED SUCCESSFULLY")
                print("INVOICE ID:", invoice.id)
                print("SAVED ORDER ID:", invoice.order_id)
                print("========== INVOICE DEBUG END ==========\n")

                return Response(
                    InvoiceSerializer(invoice).data,
                    status=status.HTTP_201_CREATED,
                )

            except Exception as error:
                print("INVOICE SAVE FAILED:", repr(error))
                raise

        print("SERIALIZER ERRORS:", serializer.errors)
        print("========== INVOICE DEBUG END ==========\n")

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================
# Invoice Detail
# ============================================
class InvoiceDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        invoice = self.get_object(pk)
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        invoice = self.get_object(pk)
        serializer = InvoiceSerializer(
            invoice,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk, format=None):
        invoice = self.get_object(pk)
        serializer = InvoiceSerializer(
            invoice,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk, format=None):
        invoice = self.get_object(pk)
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================
# Helper
# ============================================
def get_current_order():
    """Return the most recently created order."""
    return Order.objects.order_by("-created_at").first()


# ============================================
# Slip Item List
# ============================================
class SlipItemList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        slip_items = SlipItem.objects.select_related(
            "order",
        ).all()

        order_id = request.query_params.get("order")

        if order_id:
            slip_items = slip_items.filter(order_id=order_id)

        serializer = SlipItemSerializer(
            slip_items,
            many=True,
        )

        current_order = get_current_order()

        return Response({
            "current_order": (
                str(current_order.id)
                if current_order else None
            ),
            "items": serializer.data,
        })

    def post(self, request, format=None):
        data = request.data.copy()

        # Default to the latest order only if no order was selected.
        if not data.get("order"):
            current_order = get_current_order()

            if current_order is None:
                return Response(
                    {"order": ["No orders exist yet."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data["order"] = str(current_order.id)

        serializer = SlipItemSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================
# Slip Item Detail
# ============================================
class SlipItemDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return SlipItem.objects.select_related(
                "order",
            ).get(pk=pk)
        except SlipItem.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        slip_item = self.get_object(pk)
        serializer = SlipItemSerializer(slip_item)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        slip_item = self.get_object(pk)
        serializer = SlipItemSerializer(
            slip_item,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk, format=None):
        slip_item = self.get_object(pk)
        serializer = SlipItemSerializer(
            slip_item,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk, format=None):
        slip_item = self.get_object(pk)
        slip_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================
# Slip Staff Assign Work
# ============================================
class Slipstaffassignwork(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        slip_items = (
            SlipItem.objects
            .select_related(
                "order",
                "Designing_person",
                "printing_person",
                "binding_person",
            )
            .filter(order__tenant=request.user.tenant)
            .order_by("-id")
        )

        serializer = SlipItemstaffSerializer(slip_items, many=True)
        return Response(serializer.data)

    # orderslip/views.py




class MyAssignedWork(APIView):
    """
    Staff-only view for managing their assigned slip items.
    
    - GET  /slipassignwork/         → list items assigned to the logged-in user
    - PATCH /slipassignwork/<pk>/   → update the user's task status on one item
    """
    permission_classes = [IsAuthenticated]

    # ─────────────────────────────────────────────
    # LIST: My assigned work
    # ─────────────────────────────────────────────
    def get(self, request, format=None):
        user_id = request.user.id

        slip_items = (
            SlipItem.objects
            .select_related(
                "order",
                "order__customer",
                "Designing_person",
                "printing_person",
                "binding_person",
            )
            .filter(order__tenant=request.user.tenant)
            .filter(
                Q(Designing_person_id=user_id)
                | Q(printing_person_id=user_id)
                | Q(binding_person_id=user_id)
            )
            .order_by("-id")
        )

        serializer = SlipItemstaffSerializer(slip_items, many=True)
        return Response(serializer.data)

    # ─────────────────────────────────────────────
    # PATCH: Update my task status
    # ─────────────────────────────────────────────
    @transaction.atomic
    def patch(self, request, pk, format=None):
        user_id = request.user.id

        # Find the item within the current tenant (with row lock)
        item = get_object_or_404(
            SlipItem.objects.select_for_update().filter(
                order__tenant=request.user.tenant
            ),
            pk=pk,
        )

        # Only allow the assigned staff to update their own task status
        allowed_fields = {
            "designing_status": (
                "Designing_person_id",
                {"waiting", "in_progress", "completed"},
            ),
            "printing_status": (
                "printing_person_id",
                {"waiting", "in_progress", "completed"},
            ),
            "binding_status": (
                "binding_person_id",
                {"waiting", "in_progress", "completed"},
            ),
        }

        # Must submit exactly one status field
        if len(request.data) != 1:
            return Response(
                {"error": "Submit exactly one status field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        field = next(iter(request.data))

        if field not in allowed_fields:
            return Response(
                {"error": "Only task statuses can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assigned_field, valid_values = allowed_fields[field]

        # Ensure the logged-in user is the assigned person for that field
        if getattr(item, assigned_field) != user_id:
            return Response(
                {"error": "You are not assigned to this task."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data[field]

        if new_status not in valid_values:
            return Response(
                {"error": "Invalid status value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enforce task dependencies
        if field == "printing_status":
            if item.designing_status != "completed":
                return Response(
                    {"error": "Designing must be completed first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if field == "binding_status":
            if item.printing_status != "completed":
                return Response(
                    {"error": "Printing must be completed first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        setattr(item, field, new_status)
        item.save(update_fields=[field])

        return Response(
            SlipItemstaffSerializer(item).data,
            status=status.HTTP_200_OK,
        )