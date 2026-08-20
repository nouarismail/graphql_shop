
from .jwt import get_user_from_token

# def require_authenticated(info):

#     user = info.context.user

#     if user.is_anonymous:
#         raise Exception("Authentication required")

#     return user



def get_current_user(info):

    authorization = info.context.headers.get(
        "Authorization"
    )

    if not authorization:
        return None

    parts = authorization.split()   

    if len(parts) != 2:
        return None

    if parts[0].lower() != "bearer":
        return None

    token = parts[1]

    return get_user_from_token(token)