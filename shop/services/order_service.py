from django.db import transaction

from ..models import Order, OrderItem, Product
from .id_service import decode_global_id

ALLOWED_ORDER_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "PROCESSING",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
}


def _validate_quantity(quantity):
    if quantity <= 0:
        raise Exception("Quantity must be greater than zero")


def _get_order(global_id):
    database_id = decode_global_id(global_id, "OrderType", "Order")
    try:
        return Order.objects.get(id=database_id)
    except Order.DoesNotExist:
        raise Exception("Order does not exist")


def _get_product(global_id):
    database_id = decode_global_id(global_id, "ProductType", "Product")
    try:
        return Product.objects.get(id=database_id)
    except Product.DoesNotExist:
        raise Exception("Product does not exist")


@transaction.atomic
def create_order(user, items):
    if not items:
        raise Exception("Order must contain at least one item")

    order = Order.objects.create(user=user, status="PENDING")
    for item in items:
        _validate_quantity(item.quantity)
        OrderItem.objects.create(
            order=order,
            product=_get_product(item.product_id),
            quantity=item.quantity,
        )
    return order


@transaction.atomic
def add_order_item(order_id, product_id, quantity, authorize):
    _validate_quantity(quantity)
    order = _get_order(order_id)
    authorize(order)
    product = _get_product(product_id)
    item, created = OrderItem.objects.get_or_create(
        order=order,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])
    return order


@transaction.atomic
def remove_order_item(order_id, item_id, authorize):
    order = _get_order(order_id)
    authorize(order)
    database_item_id = decode_global_id(item_id, "OrderItemType", "Order Item")
    try:
        item = OrderItem.objects.get(id=database_item_id, order=order)
    except OrderItem.DoesNotExist:
        raise Exception("Order item does not exist")
    item.delete()
    return order


@transaction.atomic
def update_order_item_quantity(item_id, quantity, authorize):
    _validate_quantity(quantity)
    database_item_id = decode_global_id(item_id, "OrderItemType", "Order Item")
    try:
        item = OrderItem.objects.select_related("order").get(id=database_item_id)
    except OrderItem.DoesNotExist:
        raise Exception("Order item does not exist")
    authorize(item.order)
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item.order


@transaction.atomic
def cancel_order(order_id, authorize):
    order = _get_order(order_id)
    authorize(order)
    order.status = "CANCELLED"
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def update_order_status(order_id, status):
    order = _get_order(order_id)
    status_value = status.value if hasattr(status, "value") else status
    if status_value not in ALLOWED_ORDER_STATUSES:
        raise Exception("Invalid order status")
    order.status = status_value
    order.save(update_fields=["status"])
    return order
