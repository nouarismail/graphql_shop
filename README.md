# GraphQL Shop

A Django and Graphene API for a small online shop. The project supports products,
categories, customer orders, role-based permissions, Relay global IDs, and JWT
authentication with refresh-token rotation and immediate logout invalidation.

## Technology stack

- Python 3.12
- Django 6.1
- Graphene and Graphene-Django
- Django REST Framework
- PostgreSQL with Psycopg 3
- django-filter
- PyJWT
- Redis

## Features

- Product and category management
- Product filtering by price and category
- Redis caching for product and category queries
- Customer signup and login
- Short-lived access tokens and rotating refresh tokens
- Server-side refresh-token revocation
- Immediate logout through per-user token versions
- Customer and staff roles backed by Django permissions
- Order creation with multiple items
- Adding, removing, and changing order items
- Order cancellation and status updates
- Customer-specific order visibility
- Relay global IDs for products, users, orders, and order items
- REST endpoints mirroring the GraphQL authentication, catalog, and order workflows

## Project structure

```text
config/
  settings.py                 Django and JWT settings
  urls.py                     Admin and GraphQL routes
shop/
  graphql/
    auth.py                   Authorization-header handling
    filters.py                Product filters
    fields.py                 Redis-cached product connection field
    inputs.py                 GraphQL input and enum definitions
    jwt.py                    Token creation, validation, rotation, revocation
    mutations.py              GraphQL mutations
    permissions.py            Authentication, permission, and ownership checks
    queries.py                GraphQL queries
    schema.py                 Root GraphQL schema
    types.py                  Graphene Django object types
  rest_api/
    authentication.py        Bearer JWT authentication for DRF
    permissions.py           Catalog and order authorization policies
    serializers.py           REST request and response schemas
    urls.py                  REST router and authentication routes
    views.py                 Authentication, catalog, and order endpoints
  management/commands/
    seed.py                   Sample data command
    setup_roles.py            Customer and Staff role setup
  migrations/                 Database migrations
  services/
    auth_service.py           Signup, login, refresh, and logout workflows
    catalog_cache.py          Catalog cache keys, reads, and invalidation
    category_service.py       Category write operations
    id_service.py             Relay global ID validation
    order_service.py          Order and order-item write operations
    product_service.py        Product read and write operations
    token_store.py            Redis token revocation and version storage
  signals.py                  Catalog invalidation after model writes
  models.py                   Shop models and legacy token-state models
compose.yaml                  Local persistent Redis service
requirements.txt              Python dependencies
manage.py                     Django command-line entry point
```

## Local setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Redis

Refresh-token rotation and logout require Redis. The included service enables AOF
persistence and disables key eviction so logout state is not silently discarded:

```bash
docker compose up -d redis
docker compose ps
```

The application uses `redis://127.0.0.1:6379/0` by default. These environment
variables can override the connection:

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection URL and database |
| `REDIS_TOKEN_KEY_PREFIX` | `graphql-shop:tokens` | Namespace for authentication keys |
| `REDIS_SOCKET_TIMEOUT` | `2` | Connect/read timeout in seconds |
| `REDIS_CACHE_URL` | `redis://127.0.0.1:6379/1` | Product/category cache database |
| `CATALOG_CACHE_TIMEOUT` | `300` | Catalog entry lifetime in seconds |

Redis is security-critical for this implementation. If it is unavailable, token
creation and authentication fail closed instead of accepting a token whose
revocation state cannot be checked.

Catalog caching is isolated in Redis database `1`. Product lists are cached per
filter/order combination, individual products by ID, and categories with their
prefetched products. Product or category writes increment a catalog version key,
making older entries immediately unreachable. Unlike token storage, catalog
caching fails open: if Redis is unavailable, queries use PostgreSQL and writes
continue normally.

### 4. Create the PostgreSQL database

The development settings currently expect:

| Setting | Value |
|---|---|
| Database | `graphql_shop` |
| User | `graphql_user` |
| Password | `graphql_password` |
| Host | `localhost` |
| Port | `5432` |



### 5. Apply migrations

```bash
python manage.py migrate
```

Migrations `0003` and `0004` created the original database token-state tables.
They remain in migration history for compatibility, but current authentication
uses Redis and no longer reads or writes those tables.

### 6. Create roles and permissions

```bash
python manage.py setup_roles
```

This command creates Groups:

- `Customer`, with product/category viewing and order creation/viewing permissions.
- `Staff`, with all product, category, and order permissions.

Signup expects the `Customer` group to exist, so run this command before using the
`signup` mutation.

### 7. Seed data

```bash
python manage.py seed
```

The seed command creates sample users, categories, products,

### 8. Create an administrator

```bash
python manage.py createsuperuser
```

### 9. Run the development server

