# customers/models.py (or wherever you place your Customer model)

import uuid
from django.db import models
from tenantsapp.models import Tenant   # adjust import based on your app name

class Customer(models.Model):
    # Primary key – Django automatically adds an 'id' AutoField
    # But we also add a UUID field for external references
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
        related_name='customers',
        help_text="Which shop/tenant this customer belongs to"
    )

    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=100, choices=customer_choice, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    pan_no = models.CharField(max_length=20, blank=True, verbose_name="PAN No.")


    # Optional: track creation/update
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        # Optionally enforce unique customer per tenant (e.g., same pan_no)
        unique_together = ['tenant', 'pan_no']  # if needed

    def __str__(self):
        return f"{self.name} - {self.tenant.shop_name}" 
