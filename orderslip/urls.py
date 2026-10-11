
from django.urls import path

from .views import (
    OrderSlipList,
    OrderSlipDetail,
    WorkStageList,
    WorkStageDetail,
    InvoiceList,
    InvoiceDetail,
    SlipItemList,
    SlipItemDetail,
)

urlpatterns = [
    path(
        "orderslips/",
        OrderSlipList.as_view(),
        name="order-slip-list",
    ),
    path(
        "orderslips/<uuid:pk>/",
        OrderSlipDetail.as_view(),
        name="order-slip-detail",
    ),

    path(
        "workstages/",
        WorkStageList.as_view(),
        name="work-stage-list",
    ),
    path(
        "workstages/<uuid:pk>/",
        WorkStageDetail.as_view(),
        name="work-stage-detail",
    ),

    path(
        "invoices/",
        InvoiceList.as_view(),
        name="invoice-list",
    ),
    path(
        "invoices/<uuid:pk>/",
        InvoiceDetail.as_view(),
        name="invoice-detail",
    ),

    path(
        "slipitems/",
        SlipItemList.as_view(),
        name="slip-item-list",
    ),
    path(
        "slipitems/<uuid:pk>/",
        SlipItemDetail.as_view(),
        name="slip-item-detail",
    ),
]
