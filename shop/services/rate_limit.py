import hashlib
import uuid
from functools import lru_cache

import redis
from django.conf import settings


class OrderRateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, int(retry_after))
        super().__init__(
            f"Order creation limit exceeded. Try again in {self.retry_after} seconds."
        )


class OrderRateLimitUnavailable(Exception):
    pass


_CHECK_LIMIT_SCRIPT = """
local request_limit = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
local member = ARGV[3]
local now = redis.call('TIME')
local now_ms = (tonumber(now[1]) * 1000) + math.floor(tonumber(now[2]) / 1000)
local window_ms = window_seconds * 1000
local cutoff_ms = now_ms - window_ms

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', cutoff_ms)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', cutoff_ms)
local ip_count = redis.call('ZCARD', KEYS[1])
local user_count = redis.call('ZCARD', KEYS[2])

local retry_after = 0
if ip_count >= request_limit then
    local oldest_ip = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    retry_after = math.max(retry_after, math.ceil((oldest_ip[2] + window_ms - now_ms) / 1000))
end
if user_count >= request_limit then
    local oldest_user = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
    retry_after = math.max(retry_after, math.ceil((oldest_user[2] + window_ms - now_ms) / 1000))
end

if retry_after > 0 then
    return {0, retry_after}
end

redis.call('ZADD', KEYS[1], now_ms, member)
redis.call('ZADD', KEYS[2], now_ms, member)
redis.call('EXPIRE', KEYS[1], window_seconds)
redis.call('EXPIRE', KEYS[2], window_seconds)
return {1, 0}
"""


@lru_cache(maxsize=1)
def _redis_client():
    return redis.Redis.from_url(
        settings.RATE_LIMIT_REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    )


def _client_ip(request):
    if settings.ORDER_RATE_LIMIT_TRUST_PROXY:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def enforce_order_creation_rate_limit(request, user):
    ip_digest = hashlib.sha256(_client_ip(request).encode()).hexdigest()
    prefix = settings.ORDER_RATE_LIMIT_KEY_PREFIX
    keys = (
        f"{prefix}:ip:{ip_digest}",
        f"{prefix}:user:{user.pk}",
    )

    try:
        allowed, retry_after = _redis_client().eval(
            _CHECK_LIMIT_SCRIPT,
            len(keys),
            *keys,
            settings.ORDER_RATE_LIMIT_REQUESTS,
            settings.ORDER_RATE_LIMIT_WINDOW_SECONDS,
            uuid.uuid4().hex,
        )
    except redis.RedisError as exc:
        raise OrderRateLimitUnavailable(
            "Order creation rate limiter is temporarily unavailable."
        ) from exc

    if not allowed:
        raise OrderRateLimitExceeded(
            retry_after or settings.ORDER_RATE_LIMIT_WINDOW_SECONDS
        )
