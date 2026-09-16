from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "action", "actor_id", "source", "object_type", "object_id", "request_id")
    list_filter = ("action", "source", "object_type", "occurred_at")
    search_fields = ("object_id", "=actor_id", "=request_id")
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    date_hierarchy = "occurred_at"
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
