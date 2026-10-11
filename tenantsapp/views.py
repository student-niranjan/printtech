
from django.db.models import Q
from django.http import Http404, request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model

User = get_user_model()

# pyrefly: ignore [missing-import]
from .models import Tenant

# pyrefly: ignore [missing-import]
from .serializers import TenantSerializer


class TenantListCreateAPIView(APIView):
    """
    GET: Only authenticated users can list tenants.
    POST: Anyone can create a tenant.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAdminUser()]

        return [permissions.AllowAny()]

    def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only superusers can access all tenants."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = Tenant.objects.all()
        serializer = TenantSerializer(queryset, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = TenantSerializer(data=request.data)

        if serializer.is_valid():
            contact_phone = serializer.validated_data.get(
                "contact_phone"
            )

            try:
                user = User.objects.get(phone_no=contact_phone)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found with this phone number."},
                    status=status.HTTP_404_NOT_FOUND
                )

            tenant = serializer.save()

            user.tenant = tenant
            user.save(update_fields=["tenant"])

            return Response(
                TenantSerializer(tenant).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class TenantDetailAPIView(APIView):
    """
    APIView to retrieve, update, or delete a specific tenant instance.
    Supports lookup by integer primary key (pk/id) or string uid.
    """

    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        try:
            if isinstance(pk, int) or (
                isinstance(pk, str) and pk.isdigit()
            ):
                return Tenant.objects.get(pk=int(pk))

            return Tenant.objects.get(uid=str(pk))

        except Tenant.DoesNotExist:
            raise Http404("Tenant not found.")

    def get(self, request, pk):
        tenant = self.get_object(pk)
        serializer = TenantSerializer(tenant)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def put(self, request, pk):
        tenant = self.get_object(pk)
        serializer = TenantSerializer(tenant, data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, pk):
        tenant = self.get_object(pk)
        serializer = TenantSerializer(
            tenant,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        tenant = self.get_object(pk)
        tenant.delete()

        return Response(
            {"message": "Tenant deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


# Aliases for flexible imports
TenantListCreateView = TenantListCreateAPIView
TenantDetailView = TenantDetailAPIView
