
from django.urls import path

# pyrefly: ignore [missing-import]
from .views import TenantListCreateAPIView, TenantDetailAPIView


urlpatterns = [
    # List all tenants / Create a tenant
    path(
        "tenants/",
        TenantListCreateAPIView.as_view(),
        name="tenant-list-create",
    ),

    # Get / Update / Partially update / Delete tenant
    path(
        "tenants/<str:pk>/",
        TenantDetailAPIView.as_view(),
        name="tenant-detail",
    ),
]