```bash
python manage.py runserver
```

Open GraphiQL at <http://127.0.0.1:8000/graphql/>. 

Django Admin is available at<http://127.0.0.1:8000/admin/>.

## Authentication

Authenticated operations require an access token in the HTTP header:

```http
Authorization: Bearer ACCESS_TOKEN
```


### Signup

The `Customer` role must already exist.

```graphql
mutation Signup {
  signup(
    username: "customer"
    email: "customer@example.com"
    password: "a-strong-password"
  ) {
    accessToken
    refreshToken
    user {
      id
      username
      email
    }
  }
}
```

### Login

```graphql
mutation Login {
  login(username: "customer", password: "a-strong-password") {
    accessToken
    refreshToken
    user {
      id
      username
    }
  }
}
```

### Current user

Send the access token in the `Authorization` header.

```graphql
query Me {
  me {
    id
    username
    email
  }
}
```

### Refresh the token pair

```graphql
mutation RefreshToken($token: String!) {
  refreshToken(refreshToken: "REFRESH_TOKEN") {
    accessToken
    refreshToken
    user {
      id
      username
    }
  }
}
```

### Logout

```graphql
mutation Logout($token: String!) {
  logout(refreshToken: $token) {
    success
  }
}
```

Logout performs two Redis-backed server-side actions:

1. It stores `graphql-shop:tokens:revoked:<jti>` with a TTL equal to the token's
   remaining lifetime.
2. It increments `graphql-shop:tokens:version:<user_id>`.

Every access and refresh token contains the version active when it was issued.
Authentication compares that claim to Redis. Once logout increments the Redis
version, all older access and refresh tokens are rejected immediately. Logout
therefore signs the user out on every device.

Refresh rotation writes the revocation key with Redis `SET NX EX`. `NX` means
only the first concurrent attempt can consume a refresh token; `EX` removes the
key automatically when the JWT would have expired, so the blacklist does not
grow indefinitely.

After a successful logout, the client should delete its stored access and refresh
tokens.



## Queries

### List products



