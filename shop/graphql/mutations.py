import graphene
from graphql_relay import from_global_id

from shop.graphql.inputs import ProductInput
from shop.graphql.jwt import generate_access_token
from shop.graphql.types import CategoryType, OrderType, ProductType, UserType

from ..models import Order, Product, Category

from ..services.product_service import create_product, update_product, delete_product

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User

from .permissions import (can_cancel_order, can_create_category, can_create_order, can_create_product, can_delete_category, can_delete_product, can_delete_product, can_update_category, can_update_order, can_update_product,)


class CreateProduct(graphene.Mutation):

    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, input):
        can_create_product(info)


        product = create_product(input, info.context.user)

        return CreateProduct(product=product)
    
    
    
class UpdateProduct(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        id,
        input,
    ):
        can_update_product(info)
        type_name, database_id = from_global_id(id)

        if type_name != "ProductType":
            raise Exception("Invalid Product ID")

        product = Product.objects.get(id=database_id)

        product = update_product(database_id, input, info.context.user)


        return UpdateProduct(product=product)
    
class DeleteProduct(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate(
        cls,
        root,
        info,
        id,
    ):
        
        can_delete_product(info)
        type_name, database_id = from_global_id(id) 

        if type_name != "ProductType":
            raise Exception("Invalid Product ID")

        

        success = delete_product(database_id,  info.context.user)


        return DeleteProduct(success=success)
    
class CreateCategory(graphene.Mutation):

    class Arguments:
        name = graphene.String(required=True)

    category = graphene.Field(CategoryType)

    @classmethod
    def mutate(cls, root, info, name):

        can_create_category(info)

        category = Category.objects.create(
            name=name
        )

        return CreateCategory(
            category=category
        )


class UpdateCategory(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=True)

    category = graphene.Field(CategoryType)

    @classmethod
    def mutate(cls, root, info, id, name):

        can_update_category(info)

        _, database_id = from_global_id(id)

        category = Category.objects.get(
            id=database_id
        )

        category.name = name
        category.save()

        return UpdateCategory(
            category=category
        )
        
        

class DeleteCategory(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):

        can_delete_category(info)

        _, database_id = from_global_id(id)

        category = Category.objects.get(
            id=database_id
        )

        category.delete()

        return DeleteCategory(
            success=True
        )
        
class CreateOrder(graphene.Mutation):

    class Arguments:
        # We'll add product/items later
        pass

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info):

        user = can_create_order(info)

        order = Order.objects.create(
            user=user,
            status="PENDING"
        )

        return CreateOrder(
            order=order
        )        

class UpdateOrderStatus(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)
        status = graphene.String(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, id, status):

        

        _, database_id = from_global_id(id)

        order = Order.objects.get(
            id=database_id
        )
        
        can_update_order(info,order)

        allowed_statuses = [
            "PENDING",
            "CONFIRMED",
            "PROCESSING",
            "SHIPPED",
            "DELIVERED",
            "CANCELLED",
        ]

        if status not in allowed_statuses:
            raise Exception(
                "Invalid order status"
            )

        order.status = status
        order.save()

        return UpdateOrderStatus(
            order=order
        )
        
class CancelOrder(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, id):

        _, database_id = from_global_id(id)

        order = Order.objects.get(
            id=database_id
        )

        can_cancel_order(
            info,
            order
        )

        order.status = "CANCELLED"
        order.save()

        return CancelOrder(
            order=order
        )

class Signup(graphene.Mutation):

    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    access_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        username,
        email,
        password,
    ):

        
        if User.objects.filter(
            username=username
        ).exists():
            raise Exception(
                "Username already exists"
            )

        
        if User.objects.filter(
            email=email
        ).exists():
            raise Exception(
                "Email already exists"
            )

        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        customer_group = Group.objects.get(name="Customer")

        user.groups.add(customer_group)
        
        token = generate_access_token(user)

        return Signup(
            access_token=token,
            user=user,
        )
        
class Login(graphene.Mutation):

    class Arguments:

        username = graphene.String(
            required=True
        )

        password = graphene.String(
            required=True
        )

    access_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        username,
        password,
    ):

        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            raise Exception(
                "Invalid username or password"
            )

        token = generate_access_token(user)

        return Login(
            access_token=token,
            user=user,
        )
    
class Mutation(graphene.ObjectType):

    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    
    
    signup = Signup.Field()
    login = Login.Field()