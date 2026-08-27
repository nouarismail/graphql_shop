from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from shop.models import Order
from shop.tasks import cancel_expired_pending_orders


@override_settings(ORDER_PENDING_TIMEOUT_SECONDS=1800)
class CancelExpiredPendingOrdersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="task-test-user")

    def test_cancels_only_expired_pending_orders(self):
        expired = Order.objects.create(user=self.user, status="PENDING")
        fresh = Order.objects.create(user=self.user, status="PENDING")
        confirmed = Order.objects.create(user=self.user, status="CONFIRMED")
        old_created_at = timezone.now() - timedelta(minutes=31)
        Order.objects.filter(pk__in=[expired.pk, confirmed.pk]).update(
            created_at=old_created_at
        )

        cancelled_count = cancel_expired_pending_orders.run()

        expired.refresh_from_db()
        fresh.refresh_from_db()
        confirmed.refresh_from_db()
        self.assertEqual(cancelled_count, 1)
        self.assertEqual(expired.status, "CANCELLED")
        self.assertEqual(fresh.status, "PENDING")
        self.assertEqual(confirmed.status, "CONFIRMED")
