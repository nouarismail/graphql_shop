from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Product
from .services.catalog_cache import invalidate_catalog_cache


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def invalidate_catalog_on_write(**kwargs):
    invalidate_catalog_cache()
