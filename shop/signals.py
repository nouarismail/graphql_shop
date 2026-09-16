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


# Deletion signals also cover QuerySet.delete() and cascading child deletions.
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from .audit import FIELDS, record_event, snapshot


@receiver(post_delete)
def audit_deletion(sender, instance, using, **kwargs):
    if sender._meta.label_lower in FIELDS:
        record_event("delete", instance=instance, using=using,
                     changes={key: {"before": value, "after": None}
                              for key, value in snapshot(instance).items()})


@receiver(user_login_failed)
def audit_failed_login(sender, **kwargs):
    # Never store submitted usernames, credentials, or exception text.
    record_event("auth.login_failed")


@receiver(user_logged_in)
def audit_session_login(sender, user, **kwargs):
    record_event("auth.login", actor=user)


@receiver(user_logged_out)
def audit_session_logout(sender, user, **kwargs):
    record_event("auth.logout", actor=user)
