from .auth import get_current_user
from ..models import Order


def require_authentication(info):

    user = get_current_user(info)

    if user is None:
        raise Exception(
            "Authentication required"
        )

    return user

#
def require_permission(info, permission):

    user = require_authentication(info)

    if not user.has_perm(permission):
        raise Exception(
            "Permission denied"
        )

    return user

# Permission checks for product operations
def can_view_product(info):

    user = get_current_user(info)

    # Public operation
    if user is None:
        return None

    if user.has_perm("shop.view_product"):
        return user

    raise Exception("Permission denied")

def can_create_product(info):

    return require_permission(
        info,
        "shop.add_product",
    )
    
def can_update_product(info):

    return require_permission(
        info,
        "shop.change_product",
    )

def can_delete_product(info):

    return require_permission(
        info,
        "shop.delete_product",
    )   

# Permission checks for category operations
def can_view_category(info):

    user = get_current_user(info)

    # Public operation
    if user is None:
        return None

    if user.has_perm("shop.view_category"):
        return user

    raise Exception("Permission denied")

def can_create_category(info):

    return require_permission(
        info,
        "shop.add_category",
    )   
    
def can_update_category(info):

    return require_permission(
        info,
        "shop.change_category",
    )   
    
def can_delete_category(info):  

    return require_permission(
        info,
        "shop.delete_category",
    )

# Permission checks for order operations


def can_create_order(info):

    return require_permission(
        info,
        "shop.add_order",
    )
    
def can_view_order(info, order):

    user = require_authentication(info)

    # Admin
    if user.is_superuser:
        return user

    # Staff
    if (
        user.groups
        .filter(name="Staff")
        .exists()
        and user.has_perm("shop.view_order")
    ):
        return user

    # Customer : own order only
    if (
        user.has_perm("shop.view_order")
        and order.user_id == user.id
    ):
        return user

    raise Exception(
        "You cannot access this order"
    )


def get_visible_orders(info):

    user = require_authentication(info)

    if user.is_superuser:
        return Order.objects.all()

    if (
        user.groups.filter(name="Staff").exists()
        and user.has_perm("shop.view_order")
    ):
        return Order.objects.all()

    if user.has_perm("shop.view_order"):
        return Order.objects.filter(user=user)

    raise Exception("Permission denied")

def can_cancel_order(info, order):

    user = require_authentication(info)

    if user.is_superuser:
        return user

    if (
        user.groups.filter(name="Staff").exists()
        and user.has_perm("shop.change_order")
    ):
        return user

    if order.user_id != user.id:
        raise Exception(
            "You can only cancel your own orders"
        )

    if order.status not in [
        "PENDING",
        "CONFIRMED",
    ]:
        raise Exception(
            "This order can no longer be cancelled"
        )

    return user

def can_modify_order(info, order):

    user = require_authentication(info)

    # Admin
    if user.is_superuser:
        return user

    # Staff
    if (
        user.groups.filter(name="Staff").exists()
        and user.has_perm("shop.change_order")
    ):
        return user

    # Customer can modify only own pending order
    if order.user_id != user.id:
        raise Exception(
            "You can only modify your own orders"
        )

    if order.status != "PENDING":
        raise Exception(
            "Order items can only be modified while order is PENDING"
        )

    return user

def can_update_order(info):
    return require_permission(
        info,
        "shop.change_order"
    )
