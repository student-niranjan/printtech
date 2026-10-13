import uuid
from django.db import models
from django.db.models import Sum
from django.conf import settings


class Order(models.Model):
    work_type_choices = [
        ("pending", "pending"),
        ("completed", "completed"),
        ("printed", "printed"),
    ]
    PROOF_METHOD_CHOICES = [
        ("show", "देखाउने"),
        ("sample", "नमूना अनुसार"),
        ("computer", "कम्प्युटरमा भएको"),
    ]
    priority_choice = [
        ("urgent", "Urgent"),
        ("high", "High"),
        ("normal", "Normal"),
        ("low", "Low"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    tenant = models.ForeignKey(
        "tenantsapp.Tenant",
        on_delete=models.CASCADE,
        related_name="orders",
    )

    slip_no = models.PositiveIntegerField()

    project_name = models.CharField(max_length=255)
    priority = models.CharField(max_length=50, choices=priority_choice, blank=True)
    work_stage = models.CharField(
        max_length=100,
        blank=True,
        default="pending",
        choices=work_type_choices,
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_prepared",
    )
    print_details_full = models.TextField(blank=True, help_text="Full print details for the order slip.")
    slip_date = models.DateField()

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    delivery_date = models.DateField(null=True, blank=True)

    proof_method = models.CharField(
        max_length=20,
        choices=PROOF_METHOD_CHOICES,
        blank=True,
    )

    description = models.TextField(blank=True)

    taken_by_signature = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_taken_by_signature",
        null=True,
        blank=True,
    )

    given_by_signature = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders_given_by_signature",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "slip_no")
        ordering = ["-slip_date"]

    def __str__(self):
        return f"Slip #{self.slip_no} — {self.customer}"

    # ============================================
    # AUTOMATIC SLIP NUMBER
    # ============================================
    def save(self, *args, **kwargs):
        """Auto-generate slip_no per tenant on first save."""
        if self._state.adding and not self.slip_no:
            last_order = (
                Order.objects
                .filter(tenant=self.tenant)
                .order_by("-slip_no")
                .first()
            )
            self.slip_no = (last_order.slip_no + 1) if last_order else 1

        super().save(*args, **kwargs)

    # ============================================
    # RECALCULATE TOTALS
    # ============================================
    # orderslip/models.py
    def recalculate_totals(self, save=True):
        """Recalculate total_amount, paid_amount, and balance."""
        total = self.slip_items.aggregate(
            total=Sum("subtotal")
        )["total"] or 0

        paid = self.invoices.filter(
            status__in=["paid", "partial"]
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        self.total_amount = total
        self.paid_amount = paid
        self.balance = total - paid

        if save:
            super().save(
                update_fields=[
                    "total_amount",
                    "paid_amount",
                    "balance",
                    "updated_at",
                ]
            )
        return self

class SlipItem(models.Model):

    paper_type_choices = [
        ("art", "Art"),
        ("card", "Card"),
        ("newsprint", "Newsprint"),
        ("coated", "Coated"),
        ("uncoated", "Uncoated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="slip_items")

    item_description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=100, blank=True)
    maso = models.CharField(max_length=100, blank=True)
    paper_type = models.CharField(max_length=100, choices=paper_type_choices, blank=True)
    band_type = models.CharField(max_length=100, blank=True)
    work_type = models.CharField(max_length=100, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    Designing_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="designed_slip_items"
    )
    printing_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="printed_slip_items"
    )
    binding_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bound_slip_items"
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_description} × {self.quantity}"


class WorkStage(models.Model):
    STAGE_CHOICES = [
        ("design", "Design"),
        ("printing", "Printing"),
        ("binding", "Binding"),
    ]
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("completed", "completed"),
        ("printed", "printed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slip_item = models.ForeignKey(SlipItem, on_delete=models.CASCADE, related_name="work_stages")

    stage_type = models.CharField(max_length=20, choices=STAGE_CHOICES, default="pending")
    stage_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_stages"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        ordering = ["stage_date"]

    def __str__(self):
        return f"{self.slip_item} — {self.get_stage_type_display()} ({self.status})"


class Invoice(models.Model):
    TYPE_CHOICES = [
        ("advance", "Advance"),
        ("final", "Final"),

    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("partial", "Partial"),
        ("paid", "Paid"),
    ]

    PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("bank", "Bank Transfer"),
    ("esewa", "eSewa"),
    ("khalti", "Khalti"),
    ("card", "Card"),
]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenantsapp.Tenant", on_delete=models.CASCADE, related_name="invoices")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="invoices")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    invoice_type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default="cash", blank=True)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_date"]

    def __str__(self):
        return f"{self.order} — {self.invoice_type} — {self.amount}"



class PaperType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name 