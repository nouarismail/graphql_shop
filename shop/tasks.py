import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


@shared_task(name="shop.tasks.cancel_expired_pending_orders")
def cancel_expired_pending_orders():
    """Cancel orders that are still pending after the configured payment window."""
    now = timezone.now()
    cutoff = now - timedelta(seconds=settings.ORDER_PENDING_TIMEOUT_SECONDS)

    cancelled_count = Order.objects.filter(
        status="PENDING",
        created_at__lte=cutoff,
    ).update(
        status="CANCELLED",
        updated_at=now,
    )

    if cancelled_count:
        logger.info("Automatically cancelled %s expired pending order(s)", cancelled_count)

    return cancelled_count
