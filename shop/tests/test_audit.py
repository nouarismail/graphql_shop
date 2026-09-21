from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.db import transaction
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from shop.admin import AuditEventAdmin
from shop.audit import AuditMiddleware, audit_context, set_audit_actor
from shop.models import AuditEvent, Category, Order, Product
from shop.services import auth_service
from shop.tasks import cancel_expired_pending_orders


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class AuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="auditor", password="test-secret")

    def test_create_update_partial_save_and_redaction(self):
        with audit_context(source="test"):
            set_audit_actor(self.user)
            category = Category.objects.create(name="Hardware", description="private text")
            product = Product.objects.create(name="Mouse", price=Decimal("10.00"), category=category)
            product.price = Decimal("15.00")
            product.name = "unsaved name"
            product.save(update_fields=["price"])
        event = AuditEvent.objects.first()
        self.assertEqual(event.actor_id, self.user.pk)
        self.assertEqual(event.action, "update")
        self.assertEqual(event.changes, {"price": {"before": "10.00", "after": "15.00"}})
        self.assertNotIn("private text", str(list(AuditEvent.objects.values())))
        self.assertEqual(AuditEvent.objects.count(), 3)

    def test_noop_save_does_not_emit_event(self):
        category = Category.objects.create(name="Hardware")
        category.save()
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_rollback_removes_both_change_and_event(self):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                Category.objects.create(name="Rollback")
                raise ValueError("abort")
        self.assertFalse(Category.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_audit_failure_rolls_back_write(self):
        with patch("shop.audit.record_event", side_effect=RuntimeError("unavailable")):
            with self.assertRaises(RuntimeError):
                Category.objects.create(name="Must not persist")
        self.assertFalse(Category.objects.exists())

    def test_cascade_deletions_audited(self):
        category = Category.objects.create(name="Hardware")
        Product.objects.create(name="Mouse", price=10, category=category)
        Category.objects.filter(pk=category.pk).delete()
        self.assertEqual(set(AuditEvent.objects.filter(action="delete").values_list("object_type", flat=True)),
                         {"shop.category", "shop.product"})

    def test_context_is_reset_on_exception(self):
        def fail(request):
            set_audit_actor(self.user)
            raise ValueError("abort")
        with self.assertRaises(ValueError):
            AuditMiddleware(fail)(RequestFactory().get("/"))
        Category.objects.create(name="No request")
        event = AuditEvent.objects.first()
        self.assertIsNone(event.actor_id)
        self.assertIsNone(event.request_id)
        self.assertEqual(event.source, "system")

    def test_response_request_id_matches_event(self):
        def view(request):
            Category.objects.create(name="HTTP")
            return HttpResponse()
        request = RequestFactory().get("/?password=do-not-store", HTTP_X_REQUEST_ID="untrusted")
        request.user = self.user
        response = AuditMiddleware(view)(request)
        event = AuditEvent.objects.first()
        self.assertEqual(response["X-Request-ID"], str(event.request_id))
        self.assertEqual(event.actor_id, self.user.pk)
        self.assertNotIn("do-not-store", str(event.__dict__))

    def test_login_success_and_failure_without_credentials(self):
        with patch("shop.services.auth_service._tokens_for", return_value="tokens"):
            auth_service.login("auditor", "test-secret")
        with self.assertRaises(Exception):
            auth_service.login("auditor", "incorrect-secret")
        self.assertEqual(set(AuditEvent.objects.values_list("action", flat=True)),
                         {"auth.login", "auth.login_failed"})
        self.assertNotIn("secret", str(list(AuditEvent.objects.values())))

    def test_expired_task_records_transition_once(self):
        order = Order.objects.create(user=self.user)
        # Deliberate fixture-only bulk update; bulk writes bypass auditing.
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=1))
        self.assertEqual(cancel_expired_pending_orders(), 1)
        self.assertEqual(cancel_expired_pending_orders(), 0)
        event = AuditEvent.objects.filter(action="update").get()
        self.assertEqual(event.source, "celery.cancel_expired_pending_orders")
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.changes["status"], {"before": "PENDING", "after": "CANCELLED"})

    def test_admin_view_requires_permission_and_cannot_modify(self):
        from django.contrib.admin import site
        model_admin = AuditEventAdmin(AuditEvent, site)
        self.user.is_staff = True
        self.user.save()
        request = SimpleNamespace(user=self.user)
        self.assertFalse(model_admin.has_view_permission(request))
        self.user.user_permissions.add(Permission.objects.get(codename="view_auditevent"))
        request.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(model_admin.has_view_permission(request))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_graphql_and_rest_authentication_set_actor(self):
        from shop.graphql.auth import get_current_user
        from shop.rest_api.authentication import JWTAuthentication
        with audit_context(source="http"):
            with patch("shop.graphql.auth.get_user_from_token", return_value=self.user):
                get_current_user(SimpleNamespace(context=SimpleNamespace(headers={"Authorization": "Bearer token"})))
            Category.objects.create(name="GraphQL")
        with audit_context(source="http"):
            with patch("shop.rest_api.authentication.get_user_from_token", return_value=self.user):
                JWTAuthentication().authenticate(RequestFactory().get("/", HTTP_AUTHORIZATION="Bearer token"))
            Category.objects.create(name="REST")
        self.assertEqual(list(AuditEvent.objects.values_list("actor_id", flat=True)), [self.user.pk, self.user.pk])

    def test_signup_refresh_logout_events(self):
        from django.contrib.auth.models import Group
        Group.objects.create(name="Customer")
        with patch("shop.services.auth_service._tokens_for", return_value="tokens"):
            auth_service.signup("new-user", "private@example.com", "private-password")
            with patch("shop.services.auth_service.get_user_from_refresh_token", return_value=self.user), \
                 patch("shop.services.auth_service.revoke_refresh_token", return_value=True), \
                 patch("shop.services.auth_service.invalidate_user_tokens"):
                auth_service.refresh("private-refresh-token")
                auth_service.logout("private-refresh-token")
        self.assertEqual(set(AuditEvent.objects.values_list("action", flat=True)),
                         {"auth.signup", "auth.refresh", "auth.logout"})
        self.assertNotIn("private", str(list(AuditEvent.objects.values())))

    def test_deletion_failure_preserves_object(self):
        category = Category.objects.create(name="Keep")
        with patch("shop.signals.record_event", side_effect=RuntimeError("unavailable")):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    category.delete()
        self.assertTrue(Category.objects.filter(name="Keep").exists())
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_actor_id_survives_user_deletion(self):
        actor_id = self.user.pk
        with audit_context():
            set_audit_actor(self.user)
            Category.objects.create(name="Keep attribution")
        self.user.delete()
        self.assertEqual(AuditEvent.objects.get().actor_id, actor_id)