```graphql
query Products {
  products(minPrice: 10, maxPrice: 1500) {
    edges {
      node {
        id
        name
        description
        price
        priceWithTax
        category {
          id
          name
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

Available filters include `minPrice`, `maxPrice`, and `categoryId`.

### Get one product

```graphql
query Product($id: ID!) {
  product(id: $id) {
    id
    name
    description
    price
    priceWithTax
  }
}
```

### List categories

```graphql
query Categories {
  categories {
    id
    name
    products {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
```

### List visible orders

This query requires authentication. Customers receive only their own orders.
Staff members with `shop.view_order` and superusers receive all orders.

```graphql
query Orders {
  orders {
    id
    status
    createdAt
    user {
      id
      username
    }
    items {
      id
      quantity
      product {
        id
        name
        price
      }
    }
  }
}
```

### Get one order

Customers can retrieve only an order they own.

```graphql
query Order($id: ID!) {
  order(id: $id) {
    id
    status
    createdAt
    items {
      id
      quantity
      product {
        id
        name
      }
    }
  }
}
```

## Product and category mutations

These operations require the corresponding Django permissions.

### Create a product

```graphql
mutation CreateProduct {
  createProduct(
    input: {
      name: "Mechanical Keyboard"
      description: "Hot-swappable keyboard"
      price: "99.90"
      categoryId: "1"
    }
  ) {
    product {
      id
      name
      price
    }
  }
}
```

### Update a product

```graphql
mutation UpdateProduct($id: ID!) {
  updateProduct(
    id: $id
    input: {
      name: "Updated Keyboard"
      description: "Updated description"
      price: "109.90"
      categoryId: "1"
    }
  ) {
    product {
      id
      name
      price
    }
  }
}
```

### Delete a product

```graphql
mutation DeleteProduct($id: ID!) {
  deleteProduct(id: $id) {
    success
  }
}
```

Category mutation classes exist internally, but they are not currently registered
on the root `Mutation` type and therefore are not exposed by the GraphQL API.

## Order mutations

### Create an order

Every `productId` must be a `ProductType` global ID. The operation is atomic: if
one item is invalid, the complete order creation is rolled back.

```graphql
mutation CreateOrder($items: [OrderItemInput!]!) {
  createOrder(items: $items) {
    order {
      id
      status
      items {
        id
        quantity
        product { id name }
      }
    }
  }
}
```

Variables:

```json
{
  "items": [
    { "productId": "PRODUCT_GLOBAL_ID", "quantity": 2 },
    { "productId": "ANOTHER_PRODUCT_GLOBAL_ID", "quantity": 1 }
  ]
}
```

### Add an item

Customers can modify only their own `PENDING` orders. Adding a product already in
the order increases its existing quantity.

```graphql
mutation AddOrderItem(
  $orderId: ID!
  $productId: ID!
  $quantity: Int!
) {
  addOrderItem(
    orderId: $orderId
    productId: $productId
    quantity: $quantity
  ) {
    order {
      id
      items { id quantity product { id name } }
    }
  }
}
```

### Change an item quantity

```graphql
mutation UpdateOrderItemQuantity($itemId: ID!, $quantity: Int!) {
  updateOrderItemQuantity(itemId: $itemId, quantity: $quantity) {
    order {
      id
      items { id quantity }
    }
  }
}
```

### Remove an item

```graphql
mutation RemoveOrderItem($orderId: ID!, $itemId: ID!) {
  removeOrderItem(orderId: $orderId, itemId: $itemId) {
    success
    order {
      id
      items { id quantity }
    }
  }
}
```

### Cancel an order

Customers can cancel their own orders while the status is `PENDING` or
`CONFIRMED`. Staff with change permission and superusers can also cancel orders.

```graphql
mutation CancelOrder($id: ID!) {
  cancelOrder(id: $id) {
    success
    order { id status }
  }
}
```

### Update order status

This mutation requires `shop.change_order`. Valid values are `PENDING`,
`CONFIRMED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, and `CANCELLED`.

```graphql
mutation UpdateOrderStatus($id: ID!, $status: OrderStatusEnum!) {
  updateOrderStatus(id: $id, status: "CONFIRMED") {
    order { id status }
  }
}
```

## REST API

The REST API is available under `/api/` and uses the same services, permissions,
JWT tokens, Redis revocation state, and catalog cache as GraphQL. REST resources
use ordinary integer IDs; Relay global IDs remain specific to GraphQL.

Send authenticated requests with:

```http
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

### Authentication endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup/` | Create a customer and return a token pair |
| `POST` | `/api/auth/login/` | Authenticate and return a token pair |
| `POST` | `/api/auth/refresh/` | Rotate a refresh token |
| `POST` | `/api/auth/logout/` | Revoke the refresh token and invalidate old tokens |
| `GET` | `/api/auth/me/` | Return the authenticated user |

Signup body:

```json
{
  "username": "customer",
  "email": "customer@example.com",
  "password": "a-strong-password"
}
```

Login uses `username` and `password`. Refresh and logout accept:

```json
{ "refresh_token": "REFRESH_TOKEN" }
```

### Catalog endpoints

| Method | Endpoint | Permission |
|---|---|---|
| `GET` | `/api/products/` | Public |
| `GET` | `/api/products/{id}/` | Public |
| `POST` | `/api/products/` | `shop.add_product` |
| `PUT/PATCH` | `/api/products/{id}/` | `shop.change_product` |
| `DELETE` | `/api/products/{id}/` | `shop.delete_product` |
| `GET` | `/api/categories/` | Public |
| `GET` | `/api/categories/{id}/` | Public |
| `POST` | `/api/categories/` | `shop.add_category` |
| `PUT/PATCH` | `/api/categories/{id}/` | `shop.change_category` |
| `DELETE` | `/api/categories/{id}/` | `shop.delete_category` |

Product lists support pagination, search, ordering, and filters, for example:

```text
/api/products/?page=1&search=keyboard&category_id=1&price__gte=10&price__lte=500&ordering=-price
```

Catalog GET responses use the same versioned Redis cache invalidated by product
and category model signals.

### Order endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/orders/` | List orders visible to the user |
| `GET` | `/api/orders/{id}/` | Retrieve a visible order |
| `POST` | `/api/orders/` | Create an order |
| `POST` | `/api/orders/{id}/items/` | Add an item or increase its quantity |
| `PATCH` | `/api/orders/{id}/items/{item_id}/` | Change item quantity |
| `DELETE` | `/api/orders/{id}/items/{item_id}/` | Remove an item |
| `POST` | `/api/orders/{id}/cancel/` | Cancel an allowed order |
| `PATCH` | `/api/orders/{id}/status/` | Staff status update |

Create-order body:

```json
{
  "items": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 3, "quantity": 1 }
  ]
}
```

Customers see and modify only their own eligible orders. Staff users with the
corresponding Django permissions and superusers can operate across users.


## Postman Collection

A Postman collection is included in the `postman/` directory.

Import:

- `GraphQL.postman_collection.json`
- `GraphQL Shop Local.postman_environment.json`

Select the `GraphQL Shop Local` environment and configure its customer and staff
credentials. The collection stores returned tokens and Relay IDs automatically.
For a complete run, execute folders in this order:

1. `Authentication` (use either signup or login for the customer)
2. `Catalog`
3. `Orders`
4. `Cleanup` (optional; deletes the created product and logs out)

The staff account must belong to the `Staff` group created by `setup_roles`.
