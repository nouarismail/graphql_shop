# graphql/types.py

from django.contrib.auth.models import User
from decimal import Decimal
import graphene
from graphene_django import DjangoObjectType

from ..models import Category, Product, Order, OrderItem


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "products",
        )


class ProductType(DjangoObjectType):
    price_with_tax = graphene.Decimal()
    price = graphene.Decimal()
    
    class Meta:
        model = Product
        fields = ("id", "name", "description", "price", "category")
        
        interfaces = (graphene.relay.Node,)
        
    def resolve_price_with_tax(self, info):
        return self.price * Decimal("1.2") 
    
    
class ProductConnection(graphene.ObjectType):

    items = graphene.List(ProductType)

    total_count = graphene.Int()

    has_next_page = graphene.Boolean()


class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "quantity",
            "product",
        )
        interfaces = (graphene.relay.Node,)


class OrderType(DjangoObjectType):
    items = graphene.List(OrderItemType, required=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "items",
            "created_at",
            "status",
        )
        interfaces = (graphene.relay.Node,)

    def resolve_items(self, info):
        return self.items.all()


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "orders",
        )
        interfaces = (
            graphene.relay.Node,
        )
