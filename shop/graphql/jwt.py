import jwt
import uuid

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import F

from ..models import RevokedRefreshToken, UserTokenState


def _generate_token(user, token_type, lifetime):

    now = datetime.now(timezone.utc)
    token_state, _ = UserTokenState.objects.get_or_create(user=user)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "token_type": token_type,
        "token_version": token_state.version,
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

    if RevokedRefreshToken.objects.filter(jti=payload["jti"]).exists():
        return None

    return payload


def revoke_refresh_token(token):

    payload = _decode_token(token, "refresh")

    if not payload or not payload.get("jti"):
        return False

    try:
        user = User.objects.get(id=payload["user_id"])
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except (User.DoesNotExist, KeyError, TypeError, ValueError):
        return False

    RevokedRefreshToken.objects.get_or_create(
        jti=payload["jti"],
        defaults={
            "user": user,
            "expires_at": expires_at,
        },
    )

    return True


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

    token_state, _ = UserTokenState.objects.get_or_create(user=user)
    UserTokenState.objects.filter(pk=token_state.pk).update(
        version=F("version") + 1
    )


def _has_current_token_version(user, payload):

    try:
        token_version = payload["token_version"]
    except KeyError:
        return False

    token_state, _ = UserTokenState.objects.get_or_create(user=user)
    return token_version == token_state.version


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
