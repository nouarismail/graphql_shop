import graphene
from graphql_relay import from_global_id
from  .types import ProductConnection, UserType, ProductType, CategoryType, OrderType
from ..models import Category, Product, Order
from django.contrib.auth.models import User
from graphene_django.filter import DjangoFilterConnectionField
from .filters import ProductFilter
from .auth import get_current_user
from .permissions import can_view_order, get_visible_orders

class Query(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int())
    product = graphene.Field(
        ProductType,
        id=graphene.ID(required=True)
    )
    users = graphene.List(UserType)
    categories = graphene.List(CategoryType)
    node = graphene.relay.Node.Field()
    products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
    )
    orders = graphene.List(OrderType)
    order = graphene.Field(
        OrderType,
        id=graphene.ID(required=True),
    )
    me = graphene.Field(UserType)

    def resolve_me(root, info):

        user = get_current_user(info)


        return user

    def resolve_categories(root, info):
        return Category.objects.all()

    # def resolve_products(root, info, category_id=None, min_price=None, max_price=None, limit=None, offset=None):
    #     queryset = Product.objects.select_related("category")
    #     if category_id:
    #         queryset = queryset.filter(category_id=category_id)
    #     if min_price is not None:
    #         queryset = queryset.filter(price__gte=min_price)
    #     if max_price is not None:
    #         queryset = queryset.filter(price__lte=max_price)
            
    #     total_count = queryset.count()

    #     offset = max(offset, 0)

    #     limit = min(limit, 100)

    #     products = queryset[
    #         offset:offset + limit
    #     ]

    #     has_next_page = (
    #         offset + limit < total_count
    #     )

    #     return ProductConnection(
    #         items=products,
    #         total_count=total_count,
    #         has_next_page=has_next_page,
    #     )

    def resolve_orders(root, info):
        return (
            get_visible_orders(info)
            .select_related("user")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    def resolve_order(root, info, id):

        try:
            type_name, database_id = from_global_id(id)
        except (TypeError, ValueError, UnicodeDecodeError):
            raise Exception("Invalid Order ID")

        if type_name != "OrderType" or not database_id.isdigit():
            raise Exception("Invalid Order ID")

        try:
            order = (
                Order.objects
                .select_related("user")
                .prefetch_related("items__product")
                .get(id=database_id)
            )
        except Order.DoesNotExist:
            raise Exception("Order does not exist")

        can_view_order(info, order)

        return order
    
    def resolve_users(root, info):
        return User.objects.all()
    
    def resolve_product(self, info, id):

        type_name, database_id = from_global_id(id)

        if type_name != "ProductType":
            raise Exception("Invalid Product ID")

        return Product.objects.get(id=database_id)
