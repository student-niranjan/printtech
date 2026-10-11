# orderslip/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

from orderslip.models import SlipItem, Invoice


def _recalculate(order):
    if order is None:
        return

    try:
        order.recalculate_totals()
    except ObjectDoesNotExist:
        # Order was deleted (cascade) — skip
        pass
    except Exception as e:
        # ✅ Print the actual error so we can debug it
        print(f"❌ recalculate_totals failed: {type(e).__name__}: {e}")
        raise   # 👈 re-raise so Django shows the 500 error


@receiver([post_save, post_delete], sender=SlipItem)
def update_order_on_slip_item_change(sender, instance, **kwargs):
    _recalculate(getattr(instance, "order", None))


@receiver([post_save, post_delete], sender=Invoice)
def update_order_on_invoice_change(sender, instance, **kwargs):
    _recalculate(getattr(instance, "order", None))