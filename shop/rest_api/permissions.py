from rest_framework.permissions import SAFE_METHODS, BasePermission


class CatalogPermission(BasePermission):
    permission_map = {
        "POST": "add",
        "PUT": "change",
        "PATCH": "change",
        "DELETE": "delete",
    }

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        action = self.permission_map.get(request.method)
        model_name = view.queryset.model._meta.model_name
        return request.user.has_perm(f"shop.{action}_{model_name}")


class OrderPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "create":
            return request.user.has_perm("shop.add_order")
        if view.action == "update_status":
            return request.user.has_perm("shop.change_order")
        return request.user.has_perm("shop.view_order")


class StaffCsvPermission(BasePermission):
    """Restrict bulk data transfer to staff members with model permissions."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user.groups.filter(name="Staff").exists():
            return False
        if view.action == "import_csv":
            return user.has_perms(("shop.add_product", "shop.change_product"))
        if view.basename == "product":
            return user.has_perm("shop.view_product")
        return user.has_perm("shop.view_order")
