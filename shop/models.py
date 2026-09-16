from django.db import models, router, transaction

# Create your models here.

from django.contrib.auth.models import User

class AuditedModel(models.Model):
    """Keep each ordinary model save and its audit event in one transaction."""
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .audit import record_event, snapshot

        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            previous = None
            if self.pk is not None:
                previous = type(self).objects.using(using).select_for_update().filter(pk=self.pk).first()
            before = snapshot(previous) if previous is not None else {}
            super().save(*args, **kwargs)
            persisted = type(self).objects.using(using).get(pk=self.pk)
            after = snapshot(persisted)
            changes = {key: {"before": before.get(key), "after": value}
                       for key, value in after.items()
                       if previous is None or before.get(key) != value}
            if changes:
                record_event("create" if previous is None else "update",
                             instance=self, changes=changes, using=using)


class AuditEvent(models.Model):
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=40, db_index=True)
    # A scalar ID preserves attribution after the user is deleted.
    actor_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    source = models.CharField(max_length=80, default="system")
    request_id = models.UUIDField(null=True, blank=True, db_index=True)
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        default_permissions = ("view",)
        indexes = [models.Index(fields=["object_type", "object_id"], name="audit_object_idx")]


class Category(AuditedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Product(AuditedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name
    
class Order(AuditedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='PENDING')

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
class OrderItem(AuditedModel):
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
    
