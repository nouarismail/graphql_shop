def require_authenticated(info):

    user = info.context.user

    if user.is_anonymous:
        raise Exception("Authentication required")

    return user