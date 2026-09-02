import django_filters
from django.db.models import Q

from ..models import Product


class ProductFilter(django_filters.FilterSet):

    search = django_filters.CharFilter(method="filter_search")

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
            "search",
            "min_price",
            "max_price",
            "category_id",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )
