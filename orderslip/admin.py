
from django.contrib import admin
# pyrefly: ignore [missing-import]
from .models import Order, SlipItem, WorkStage, Invoice


class SlipItemInline(admin.TabularInline):
    model = SlipItem
    extra = 1
    readonly_fields = ("subtotal",)


class WorkStageInline(admin.StackedInline):
    model = WorkStage
    extra = 1
    # allow adding more than 3 stages if you want, or limit: max_num = 3


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        "slip_no",
        "customer",
        "slip_date",
        "delivery_date",
        "total_amount",
        "paid_amount",
        "balance",
        "tenant",
    )
    list_filter = ("slip_date", "tenant")
    search_fields = ("slip_no", "customer__name", "print_details_full")
    inlines = [
        SlipItemInline,  # nested items
    ]
    

@admin.register(SlipItem)
class SlipItemAdmin(admin.ModelAdmin):
    readonly_fields = ("subtotal",)
    list_display = (
        "order",
        "item_description",
        "quantity",
        "rate",
        "subtotal",
        "size",
        "maso",
        "paper_type",
        "band_type",
        "work_type",
    )
    list_filter = ("order__slip_date", "order__tenant")
    search_fields = ("item_description", "order__slip_no", "order__customer__name")
    # optional: show work stages also inside SlipItem admin if you want more context
    inlines = [WorkStageInline]


@admin.register(WorkStage)
class WorkStageAdmin(admin.ModelAdmin):
    list_display = ("slip_item", "stage_type", "stage_date", "assigned_to", "status")
    list_filter = ("stage_type", "status", "stage_date", "assigned_to")
    search_fields = ("slip_item__item_description", "slip_item__order__slip_no")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "invoice_type", "paid_date", "status", "tenant")
    list_filter = ("status", "invoice_type", "paid_date", "tenant")
    search_fields = ("order__slip_no", "order__customer__name")
