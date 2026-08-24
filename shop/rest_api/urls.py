from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet, LoginView, LogoutView, MeView, OrderViewSet,
    ProductViewSet, RefreshTokenView, SignupView,
)


router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("auth/signup/", SignupView.as_view(), name="rest-signup"),
    path("auth/login/", LoginView.as_view(), name="rest-login"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="rest-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="rest-logout"),
    path("auth/me/", MeView.as_view(), name="rest-me"),
    path("", include(router.urls)),
]
