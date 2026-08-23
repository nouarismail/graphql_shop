import jwt
import uuid

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth.models import User

from ..services.token_store import (
    get_user_token_version,
    increment_user_token_version,
    is_refresh_token_revoked,
    revoke_refresh_token as store_revoked_refresh_token,
)


def _generate_token(user, token_type, lifetime):

    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user.id,
        "username": user.username,
        "token_type": token_type,
        "token_version": get_user_token_version(user.id),
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
    }

    if token_type == "refresh":
        payload["jti"] = str(uuid.uuid4())

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def generate_access_token(user):

    return _generate_token(
        user,
        "access",
        settings.JWT_ACCESS_TOKEN_LIFETIME,
    )


def generate_refresh_token(user):

    return _generate_token(
        user,
        "refresh",
        settings.JWT_REFRESH_TOKEN_LIFETIME,
    )


def _decode_token(token, expected_type):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("token_type") != expected_type:
            return None

        return payload

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def decode_access_token(token):

    return _decode_token(token, "access")


def decode_refresh_token(token):

    payload = _decode_token(token, "refresh")

    if not payload or not payload.get("jti"):
        return None

    if is_refresh_token_revoked(payload["jti"]):
        return None

    return payload


def revoke_refresh_token(token):

    payload = _decode_token(token, "refresh")

    if not payload or not payload.get("jti"):
        return False

    try:
        expires_at = float(payload["exp"])
    except (KeyError, TypeError, ValueError):
        return False

    return store_revoked_refresh_token(payload["jti"], expires_at)


def get_user_from_refresh_token(token):

    payload = decode_refresh_token(token)

    if not payload:
        return None

    try:
        user = User.objects.get(id=payload["user_id"], is_active=True)
    except (User.DoesNotExist, KeyError):
        return None

    if not _has_current_token_version(user, payload):
        return None

    return user


def invalidate_user_tokens(user):
    return increment_user_token_version(user.id)


def _has_current_token_version(user, payload):

    try:
        token_version = payload["token_version"]
    except KeyError:
        return False

    return token_version == get_user_token_version(user.id)


def get_user_from_token(token):

    payload = decode_access_token(token)

    if not payload:
        return None

    try:

        user = User.objects.get(id=payload["user_id"], is_active=True)

    except (User.DoesNotExist, KeyError):
        return None

    if not _has_current_token_version(user, payload):
        return None

    return user
