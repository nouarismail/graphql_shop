from ..models import Product, Category

def create_product(input, user):
    # if user.is_anonymous:
    #     raise Exception("Authentication required")

    try:
        category = Category.objects.get(
            id=input.category_id
        )
    except Category.DoesNotExist:
        raise Exception("Category does not exist")

    product = Product.objects.create(
        name=input.name,
        description=input.description,
        price=input.price,
        category=category,
    )

    return product

def update_product(id, input, user):
    # if user.is_anonymous:
    #     raise Exception("Authentication required")

    try:
        product = Product.objects.get(id=id)
    except Product.DoesNotExist:
        raise Exception("Product does not exist")

    try:
        category = Category.objects.get(
            id=input.category_id
        )
    except Category.DoesNotExist:
        raise Exception("Category does not exist")

    product.name = input.name
    product.description = input.description
    product.price = input.price
    product.category = category

    product.save()

    return product

def get_product(id):
    try:
        return Product.objects.get(pk=id)
    except Product.DoesNotExist:
        return None 
    
def get_all_products():
    return Product.objects.all()

def delete_product(id, user):
    # if user.is_anonymous:
    #     raise Exception("Authentication required")

    try:
        product = Product.objects.get(id=id)
    except Product.DoesNotExist:
        raise Exception("Product does not exist")

    product.delete()
    return True

