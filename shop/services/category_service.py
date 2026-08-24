from ..models import Category
from .id_service import decode_global_id

_UNSET = object()


def create_category(name, description=None):
    return Category.objects.create(name=name, description=description)


def update_category(global_id, name, description=_UNSET):
    category = _get_category(global_id)
    category.name = name
    update_fields = ["name"]
    if description is not _UNSET:
        category.description = description
        update_fields.append("description")
    category.save(update_fields=update_fields)
    return category


def delete_category(global_id):
    category = _get_category(global_id)
    category.delete()
    return True


def _get_category(global_id):
    database_id = decode_global_id(global_id, "CategoryType", "Category")
    try:
        return Category.objects.get(id=database_id)
    except Category.DoesNotExist:
        raise Exception("Category does not exist")
