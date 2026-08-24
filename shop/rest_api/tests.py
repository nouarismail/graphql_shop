from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from ..models import Product
from .authentication import JWTAuthentication
from .serializers import ProductSerializer
from .views import LoginView, ProductViewSet


class RestApiRoutingTests(SimpleTestCase):
    def test_authentication_routes_are_registered(self):
        self.assertIs(resolve(reverse("rest-login")).func.view_class, LoginView)

    def test_product_router_is_registered(self):
        match = resolve(reverse("product-list"))
        self.assertIs(match.func.cls, ProductViewSet)


class JWTAuthenticationTests(SimpleTestCase):
    factory = APIRequestFactory()

    @patch("shop.rest_api.authentication.get_user_from_token")
    def test_bearer_token_authenticates_user(self, get_user):
        user = AnonymousUser()
        get_user.return_value = user
        request = self.factory.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer token")

        authenticated_user, token = JWTAuthentication().authenticate(request)

        self.assertIs(authenticated_user, user)
        self.assertEqual(token, "token")

    @patch("shop.rest_api.authentication.get_user_from_token", return_value=None)
    def test_invalid_token_is_rejected(self, get_user):
        request = self.factory.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer invalid")

        with self.assertRaises(AuthenticationFailed):
            JWTAuthentication().authenticate(request)


class ProductSerializerTests(SimpleTestCase):
    def test_price_with_tax_uses_decimal_arithmetic(self):
        product = Product(name="Keyboard", price=Decimal("100.00"))

        self.assertEqual(ProductSerializer(product).data["price_with_tax"], 120.0)
