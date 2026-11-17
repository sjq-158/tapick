from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.home.models import Inventory

from .rules import handle_stock_change, stock_status


@receiver(pre_save, sender=Inventory)
def remember_previous_status(sender, instance, raw=False, **kwargs):
    instance._previous_status = None
    if raw or not instance.pk:
        return
    old = Inventory.objects.filter(pk=instance.pk).values("quantity_on_hand", "reorder_threshold").first()
    if old:
        instance._previous_status = stock_status(old["quantity_on_hand"], old["reorder_threshold"])


@receiver(post_save, sender=Inventory)
def run_stock_rules(sender, instance, raw=False, **kwargs):
    if not raw:
        handle_stock_change(instance, getattr(instance, "_previous_status", None))