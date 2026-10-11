# orderslip/apps.py
from django.apps import AppConfig


class OrderslipConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orderslip"

    def ready(self):
        print("✅ OrderslipConfig.ready() called")   # 🔍 debug
        import orderslip.signals