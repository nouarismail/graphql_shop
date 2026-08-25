from types import SimpleNamespace

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from graphql_relay import to_global_id
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Category, Order, OrderItem, Product
from ..services import auth_service, category_service, order_service, product_service
from ..services.catalog_cache import cached_or_load
from .permissions import CatalogPermission, OrderPermission
from .serializers import (
    AddOrderItemSerializer, CategorySerializer, CreateOrderSerializer,
    LoginSerializer, OrderSerializer, ProductSerializer, RefreshTokenSerializer,
    SignupSerializer, UpdateOrderItemSerializer, UpdateOrderStatusSerializer,
    UserSerializer,
)


def _service_call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except APIException:
        raise
    except Exception as exc:
        raise ValidationError({"detail": str(exc)}) from exc


def _authentication_response(result):
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user": UserSerializer(result.user).data,
    }


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _service_call(auth_service.signup, **serializer.validated_data)
        return Response(_authentication_response(result), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _service_call(auth_service.login, **serializer.validated_data)
        return Response(_authentication_response(result))


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _service_call(auth_service.refresh, serializer.validated_data["refresh_token"])
        return Response(_authentication_response(result))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _service_call(auth_service.logout, serializer.validated_data["refresh_token"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").order_by("id")
    serializer_class = ProductSerializer
    permission_classes = [CatalogPermission]
    filterset_fields = {"category_id": ["exact"], "price": ["gte", "lte"]}
    ordering_fields = ["id", "name", "price"]
    search_fields = ["name", "description"]

    def list(self, request, *args, **kwargs):
        arguments = {key: request.query_params.getlist(key) for key in sorted(request.query_params)}

        def load():
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                return self.get_paginated_response(self.get_serializer(page, many=True).data).data
            return self.get_serializer(queryset, many=True).data

        return Response(cached_or_load("rest-products", load, arguments))

    def retrieve(self, request, *args, **kwargs):
        product_id = self.kwargs["pk"]
        product = cached_or_load(
            "rest-product",
            lambda: get_object_or_404(self.get_queryset(), pk=product_id),
            {"id": product_id},
        )
        return Response(self.get_serializer(product).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = _service_call(
            product_service.create_product,
            SimpleNamespace(**serializer.validated_data),
        )
        return Response(self.get_serializer(product).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        existing = self.get_object()
        serializer = self.get_serializer(
            existing,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        product = _service_call(
            product_service.update_product,
            to_global_id("ProductType", self.kwargs["pk"]),
            SimpleNamespace(
                name=values.get("name", existing.name),
                description=values.get("description", existing.description),
                price=values.get("price", existing.price),
                category_id=values.get("category_id", existing.category_id),
            ),
        )
        return Response(self.get_serializer(product).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object()
        _service_call(
            product_service.delete_product,
            to_global_id("ProductType", self.kwargs["pk"]),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.order_by("id")
    serializer_class = CategorySerializer
    permission_classes = [CatalogPermission]

    def list(self, request, *args, **kwargs):
        data = cached_or_load(
            "rest-categories",
            lambda: self.get_serializer(self.get_queryset(), many=True).data,
        )
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        category_id = self.kwargs["pk"]
        category = cached_or_load(
            "rest-category",
            lambda: get_object_or_404(self.get_queryset(), pk=category_id),
            {"id": category_id},
        )
        return Response(self.get_serializer(category).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = _service_call(category_service.create_category, **serializer.validated_data)
        return Response(self.get_serializer(category).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        existing = self.get_object()
        serializer = self.get_serializer(
            existing,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)
        category = _service_call(
            category_service.update_category,
            to_global_id("CategoryType", self.kwargs["pk"]),
            serializer.validated_data.get("name", existing.name),
            serializer.validated_data.get("description", existing.description),
        )
        return Response(self.get_serializer(category).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object()
        _service_call(
            category_service.delete_category,
            to_global_id("CategoryType", self.kwargs["pk"]),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [OrderPermission]

    def get_queryset(self):
        queryset = Order.objects.select_related("user").prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.select_related("product__category"))
        ).order_by("-created_at")
        user = self.request.user
        if user.is_superuser or (
            user.groups.filter(name="Staff").exists()
            and user.has_perm("shop.view_order")
        ):
            return queryset
        return queryset.filter(user=user)

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        order = self.get_object()
        return Response(self.get_serializer(order).data)

    def create(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = [
            SimpleNamespace(
                product_id=to_global_id("ProductType", item["product_id"]),
                quantity=item["quantity"],
            )
            for item in serializer.validated_data["items"]
        ]
        order = _service_call(order_service.create_order, request.user, items)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    def _authorize_modify(self, order):
        user = self.request.user
        if user.is_superuser or (
            user.groups.filter(name="Staff").exists()
            and user.has_perm("shop.change_order")
        ):
            return
        if order.user_id != user.id:
            raise PermissionDenied("You can only modify your own orders")
        if order.status != "PENDING":
            raise PermissionDenied("Order items can only be modified while order is PENDING")

    def _authorize_cancel(self, order):
        user = self.request.user
        if user.is_superuser or (
            user.groups.filter(name="Staff").exists()
            and user.has_perm("shop.change_order")
        ):
            return
        if order.user_id != user.id:
            raise PermissionDenied("You can only cancel your own orders")
        if order.status not in {"PENDING", "CONFIRMED"}:
            raise PermissionDenied("This order can no longer be cancelled")

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):
        self.get_object()
        serializer = AddOrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = _service_call(
            order_service.add_order_item,
            to_global_id("OrderType", pk),
            to_global_id("ProductType", serializer.validated_data["product_id"]),
            serializer.validated_data["quantity"],
            self._authorize_modify,
        )
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<item_id>[^/.]+)")
    def item(self, request, pk=None, item_id=None):
        order_from_url = self.get_object()
        get_object_or_404(OrderItem, pk=item_id, order=order_from_url)
        if request.method == "DELETE":
            order = _service_call(
                order_service.remove_order_item,
                to_global_id("OrderType", pk),
                to_global_id("OrderItemType", item_id),
                self._authorize_modify,
            )
        else:
            serializer = UpdateOrderItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            order = _service_call(
                order_service.update_order_item_quantity,
                to_global_id("OrderItemType", item_id),
                serializer.validated_data["quantity"],
                self._authorize_modify,
            )
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.get_object()
        order = _service_call(
            order_service.cancel_order,
            to_global_id("OrderType", pk),
            self._authorize_cancel,
        )
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        self.get_object()
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = _service_call(
            order_service.update_order_status,
            to_global_id("OrderType", pk),
            serializer.validated_data["status"],
        )
        return Response(self.get_serializer(order).data)
