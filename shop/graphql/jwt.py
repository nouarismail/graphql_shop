import jwt

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth.models import User

def generate_access_token(user):

    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "iat": now,
        "exp": now + timedelta(
            seconds=settings.JWT_ACCESS_TOKEN_LIFETIME
        ),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
def decode_access_token(token):

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        return payload

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None
    
def get_user_from_token(token):

    payload = decode_access_token(token)

    if not payload:
        return None

    try:

        return User.objects.get(
            id=payload["user_id"]
        )

    except User.DoesNotExist:
        return None