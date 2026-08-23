import time
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .services import token_store


@override_settings(
    REDIS_TOKEN_KEY_PREFIX="test:tokens",
    REDIS_URL="redis://localhost:6379/15",
    REDIS_SOCKET_TIMEOUT=1,
)
class TokenStoreTests(SimpleTestCase):
    def tearDown(self):
        token_store.get_redis_client.cache_clear()

    @patch("shop.services.token_store.get_redis_client")
    def test_missing_user_version_defaults_to_zero(self, get_client):
        get_client.return_value.get.return_value = None

        self.assertEqual(token_store.get_user_token_version(42), 0)
        get_client.return_value.get.assert_called_once_with("test:tokens:version:42")

    @patch("shop.services.token_store.get_redis_client")
    def test_increment_user_version_uses_atomic_redis_increment(self, get_client):
        get_client.return_value.incr.return_value = 3

        self.assertEqual(token_store.increment_user_token_version(42), 3)
        get_client.return_value.incr.assert_called_once_with("test:tokens:version:42")

    @patch("shop.services.token_store.get_redis_client")
    def test_revoke_refresh_token_uses_nx_and_expiration(self, get_client):
        get_client.return_value.set.return_value = True

        revoked = token_store.revoke_refresh_token("token-jti", time.time() + 60)

        self.assertTrue(revoked)
        args, kwargs = get_client.return_value.set.call_args
        self.assertEqual(args, ("test:tokens:revoked:token-jti", "1"))
        self.assertGreaterEqual(kwargs["ex"], 59)
        self.assertTrue(kwargs["nx"])

    @patch("shop.services.token_store.get_redis_client")
    def test_expired_refresh_token_is_not_written(self, get_client):
        self.assertFalse(token_store.revoke_refresh_token("expired", time.time() - 1))
        get_client.return_value.set.assert_not_called()

    @patch("shop.services.token_store.get_redis_client")
    def test_redis_errors_fail_closed(self, get_client):
        get_client.return_value.exists.side_effect = token_store.redis.RedisError("down")

        with self.assertRaises(token_store.TokenStoreUnavailable):
            token_store.is_refresh_token_revoked("token-jti")
