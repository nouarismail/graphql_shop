from types import SimpleNamespace
from unittest.mock import patch

import redis
from django.test import RequestFactory, SimpleTestCase, override_settings

from shop.services.rate_limit import (
    OrderRateLimitExceeded,
    OrderRateLimitUnavailable,
    _client_ip,
    enforce_order_creation_rate_limit,
)


@override_settings(ORDER_RATE_LIMIT_TRUST_PROXY=False)
class ClientIpTests(SimpleTestCase):
    def test_ignores_forwarded_header_by_default(self):
        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="198.51.100.1")
        self.assertEqual(_client_ip(request), "192.0.2.1")

    @override_settings(ORDER_RATE_LIMIT_TRUST_PROXY=True)
    def test_trusted_proxy_uses_first_forwarded_address(self):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR=" 198.51.100.1, 192.0.2.1")
        self.assertEqual(_client_ip(request), "198.51.100.1")

    @override_settings(ORDER_RATE_LIMIT_TRUST_PROXY=True)
    def test_missing_forwarded_header_falls_back_to_remote_address(self):
        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.1")
        self.assertEqual(_client_ip(request), "192.0.2.1")

    def test_missing_remote_address_uses_unknown(self):
        self.assertEqual(_client_ip(SimpleNamespace(META={})), "unknown")


@override_settings(ORDER_RATE_LIMIT_WINDOW_SECONDS=3600)
class OrderRateLimitTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/api/orders/")
        self.user = SimpleNamespace(pk=7)
        client = patch("shop.services.rate_limit._redis_client")
        self.redis_client = client.start().return_value
        self.addCleanup(client.stop)

    def test_allows_request_when_redis_allows_it(self):
        self.redis_client.eval.return_value = [1, 0]
        self.assertIsNone(enforce_order_creation_rate_limit(self.request, self.user))
        self.redis_client.eval.assert_called_once()

    def test_rejected_request_exposes_retry_delay(self):
        self.redis_client.eval.return_value = [0, 90]
        with self.assertRaises(OrderRateLimitExceeded) as caught:
            enforce_order_creation_rate_limit(self.request, self.user)
        self.assertEqual(caught.exception.retry_after, 90)

    def test_missing_retry_delay_falls_back_to_window(self):
        self.redis_client.eval.return_value = [0, 0]
        with self.assertRaises(OrderRateLimitExceeded) as caught:
            enforce_order_creation_rate_limit(self.request, self.user)
        self.assertEqual(caught.exception.retry_after, 3600)

    def test_redis_failure_blocks_order_creation(self):
        self.redis_client.eval.side_effect = redis.ConnectionError("unavailable")
        with self.assertRaises(OrderRateLimitUnavailable):
            enforce_order_creation_rate_limit(self.request, self.user)

    def test_retry_delay_is_at_least_one_second(self):
        for delay in (0, -5):
            with self.subTest(delay=delay):
                self.assertEqual(OrderRateLimitExceeded(delay).retry_after, 1)
