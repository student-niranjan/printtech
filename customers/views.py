from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    # Use UUID instead of the default id/pk
    lookup_field = "uuid"

    def get_queryset(self):
        return Customer.objects.filter(
            tenant=self.request.user.tenant
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant
        )