from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from shop.models import Category, Product, Order, OrderItem


class Command(BaseCommand):
    help = "Seed database with sample data"

    def handle(self, *args, **kwargs):

        # Users
        user1, _ = User.objects.get_or_create(
            username="alice",
            defaults={
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith",
            }
        )

        user2, _ = User.objects.get_or_create(
            username="bob",
            defaults={
                "email": "bob@example.com",
                "first_name": "Bob",
                "last_name": "Johnson",
            }
        )

        # Categories
        electronics, _ = Category.objects.get_or_create(
            name="Electronics"
        )

        books, _ = Category.objects.get_or_create(
            name="Books"
        )

        # Products
        laptop, _ = Product.objects.get_or_create(
            name="Laptop",
            defaults={
                "description": "A powerful laptop",
                "price": 1200,
                "category": electronics,
            }
        )

        keyboard, _ = Product.objects.get_or_create(
            name="Mechanical Keyboard",
            defaults={
                "description": "RGB mechanical keyboard",
                "price": 100,
                "category": electronics,
            }
        )

        book, _ = Product.objects.get_or_create(
            name="GraphQL Book",
            defaults={
                "description": "Learn GraphQL from scratch",
                "price": 40,
                "category": books,
            }
        )

        # Order
        order, _ = Order.objects.get_or_create(
            user=user1
        )

        OrderItem.objects.get_or_create(
            order=order,
            product=laptop,
            defaults={"quantity": 1}
        )

        OrderItem.objects.get_or_create(
            order=order,
            product=keyboard,
            defaults={"quantity": 2}
        )

        self.stdout.write(
            self.style.SUCCESS("Database seeded successfully!")
        )