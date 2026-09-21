from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from shop.graphql.permissions import can_cancel_order, can_modify_order, can_view_order


class OrderPermissionTests(SimpleTestCase):
    def setUp(self):
        self.info = SimpleNamespace()
        self.user = Mock(id=1, is_superuser=False)
        self.user.groups.filter.return_value.exists.return_value = False
        self.user.has_perm.return_value = True
        self.order = SimpleNamespace(user_id=1, status="PENDING")
        current_user = patch("shop.graphql.permissions.get_current_user", return_value=self.user)
        current_user.start()
        self.addCleanup(current_user.stop)

    def test_anonymous_user_cannot_access_orders(self):
        with patch("shop.graphql.permissions.get_current_user", return_value=None):
            for authorize in (can_view_order, can_modify_order, can_cancel_order):
                with self.subTest(operation=authorize.__name__):
                    with self.assertRaisesRegex(Exception, "^Authentication required$"):
                        authorize(self.info, self.order)

    def test_customer_can_view_own_order_with_permission(self):
        self.assertIs(can_view_order(self.info, self.order), self.user)

    def test_customer_cannot_view_another_customers_order(self):
        self.order.user_id = 2
        with self.assertRaisesRegex(Exception, "^You cannot access this order$"):
            can_view_order(self.info, self.order)

    def test_customer_needs_view_permission_even_for_own_order(self):
        self.user.has_perm.return_value = False
        with self.assertRaisesRegex(Exception, "^You cannot access this order$"):
            can_view_order(self.info, self.order)

    def test_customer_can_modify_own_pending_order(self):
        self.assertIs(can_modify_order(self.info, self.order), self.user)

    def test_customer_cannot_modify_another_customers_order(self):
        self.order.user_id = 2
        with self.assertRaisesRegex(Exception, "^You can only modify your own orders$"):
            can_modify_order(self.info, self.order)

    def test_customer_cannot_modify_non_pending_orders(self):
        for status in ("CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"):
            with self.subTest(status=status):
                self.order.status = status
                with self.assertRaisesRegex(Exception, "only be modified while order is PENDING"):
                    can_modify_order(self.info, self.order)

    def test_customer_can_cancel_pending_and_confirmed_orders(self):
        for status in ("PENDING", "CONFIRMED"):
            with self.subTest(status=status):
                self.order.status = status
                self.assertIs(can_cancel_order(self.info, self.order), self.user)

    def test_customer_cannot_cancel_another_customers_order(self):
        self.order.user_id = 2
        with self.assertRaisesRegex(Exception, "^You can only cancel your own orders$"):
            can_cancel_order(self.info, self.order)

    def test_customer_cannot_cancel_orders_after_confirmation(self):
        for status in ("PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"):
            with self.subTest(status=status):
                self.order.status = status
                with self.assertRaisesRegex(Exception, "^This order can no longer be cancelled$"):
                    can_cancel_order(self.info, self.order)

    def test_staff_with_permission_can_access_other_customers_orders(self):
        self.user.groups.filter.return_value.exists.return_value = True
        self.order.user_id = 2
        for authorize in (can_view_order, can_modify_order, can_cancel_order):
            with self.subTest(operation=authorize.__name__):
                self.assertIs(authorize(self.info, self.order), self.user)

    def test_staff_without_permission_cannot_view_other_customers_orders(self):
        self.user.groups.filter.return_value.exists.return_value = True
        self.user.has_perm.return_value = False
        self.order.user_id = 2
        with self.assertRaisesRegex(Exception, "^You cannot access this order$"):
            can_view_order(self.info, self.order)

    def test_superuser_can_access_other_customers_orders(self):
        self.user.is_superuser = True
        self.user.has_perm.return_value = False
        self.order.user_id = 2
        for authorize in (can_view_order, can_modify_order, can_cancel_order):
            with self.subTest(operation=authorize.__name__):
                self.assertIs(authorize(self.info, self.order), self.user)
