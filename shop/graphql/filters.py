import django_filters

from ..models import Product


class ProductFilter(django_filters.FilterSet):

    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )

    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )

    category_id = django_filters.NumberFilter(
        field_name="category_id",
        lookup_expr="exact",
    )
    
    order_by = django_filters.OrderingFilter(
        fields=(
            ("price", "price"),
            ("name", "name"),
            ("created_at", "created_at"),
            ("id", "id"),
        )
    )

    class Meta:
        model = Product

        fields = [
            "min_price",
            "max_price",
            "category_id",
        ]