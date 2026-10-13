
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
    WorkStageSerializer,
)
from customers.models import Customer 


class OrderSlipList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        orders = Order.objects.select_related(
            "customer",
            "tenant",
            "prepared_by",
        ).order_by("-created_at")

        serializer = OrderSerializer(orders, many=True)

        return Response({
            "orders": serializer.data,
        })

    def post(self, request, format=None):
        data = request.data.copy()

        # ============================================
        # 1. Determine tenant + prepared_by
        # ============================================
        last_order = Order.objects.order_by("-created_at").first()

        tenant_id = data.get("tenant") or (
            last_order.tenant_id if last_order else None
        )
        prepared_by_id = data.get("prepared_by") or (
            last_order.prepared_by_id if last_order else request.user.id
        )

        if not tenant_id:
            return Response(
                {"tenant": ["Cannot determine tenant."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ============================================
        # 2. Auto-pick the NEWEST customer in tenant
        # ============================================
        customer_id = data.get("customer")   # Priority 1: frontend override

        if not customer_id:
            # Priority 2: newest customer in this tenant
            newest = (
                Customer.objects
                .filter(tenant_id=tenant_id)
                .order_by("-created_at")     # newest first
                .first()
            )
            if newest:
                customer_id = newest.id

        if not customer_id:
            return Response(
                {"customer": ["No customer available. Please add a customer first."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ============================================
        # 3. Apply auto values
        # ============================================
        data["customer"] = customer_id
        data["tenant"] = tenant_id
        data["prepared_by"] = prepared_by_id

        # ============================================
        # 4. Save
        # ============================================
        serializer = OrderSerializer(data=data)

        if serializer.is_valid():
            order = serializer.save()
            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )
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


# orderslip/views.py

class InvoiceList(APIView):
    permission_classes = [IsAuthenticated]

    
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


def get_current_order():
    """Return the most recently created order."""
    return Order.objects.order_by("-created_at").first()


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
