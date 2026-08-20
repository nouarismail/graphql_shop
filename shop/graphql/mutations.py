import graphene
from graphql_relay import from_global_id
from django.db import transaction

from shop.graphql.inputs import OrderItemInput, OrderStatusEnum, ProductInput
from shop.graphql.jwt import (
    generate_access_token,
    generate_refresh_token,
    get_user_from_refresh_token,
    revoke_refresh_token,
)
from shop.graphql.types import CategoryType, OrderType, ProductType, UserType

from ..models import Order, OrderItem, Product, Category

from ..services.product_service import create_product, update_product, delete_product

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User

from .permissions import (can_cancel_order, can_create_category, can_create_order, can_create_product, can_delete_category, can_delete_product, can_delete_product, can_modify_order, can_update_category, can_update_order, can_update_product,)


def decode_global_id(value, expected_type, label):
    try:
        type_name, database_id = from_global_id(value)
    except (TypeError, ValueError, UnicodeDecodeError):
        raise Exception(f"Invalid {label} ID")

    if type_name != expected_type or not database_id.isdigit():
        raise Exception(f"Invalid {label} ID")

    return database_id


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
        items = graphene.List(
            graphene.NonNull(OrderItemInput),
            required=True,
        )

    order = graphene.Field(OrderType)

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, items):

        user = can_create_order(info)

        if not items:
            raise Exception(
                "Order must contain at least one item"
            )

        order = Order.objects.create(
            user=user,
            status="PENDING",
        )

        for item in items:

            product_id = decode_global_id(
                item.product_id,
                "ProductType",
                "Product",
            )

            try:
                product = Product.objects.get(
                    id=product_id
                )
            except Product.DoesNotExist:
                raise Exception(
                    "Product does not exist"
                )

            if item.quantity <= 0:
                raise Exception(
                    "Quantity must be greater than zero"
                )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
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
        
class AddOrderItem(graphene.Mutation):

    class Arguments:
        order_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    @transaction.atomic
    def mutate(
        cls,
        root,
        info,
        order_id,
        product_id,
        quantity,
    ):

        if quantity <= 0:
            raise Exception(
                "Quantity must be greater than zero"
            )

        database_order_id = decode_global_id(
            order_id,
            "OrderType",
            "Order",
        )

        try:
            order = Order.objects.get(
                id=database_order_id
            )
        except Order.DoesNotExist:
            raise Exception(
                "Order does not exist"
            )

        can_modify_order(
            info,
            order
        )

        database_product_id = decode_global_id(
            product_id,
            "ProductType",
            "Product",
        )

        try:
            product = Product.objects.get(
                id=database_product_id
            )
        except Product.DoesNotExist:
            raise Exception(
                "Product does not exist"
            )

        order_item, created = (
            OrderItem.objects.get_or_create(
                order=order,
                product=product,
                defaults={
                    "quantity": quantity
                },
            )
        )

        if not created:
            order_item.quantity += quantity
            order_item.save(
                update_fields=["quantity"]
            )

        return AddOrderItem(
            order=order
        )


class RemoveOrderItem(graphene.Mutation):

    class Arguments:
        order_id = graphene.ID(required=True)
        item_id = graphene.ID(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate(
        cls,
        root,
        info,
        order_id,
        item_id,
    ):

        database_order_id = decode_global_id(
            order_id,
            "OrderType",
            "Order",
        )
        database_item_id = decode_global_id(
            item_id,
            "OrderItemType",
            "Order Item",
        )

        try:
            order = Order.objects.get(
                id=database_order_id
            )
        except Order.DoesNotExist:
            raise Exception(
                "Order does not exist"
            )

        can_modify_order(
            info,
            order
        )

        try:
            item = OrderItem.objects.get(
                id=database_item_id,
                order=order,
            )
        except OrderItem.DoesNotExist:
            raise Exception(
                "Order item does not exist"
            )

        item.delete()

        return RemoveOrderItem(
            order=order,
            success=True,
        )
        
class UpdateOrderItemQuantity(graphene.Mutation):

    class Arguments:
        item_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    @transaction.atomic
    def mutate(
        cls,
        root,
        info,
        item_id,
        quantity,
    ):

        if quantity <= 0:
            raise Exception(
                "Quantity must be greater than zero"
            )

        database_item_id = decode_global_id(
            item_id,
            "OrderItemType",
            "Order Item",
        )

        try:
            item = (
                OrderItem.objects
                .select_related("order")
                .get(id=database_item_id)
            )
        except OrderItem.DoesNotExist:
            raise Exception(
                "Order item does not exist"
            )

        can_modify_order(
            info,
            item.order
        )

        item.quantity = quantity

        item.save(
            update_fields=["quantity"]
        )

        return UpdateOrderItemQuantity(
            order=item.order
        )
class CancelOrder(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, id):

        database_id = decode_global_id(
            id,
            "OrderType",
            "Order",
        )

        try:
            order = Order.objects.get(
                id=database_id
            )
        except Order.DoesNotExist:
            raise Exception(
                "Order does not exist"
            )

        can_cancel_order(
            info,
            order
        )

        order.status = "CANCELLED"

        order.save(
            update_fields=["status"]
        )

        return CancelOrder(
            order=order,
            success=True,
        )

class UpdateOrderStatus(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

        status = OrderStatusEnum(
            required=True
        )

    order = graphene.Field(OrderType)

    @classmethod
    @transaction.atomic
    def mutate(
        cls,
        root,
        info,
        id,
        status,
    ):

        can_update_order(info)

        database_id = decode_global_id(
            id,
            "OrderType",
            "Order",
        )

        try:
            order = Order.objects.get(
                id=database_id
            )
        except Order.DoesNotExist:
            raise Exception(
                "Order does not exist"
            )

        order.status = status.value

        order.save(
            update_fields=["status"]
        )

        return UpdateOrderStatus(
            order=order
        )
        
class Signup(graphene.Mutation):

    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    access_token = graphene.String()
    refresh_token = graphene.String()
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
        
        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)

        return Signup(
            access_token=access_token,
            refresh_token=refresh_token,
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
    refresh_token = graphene.String()
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

        access_token = generate_access_token(user)
        refresh_token = generate_refresh_token(user)

        return Login(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
        )


class RefreshToken(graphene.Mutation):

    class Arguments:
        refresh_token = graphene.String(required=True)

    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, refresh_token):

        user = get_user_from_refresh_token(refresh_token)

        if user is None:
            raise Exception("Invalid or expired refresh token")

        revoke_refresh_token(refresh_token)

        return RefreshToken(
            access_token=generate_access_token(user),
            refresh_token=generate_refresh_token(user),
            user=user,
        )


class Logout(graphene.Mutation):

    class Arguments:
        refresh_token = graphene.String(required=True)

    success = graphene.Boolean(required=True)

    @classmethod
    def mutate(cls, root, info, refresh_token):

        if not revoke_refresh_token(refresh_token):
            raise Exception("Invalid or expired refresh token")

        return Logout(success=True)
    
class Mutation(graphene.ObjectType):

    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    
    create_order = CreateOrder.Field()
    add_order_item = AddOrderItem.Field()
    remove_order_item = RemoveOrderItem.Field()
    update_order_item_quantity = (
        UpdateOrderItemQuantity.Field()
    )

    cancel_order = CancelOrder.Field()

    update_order_status = (
        UpdateOrderStatus.Field()
    )
    
    
    signup = Signup.Field()
    login = Login.Field()
    refresh_token = RefreshToken.Field()
    logout = Logout.Field()
