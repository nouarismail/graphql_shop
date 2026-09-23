from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension

from ..graphql.jwt import get_user_from_token
from ..services.token_store import TokenStoreUnavailable


class JWTAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != self.keyword:
            raise AuthenticationFailed("Invalid Authorization header")

        try:
            token = header[1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid access token") from exc

        try:
            user = get_user_from_token(token)
        except TokenStoreUnavailable as exc:
            raise AuthenticationFailed("Authentication service is unavailable") from exc
        if user is None:
            raise AuthenticationFailed("Invalid or expired access token")
        from ..audit import set_audit_actor
        set_audit_actor(user)
        return user, token

    def authenticate_header(self, request):
        return "Bearer"


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "shop.rest_api.authentication.JWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
