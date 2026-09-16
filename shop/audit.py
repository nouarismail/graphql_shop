"""Request-scoped attribution and deliberately allowlisted audit snapshots."""
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from uuid import uuid4

_context = ContextVar("audit_context", default=None)
FIELDS = {
    "shop.category": ("name",),
    "shop.product": ("name", "price", "category_id"),
    "shop.order": ("user_id", "status"),
    "shop.orderitem": ("order_id", "product_id", "quantity"),
}


@contextmanager
def audit_context(*, request=None, source="system"):
    token = _context.set({"request": request, "source": source, "actor": None,
                          "request_id": uuid4()})
    try:
        yield _context.get()
    finally:
        _context.reset(token)


def set_audit_actor(user):
    context = _context.get()
    if context is not None:
        context["actor"] = user


def snapshot(instance):
    return {field: str(value) if isinstance(value, Decimal) else value
            for field in FIELDS[instance._meta.label_lower]
            for value in [getattr(instance, field)]}


def record_event(action, *, instance=None, changes=None, actor=None, using="default"):
    from .models import AuditEvent

    context = _context.get() or {}
    request = context.get("request")
    actor = actor or context.get("actor") or getattr(request, "user", None)
    actor_id = actor.pk if actor is not None and actor.is_authenticated else None
    return AuditEvent.objects.using(using).create(
        action=action, actor_id=actor_id,
        source=context.get("source", "system"),
        request_id=context.get("request_id"),
        object_type=instance._meta.label_lower if instance is not None else "",
        object_id=str(instance.pk) if instance is not None else "",
        changes=changes or {},
    )


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with audit_context(request=request, source="http") as context:
            response = self.get_response(request)
            response["X-Request-ID"] = str(context["request_id"])
            return response
