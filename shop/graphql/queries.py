import graphene
from  .types import ProductConnection, UserType, ProductType, CategoryType, OrderType
from ..models import Category, Product, Order
from django.contrib.auth.models import User
from graphene_django.filter import DjangoFilterConnectionField
from .filters import ProductFilter

class Query(graphene.ObjectType):
    user = graphene.Field(UserType, id=graphene.Int())
    product = graphene.Field(ProductType, id=graphene.Int())
    users = graphene.List(UserType)
    categories = graphene.List(CategoryType)
    products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
    )
    orders = graphene.List(OrderType)
    me = graphene.Field(UserType)

    def resolve_me(root, info):

        user = info.context.user

        if user.is_anonymous:
            return None

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
        return Order.objects.all()
    
    def resolve_users(root, info):
        return User.objects.all()
    
    def resolve_product(root, info, id):
        try:
            return Product.objects.get(pk=id)
        except Product.DoesNotExist:
            return None