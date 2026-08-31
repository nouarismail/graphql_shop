from decimal import Decimal, InvalidOperation
from io import StringIO

import pandas as pd
from django.db import transaction

from ..models import Category, OrderItem, Product


PRODUCT_COLUMNS = ["id", "name", "description", "price", "category_id"]
ORDER_COLUMNS = [
    "order_id", "created_at", "updated_at", "status", "customer_id",
    "customer_username", "customer_email", "item_id", "product_id",
    "product_name", "category_name", "unit_price",           "quantity", "line_total",
]


class CsvImportError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("The CSV contains invalid product rows")


def _csv_safe(value):
    """Prevent spreadsheet programs from interpreting exported text as formulas."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _as_csv(frame):
    buffer = StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def export_products_csv():
    rows = Product.objects.select_related("category").order_by("id").values(
        "id", "name", "description", "price", "category_id", "category__name"
    )
    frame = pd.DataFrame.from_records(rows).rename(
        columns={"category__name": "category_name"}
    )
    frame = frame.reindex(columns=PRODUCT_COLUMNS + ["category_name"])
    for column in ("name", "description", "category_name"):
        frame[column] = frame[column].map(_csv_safe)
    return _as_csv(frame)


def export_orders_csv():
    items = OrderItem.objects.select_related(
        "order__user", "product__category"
    ).order_by("order_id", "id")
    rows = []
    for item in items.iterator():
        order = item.order
        product = item.product
        rows.append({
            "order_id": order.id,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "status": _csv_safe(order.status),
            "customer_id": order.user_id,
            "customer_username": _csv_safe(order.user.username),
            "customer_email": _csv_safe(order.user.email),
            "item_id": item.id,
            "product_id": product.id,
            "product_name": _csv_safe(product.name),
            "category_name": _csv_safe(product.category.name),
            "unit_price": product.price,
            "quantity": item.quantity,
            "line_total": product.price * item.quantity,
        })
    return _as_csv(pd.DataFrame.from_records(rows, columns=ORDER_COLUMNS))


def _read_product_frame(uploaded_file):
    try:
        frame = pd.read_csv(
            uploaded_file, dtype=str, keep_default_na=False, encoding="utf-8-sig"
        )
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        raise CsvImportError([
            {"row": None, "errors": [f"Invalid CSV: {exc}"]}
        ]) from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    missing = sorted({"name", "price", "category_id"} - set(frame.columns))
    if missing:
        raise CsvImportError([{
            "row": None,
            "errors": [f"Missing required columns: {', '.join(missing)}"],
        }])
    if "id" not in frame:
        frame["id"] = ""
    if "description" not in frame:
        frame["description"] = ""
    return frame[PRODUCT_COLUMNS]


def import_products_csv(uploaded_file):
    frame = _read_product_frame(uploaded_file)
    category_ids = set(Category.objects.values_list("id", flat=True))
    existing_products = Product.objects.in_bulk()
    seen_ids = set()
    prepared = []
    errors = []

    for index, row in frame.iterrows():
        csv_row = index + 2
        row_errors = []
        name = row["name"].strip()
        description = row["description"]
        raw_id = row["id"].strip()

        if not name:
            row_errors.append("name is required")
        elif len(name) > Product._meta.get_field("name").max_length:
            row_errors.append("name must be at most 100 characters")

        try:
            price = Decimal(row["price"].strip())
            if not price.is_finite() or price < 0:
                raise InvalidOperation
            price = price.quantize(Decimal("0.01"))
            if price >= Decimal("100000000"):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            price = None
            row_errors.append(
                "price must be a non-negative decimal with at most 8 whole digits"
            )

        try:
            category_id = int(row["category_id"].strip())
            if category_id not in category_ids:
                row_errors.append(f"category_id {category_id} does not exist")
        except ValueError:
            category_id = None
            row_errors.append("category_id must be an integer")

        product_id = None
        if raw_id:
            try:
                product_id = int(raw_id)
                if product_id in seen_ids:
                    row_errors.append(f"duplicate product id {product_id} in CSV")
                elif product_id not in existing_products:
                    row_errors.append(f"product id {product_id} does not exist")
                seen_ids.add(product_id)
            except ValueError:
                row_errors.append("id must be an integer or blank")

        if row_errors:
            errors.append({"row": csv_row, "errors": row_errors})
        else:
            prepared.append((product_id, name, description, price, category_id))

    if errors:
        raise CsvImportError(errors)

    created = updated = 0
    with transaction.atomic():
        for product_id, name, description, price, category_id in prepared:
            if product_id is None:
                Product.objects.create(
                    name=name, description=description, price=price, category_id=category_id
                )
                created += 1
            else:
                product = existing_products[product_id]
                product.name = name
                product.description = description
                product.price = price
                product.category_id = category_id
                product.full_clean()
                product.save(update_fields=["name", "description", "price", "category"])
                updated += 1
    return {"created": created, "updated": updated, "total": created + updated}
