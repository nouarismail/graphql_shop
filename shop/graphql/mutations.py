import graphene

from shop.graphql.inputs import OrderItemInput, OrderStatusEnum, ProductInput
from shop.graphql.types import CategoryType, OrderType, ProductType, UserType
from shop.services.auth_service import login, logout, refresh, signup
from shop.services.category_service import create_category, delete_category, update_category
from shop.services.order_service import (
    add_order_item, cancel_order, create_order, remove_order_item,
    update_order_item_quantity, update_order_status,
)
from shop.services.product_service import create_product, delete_product, update_product

from .permissions import (
    can_cancel_order, can_create_category, can_create_order, can_create_product,
    can_delete_category, can_delete_product, can_modify_order, can_update_category,
    can_update_order, can_update_product,
)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, input):
        can_create_product(info)
        return cls(product=create_product(input))


class UpdateProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = ProductInput(required=True)
    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, id, input):
        can_update_product(info)
        return cls(product=update_product(id, input))


class DeleteProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):
        can_delete_product(info)
        return cls(success=delete_product(id))


class CreateCategory(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
    category = graphene.Field(CategoryType)

    @classmethod
    def mutate(cls, root, info, name):
        can_create_category(info)
        return cls(category=create_category(name))


class UpdateCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=True)
    category = graphene.Field(CategoryType)

    @classmethod
    def mutate(cls, root, info, id, name):
        can_update_category(info)
        return cls(category=update_category(id, name))


class DeleteCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):
        can_delete_category(info)
        return cls(success=delete_category(id))


class CreateOrder(graphene.Mutation):
    class Arguments:
        items = graphene.List(graphene.NonNull(OrderItemInput), required=True)
    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, items):
        return cls(order=create_order(can_create_order(info), items))


class AddOrderItem(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)
    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, order_id, product_id, quantity):
        authorize = lambda order: can_modify_order(info, order)
        return cls(order=add_order_item(order_id, product_id, quantity, authorize))


class RemoveOrderItem(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)
        item_id = graphene.ID(required=True)
    order = graphene.Field(OrderType)
    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, order_id, item_id):
        authorize = lambda order: can_modify_order(info, order)
        return cls(order=remove_order_item(order_id, item_id, authorize), success=True)


class UpdateOrderItemQuantity(graphene.Mutation):
    class Arguments:
        item_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)
    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, item_id, quantity):
        authorize = lambda order: can_modify_order(info, order)
        return cls(order=update_order_item_quantity(item_id, quantity, authorize))


class CancelOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    order = graphene.Field(OrderType)
    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):
        authorize = lambda order: can_cancel_order(info, order)
        return cls(order=cancel_order(id, authorize), success=True)


class UpdateOrderStatus(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        status = OrderStatusEnum(required=True)
    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, id, status):
        can_update_order(info)
        return cls(order=update_order_status(id, status))


class Signup(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, username, email, password):
        return cls(**signup(username, email, password).__dict__)


class Login(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, username, password):
        return cls(**login(username, password).__dict__)


class RefreshToken(graphene.Mutation):
    class Arguments:
        refresh_token = graphene.String(required=True)
    access_token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, refresh_token):
        return cls(**refresh(refresh_token).__dict__)


class Logout(graphene.Mutation):
    class Arguments:
        refresh_token = graphene.String(required=True)
    success = graphene.Boolean(required=True)

    @classmethod
    def mutate(cls, root, info, refresh_token):
        return cls(success=logout(refresh_token))


class Mutation(graphene.ObjectType):
    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    create_order = CreateOrder.Field()
    add_order_item = AddOrderItem.Field()
    remove_order_item = RemoveOrderItem.Field()
    update_order_item_quantity = UpdateOrderItemQuantity.Field()
    cancel_order = CancelOrder.Field()
    update_order_status = UpdateOrderStatus.Field()
    signup = Signup.Field()
    login = Login.Field()
    refresh_token = RefreshToken.Field()
    logout = Logout.Field()
