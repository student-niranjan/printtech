from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("prints.urls")),
    path("tenantapi/", include("tenantsapp.urls")),
    path("customerapi/", include("customers.urls")),
    path("orderslipapi/", include("orderslip.urls")),

]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
