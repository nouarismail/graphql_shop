import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)
VERSION_KEY = "catalog:version"
CACHE_MISS = object()


def _catalog_version():
    try:
        return cache.get(VERSION_KEY, 1)
    except RedisError:
        logger.warning("Redis catalog cache is unavailable", exc_info=True)
        return None


def build_cache_key(resource, arguments=None):
    version = _catalog_version()
    if version is None:
        return None

    serialized = json.dumps(
        arguments or {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    return f"catalog:v{version}:{resource}:{digest}"


def cached_or_load(resource, loader, arguments=None):
    key = build_cache_key(resource, arguments)
    if key is not None:
        try:
            cached_value = cache.get(key, CACHE_MISS)
            if cached_value is not CACHE_MISS:
                return cached_value
        except RedisError:
            logger.warning("Redis catalog cache read failed", exc_info=True)

    value = loader()

    if key is not None:
        try:
            cache.set(key, value, timeout=settings.CATALOG_CACHE_TIMEOUT)
        except RedisError:
            logger.warning("Redis catalog cache write failed", exc_info=True)

    return value


def invalidate_catalog_cache():
    try:
        if cache.add(VERSION_KEY, 2, timeout=None):
            return 2
        return cache.incr(VERSION_KEY)
    except RedisError:
        # Database writes must remain available when this performance cache is down.
        logger.warning("Redis catalog cache invalidation failed", exc_info=True)
        return None
