
# customers/models.py

import uuid
from django.db import models
from django.db.models import Q
from tenantsapp.models import Tenant


class Customer(models.Model):

    customer_choice = [
        ("individual", "Individual"),
        ("business", "Business"),
    ]

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique external identifier"
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="customers",
        help_text="Which shop/tenant this customer belongs to"
    )

    name = models.CharField(max_length=200)

    customer_type = models.CharField(
        max_length=100,
        choices=customer_choice,
        default="individual"
    )

    company_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)

    pan_no = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="PAN No."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "pan_no"],
                condition=~Q(pan_no=""),
                name="unique_pan_per_tenant",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.tenant.shop_name}"
