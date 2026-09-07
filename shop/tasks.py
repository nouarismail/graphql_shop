import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


@shared_task(
    name="shop.tasks.send_order_confirmation_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_order_confirmation_email(order_id):
    """Simulate an order confirmation using Django's console email backend."""
    order = (
        Order.objects.select_related("user")
        .prefetch_related("items__product")
        .get(pk=order_id)
    )
    lines = [
        f"Thank you for your order, {order.user.get_full_name() or order.user.username}!",
        "",
        f"Order number: {order.id}",
        f"Status: {order.status}",
        "",
        "Items:",
    ]
    total = 0
    for item in order.items.all():
        line_total = item.product.price * item.quantity
        total += line_total
        lines.append(f"- {item.product.name} x {item.quantity}: {line_total:.2f}")
    lines.extend(("", f"Total: {total:.2f}"))

    sent_count = send_mail(
        subject=f"Order #{order.id} confirmation",
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=False,
    )
    logger.info("Sent confirmation for order %s to %s", order.id, order.user.email)
    return sent_count


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
