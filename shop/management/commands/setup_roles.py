from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from shop.models import Product, Category, Order


class Command(BaseCommand):

    help = "Create application roles and assign permissions"

    def handle(self, *args, **kwargs):

        # --------------------------------------------------
        # Get content types
        # --------------------------------------------------

        product_ct = ContentType.objects.get_for_model(Product)
        category_ct = ContentType.objects.get_for_model(Category)
        order_ct = ContentType.objects.get_for_model(Order)

        # --------------------------------------------------
        # Get permissions
        # --------------------------------------------------

        product_permissions = Permission.objects.filter(
            content_type=product_ct,
        )

        category_permissions = Permission.objects.filter(
            content_type=category_ct,
        )

        order_permissions = Permission.objects.filter(
            content_type=order_ct,
        )

        # --------------------------------------------------
        # Customer
        # --------------------------------------------------

        customer_group, _ = Group.objects.get_or_create(
            name="Customer"
        )

        customer_group.permissions.set(
            [
                Permission.objects.get(
                    content_type=product_ct,
                    codename="view_product",
                ),

                Permission.objects.get(
                    content_type=category_ct,
                    codename="view_category",
                ),

                Permission.objects.get(
                    content_type=order_ct,
                    codename="add_order",
                ),

                Permission.objects.get(
                    content_type=order_ct,
                    codename="view_order",
                ),
            ]
        )

        # --------------------------------------------------
        # Staff
        # --------------------------------------------------

        staff_group, _ = Group.objects.get_or_create(
            name="Staff"
        )

        staff_group.permissions.set(
            list(product_permissions)
            + list(category_permissions)
            + list(order_permissions)
        )

        # --------------------------------------------------
        # Output
        # --------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "Roles and permissions created successfully."
            )
        )