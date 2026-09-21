"""Local and CI unit-test settings; use with --settings=config.test_settings."""

from .settings import *  # noqa: F403

SECRET_KEY = "unit-tests-only-not-for-deployment"
JWT_SECRET_KEY = SECRET_KEY
DEBUG = False

# Keep test commands independent of the deployed database and Redis cache.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
