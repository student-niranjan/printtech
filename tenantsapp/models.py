import uuid
from django.db import models

class Tenant(models.Model):
    uid = models.CharField(
        max_length=36,
        unique=True,
        editable=False,   # removes it from admin forms automatically
        blank=True,
    )
    logo=models.ImageField(upload_to="tenant_logos/", null=True, blank=True)
    shop_name = models.CharField(max_length=255)
    address = models.TextField()
    contact_phone = models.CharField(max_length=20)
    pan_no = models.CharField(max_length=20)

    def save(self, *args, **kwargs):
        if not self.uid:
            self.uid = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return self.shop_name