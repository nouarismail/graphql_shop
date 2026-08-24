from graphene_django.filter import DjangoFilterConnectionField

from ..services.catalog_cache import cached_or_load


class CachedDjangoFilterConnectionField(DjangoFilterConnectionField):
    """Cache a filtered product list before Relay pagination is applied."""

    @classmethod
    def resolve_queryset(
        cls,
        connection,
        iterable,
        info,
        args,
        filtering_args,
        filterset_class,
    ):
        queryset = super().resolve_queryset(
            connection,
            iterable,
            info,
            args,
            filtering_args,
            filterset_class,
        ).select_related("category")

        filter_arguments = {
            key: value for key, value in args.items() if key in filtering_args
        }
        return cached_or_load(
            "products",
            lambda: list(queryset),
            arguments=filter_arguments,
        )
