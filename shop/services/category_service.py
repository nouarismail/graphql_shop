from ..models import Category
from .id_service import decode_global_id


def create_category(name):
    return Category.objects.create(name=name)


def update_category(global_id, name):
    category = _get_category(global_id)
    category.name = name
    category.save(update_fields=["name"])
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
