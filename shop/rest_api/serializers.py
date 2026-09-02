from django.contrib.auth.models import User
from decimal import Decimal
from rest_framework import serializers

from ..models import Category, Order, OrderItem, Product
from ..services.order_service import ALLOWED_ORDER_STATUSES


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description")
        read_only_fields = ("id",)


class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True)
    category = CategorySerializer(read_only=True)
    price_with_tax = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "description", "price", "price_with_tax",
            "category_id", "category",
        )
        read_only_fields = ("id", "price_with_tax", "category")

    def get_price_with_tax(self, product):
        return product.price * Decimal("1.2")


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "quantity")


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "user", "status", "created_at", "updated_at", "items")


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, allow_empty=False)


class AddOrderItemSerializer(OrderItemInputSerializer):
    pass


class UpdateOrderItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=sorted(ALLOWED_ORDER_STATUSES))


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(trim_whitespace=False)


class AIProductSearchSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000, trim_whitespace=True)
