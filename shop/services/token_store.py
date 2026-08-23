import math
import time
from functools import lru_cache

import redis
from django.conf import settings


class TokenStoreUnavailable(Exception):
    """Raised when token state cannot be safely read from or written to Redis."""


@lru_cache(maxsize=1)
def get_redis_client():
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    )


def _key(kind, identifier):
    return f"{settings.REDIS_TOKEN_KEY_PREFIX}:{kind}:{identifier}"


def _run(command):
    try:
        return command()
    except redis.RedisError as exc:
        # Authentication must fail closed when Redis cannot verify token state.
        raise TokenStoreUnavailable("Token store is unavailable") from exc


def get_user_token_version(user_id):
    value = _run(lambda: get_redis_client().get(_key("version", user_id)))
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TokenStoreUnavailable("Token store contains an invalid version") from exc


def increment_user_token_version(user_id):
    return _run(lambda: get_redis_client().incr(_key("version", user_id)))


def is_refresh_token_revoked(jti):
    return bool(_run(lambda: get_redis_client().exists(_key("revoked", jti))))


def revoke_refresh_token(jti, expires_at):
    ttl = math.ceil(expires_at - time.time())
    if ttl <= 0:
        return False

    # NX makes token consumption atomic: only one concurrent refresh/logout wins.
    return bool(
        _run(
            lambda: get_redis_client().set(
                _key("revoked", jti),
                "1",
                ex=ttl,
                nx=True,
            )
        )
    )
