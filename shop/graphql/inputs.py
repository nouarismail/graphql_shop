import graphene



class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    price = graphene.Decimal(required=True)
    category_id = graphene.ID(required=True)
    
class OrderStatusEnum(graphene.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    
class OrderItemInput(graphene.InputObjectType):
    product_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)