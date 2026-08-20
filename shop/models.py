from django.db import models

# Create your models here.

from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name
    
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='PENDING')

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"


class RevokedRefreshToken(models.Model):
    jti = models.CharField(max_length=36, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="revoked_refresh_tokens",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revoked refresh token for {self.user.username}"


class UserTokenState(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="token_state",
    )
    version = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"Token state for {self.user.username}"
    
