# GraphQL Shop

A Django and Graphene API for a small online shop. The project supports products,
categories, customer orders, role-based permissions, Relay global IDs, and JWT
authentication with refresh-token rotation and immediate logout invalidation.

## Technology stack

- Python 3.12
- Django 6.1
- Graphene and Graphene-Django
- PostgreSQL with Psycopg 3
- django-filter
- PyJWT

## Features

- Product and category management
- Product filtering by price and category
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

## Project structure

```text
config/
  settings.py                 Django and JWT settings
  urls.py                     Admin and GraphQL routes
shop/
  graphql/
    auth.py                   Authorization-header handling
    filters.py                Product filters
    inputs.py                 GraphQL input and enum definitions
    jwt.py                    Token creation, validation, rotation, revocation
    mutations.py              GraphQL mutations
    permissions.py            Authentication, permission, and ownership checks
    queries.py                GraphQL queries
    schema.py                 Root GraphQL schema
    types.py                  Graphene Django object types
  management/commands/
    seed.py                   Sample data command
    setup_roles.py            Customer and Staff role setup
  migrations/                 Database migrations
  models.py                   Shop and token-state models
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

### 3. Create the PostgreSQL database

The development settings currently expect:

| Setting | Value |
|---|---|
| Database | `graphql_shop` |
| User | `graphql_user` |
| Password | `graphql_password` |
| Host | `localhost` |
| Port | `5432` |



### 4. Apply migrations

```bash
python manage.py migrate
```

The token migrations are required for logout and refresh-token revocation:

- `0003_revokedrefreshtoken` creates the refresh-token blacklist.
- `0004_usertokenstate` creates the per-user token version.

### 5. Create roles and permissions

```bash
python manage.py setup_roles
```

This command creates Groups:

- `Customer`, with product/category viewing and order creation/viewing permissions.
- `Staff`, with all product, category, and order permissions.

Signup expects the `Customer` group to exist, so run this command before using the
`signup` mutation.

### 6. Seed data

```bash
python manage.py seed
```

The seed command creates sample users, categories, products,

### 7. Create an administrator

```bash
python manage.py createsuperuser
```

### 8. Run the development server

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

Logout performs two server-side actions:

1. It revokes the supplied refresh token by recording its `jti`.
2. It increments the user's `UserTokenState.version`.

Every access and refresh token contains the version active when it was issued.
Authentication compares that claim to the database. Once logout increments the
database version, all older tokens are rejected immediately. Logout therefore
currently signs the user out on every device.

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
  updateOrderStatus(id: $id, status: $status) {
    order { id status }
  }
}
```

Variables:

```json
{
  "id": "ORDER_GLOBAL_ID",
  "status": "CONFIRMED"
}
```


