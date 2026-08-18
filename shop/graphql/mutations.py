import graphene

from shop.graphql.inputs import ProductInput
from shop.graphql.types import ProductType
from .auth import require_authenticated
from ..models import Product, Category

from ..services.product_service import create_product, update_product, delete_product


class CreateProduct(graphene.Mutation):

    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(root, info, input):
        product = create_product(input, info.context.user)

        return CreateProduct(product=product)
    
class UpdateProduct(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(root, info, id, input):
        product = update_product(id, input, info.context.user)

        return UpdateProduct(product=product)
    
class DeleteProduct(graphene.Mutation):

    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(root, info, id):

        try:
            product = Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise Exception("Product does not exist")   

        product.delete()

        return DeleteProduct(success=True)
    
class Mutation(graphene.ObjectType):

    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
