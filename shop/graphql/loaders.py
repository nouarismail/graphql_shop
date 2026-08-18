from promise import Promise
from promise.dataloader import DataLoader

from ..models import Category


class CategoryLoader(DataLoader):

    def batch_load_fn(self, category_ids):

        categories = Category.objects.filter(
            id__in=category_ids
        )

        categories_by_id = {
            category.id: category
            for category in categories
        }

        return Promise.resolve([
            categories_by_id.get(category_id)
            for category_id in category_ids
        ])