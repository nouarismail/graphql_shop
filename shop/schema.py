# import graphene
# from graphene_django.types import DjangoObjectType
# from shop.models import Category, Product, Order, OrderItem
# from django.contrib.auth.models import User
# from decimal import Decimal

# class CategoryType(DjangoObjectType):
#     class Meta:
#         model = Category
#         fields = ("id", "name", "description", "products")
        
# class ProductType(DjangoObjectType):
#     price_with_tax = graphene.Float()
#     class Meta:
#         model = Product
#         fields = ("id", "name", "description", "price", "category")
#     def resolve_price_with_tax(self, info):
#         return self.price * Decimal("1.2")  # Assuming a 20% tax rate
        
# class OrderType(DjangoObjectType):
#     class Meta:
#         model = Order
#         fields = ("id", "user", "created_at", "updated_at", "items")
        
# class OrderItemType(DjangoObjectType):
#     class Meta:
#         model = OrderItem
#         fields = ("id", "order", "product", "quantity")
        
# class UserType(DjangoObjectType):
#     class Meta:
#         model = User
#         fields = ("id", "username", "email", "first_name", "last_name", "orders")
        
# class ProductInput(graphene.InputObjectType):
#     name = graphene.String(required=True)
#     description = graphene.String()
#     price = graphene.Float(required=True)
#     category_id = graphene.ID(required=True)
    
# me = graphene.Field(UserType)



# class Query(graphene.ObjectType):
#     user = graphene.Field(UserType, id=graphene.Int())
#     product = graphene.Field(ProductType, id=graphene.Int())
#     users = graphene.List(UserType)
#     categories = graphene.List(CategoryType)
#     products = graphene.List(ProductType)
#     orders = graphene.List(OrderType)
#     me = graphene.Field(UserType)

#     def resolve_me(root, info):

#         user = info.context.user

#         if user.is_anonymous:
#             return None

#         return user

#     def resolve_categories(root, info):
#         return Category.objects.all()

#     def resolve_products(root, info):
#         return Product.objects.all()

#     def resolve_orders(root, info):
#         return Order.objects.all()
    
#     def resolve_users(root, info):
#         return User.objects.all()
    
#     def resolve_product(root, info, id):
#         try:
#             return Product.objects.get(pk=id)
#         except Product.DoesNotExist:
#             return None
        
# class CreateProduct(graphene.Mutation):

#     class Arguments:
#         input = ProductInput(required=True)

#     product = graphene.Field(ProductType)

#     def mutate(root, info, input):
#         user = require_authenticated(info)

#         try:
#             category = Category.objects.get(
#             id=input.category_id
#         )
#         except Category.DoesNotExist:
#             raise Exception("Category does not exist")

#         product = Product.objects.create(
#             name=input.name,
#             description=input.description,
#             price=input.price,
#             category=category,
#         )

#         return CreateProduct(product=product)
    
# class UpdateProduct(graphene.Mutation):

#     class Arguments:
#         id = graphene.ID(required=True)
#         input = ProductInput(required=True)

#     product = graphene.Field(ProductType)

#     def mutate(root, info, id, input):

#         try:
#             product = Product.objects.get(id=id)
#         except Product.DoesNotExist:
#             raise Exception("Product does not exist")

#         try:
#             category = Category.objects.get(
#                 id=input.category_id
#             )
#         except Category.DoesNotExist:
#             raise Exception("Category does not exist")

#         product.name = input.name
#         product.description = input.description
#         product.price = input.price
#         product.category = category

#         product.save()

#         return UpdateProduct(product=product)
    
# class DeleteProduct(graphene.Mutation):

#     class Arguments:
#         id = graphene.ID(required=True)

#     success = graphene.Boolean()

#     def mutate(root, info, id):

#         try:
#             product = Product.objects.get(id=id)
#         except Product.DoesNotExist:
#             raise Exception("Product does not exist")   

#         product.delete()

#         return DeleteProduct(success=True)
    
# class Mutation(graphene.ObjectType):

#     create_product = CreateProduct.Field()
#     update_product = UpdateProduct.Field()
#     delete_product = DeleteProduct.Field()

# schema = graphene.Schema(query=Query, mutation=Mutation)   