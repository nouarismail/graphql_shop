from .loaders import CategoryLoader


class GraphQLContext:

    def __init__(self):
        self.category_loader = CategoryLoader()