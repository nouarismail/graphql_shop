# GraphQL Shop
A Django and Graphene API for a small online shop. The project supports products,

categories, customer orders, role-based permissions, Relay global IDs, and JWT

authentication with refresh-token rotation and immediate logout invalidation.

## Technology stack
\- Python 3.12

\- Django 6.1

\- Graphene and Graphene-Django

\- Django REST Framework

\- PostgreSQL with Psycopg 3

\- django-filter

\- PyJWT

\- Redis

## Features
\- Product and category management

\- Product filtering by price and category

\- Redis caching for product and category queries

\- Customer signup and login

\- Short-lived access tokens and rotating refresh tokens

\- Server-side refresh-token revocation

\- Immediate logout through per-user token versions

\- Customer and staff roles backed by Django permissions

\- Order creation with multiple items

\- Adding, removing, and changing order items

\- Order cancellation and status updates

\- Customer-specific order visibility

\- Relay global IDs for products, users, orders, and order items

\- REST endpoints mirroring the GraphQL authentication, catalog, and order workflows

## Project structure
\`\`\`text

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

  rest\_api/

    authentication.py        Bearer JWT authentication for DRF

    permissions.py           Catalog and order authorization policies

    serializers.py           REST request and response schemas

    urls.py                  REST router and authentication routes

    views.py                 Authentication, catalog, and order endpoints

  management/commands/

    seed.py                   Sample data command

    setup\_roles.py            Customer and Staff role setup

  migrations/                 Database migrations

  services/

    auth\_service.py           Signup, login, refresh, and logout workflows

    catalog\_cache.py          Catalog cache keys, reads, and invalidation

    category\_service.py       Category write operations

    id\_service.py             Relay global ID validation

    order\_service.py          Order and order-item write operations

    product\_service.py        Product read and write operations

    token\_store.py            Redis token revocation and version storage

  signals.py                  Catalog invalidation after model writes

  models.py                   Shop models and legacy token-state models

compose.yaml                  Local persistent Redis service

requirements.txt              Python dependencies

manage.py                     Django command-line entry point

\`\`\`

## Secrets with Docker Compose

This project uses Docker Compose Secrets for local and single-host deployments.
Sensitive values live in ignored files under `.secrets/`; Compose mounts each one
read-only at `/run/secrets/<name>` and grants it only to explicitly listed services.
They no longer appear as literal values in `compose.yaml` or `.env`.

### 1. Initialize the secret files

Run this once before starting a fresh stack:

```bash
chmod +x docker/init-secrets.sh
./docker/init-secrets.sh
```

The script uses `umask 077` and OpenSSL random bytes. It never overwrites an
existing secret, which prevents an accidental credential rotation from making an
existing PostgreSQL or RabbitMQ volume inaccessible. It protects the host secrets
directory with mode `0700`; its files are `0644` because local Compose preserves
source permissions and the Django image runs as a non-root user. Other host users
cannot traverse the private directory. `.secrets/` is ignored by Git, while
`.secrets.example/` documents the required filenames without real values.

### 2. Validate secret declarations

```bash
docker compose config --quiet
```

The top-level `secrets` section maps the local files. Each service-level `secrets`
list is an access grant. PostgreSQL receives `db_password`, RabbitMQ receives
`rabbitmq_password`, and the Django processes receive the credentials they need to
connect to both services.

### 3. Start or recreate the stack

```bash
docker compose up -d --build
docker compose ps
```

PostgreSQL reads `POSTGRES_PASSWORD_FILE`. RabbitMQ's startup command reads its
mounted password and exports it only inside that container. Django's
`env_or_secret` helper reads each `*_FILE` path; it constructs the AMQP URL at
runtime and URL-encodes credentials safely.

### 4. Verify mounts without printing secret values

```bash
docker compose exec web sh -c \
  'test -s /run/secrets/django_secret_key && test -s /run/secrets/db_password && test -s /run/secrets/rabbitmq_password'
docker compose logs --tail=50 web db rabbitmq celery-worker
```

Do not use `cat /run/secrets/...` in logs or screenshots. Anyone with sufficient
access to the Docker host can still read local Compose secret source files, so
protect the host and backups. Compose Secrets improve delivery and service-level
access control; they are not an encrypted cloud secret manager.

### 5. Rotate credentials deliberately

Changing a secret file alone does not change a password already stored inside an
initialized PostgreSQL or RabbitMQ data volume. Rotate the credential in the
service first, update the matching `.secrets` file, and then recreate its clients.
Keep the Django signing key stable unless intentionally invalidating every JWT and
signed value. Use a managed secret store such as a cloud provider's secret manager
for multi-host production deployments, audit logging, and automatic rotation.

## Run the complete project with Docker
The Docker setup runs seven services:

\- \`nginx\`: the public HTTP entry point, published on \`WEB_PORT\` (port \`8000\` by default).

\- \`web\`: the private Django API served by Gunicorn on the Compose network at \`web:8000\`.

\- \`db\`: PostgreSQL 16, also published on host port \`5432\` for local tools.

\- \`redis\`: persistent Redis 7 storage for JWT revocation and catalog caching,

  also published on host port \`6379\` for local tools.

\- \`rabbitmq\`: Celery's message broker; its local management UI is published on

  host port \`15672\`.

\- \`celery-worker\`: executes background tasks.

\- \`celery-beat\`: schedules recurring background tasks.

If you have Docker installed, copy the example environment file and start the stack:

\`\`\`bash

cp .env.example .env

docker compose up --build

\`\`\`

On first startup, the web entrypoint waits for healthy PostgreSQL and Redis

containers, applies Django migrations, creates the \`Customer\` and \`Staff\` roles,

collects static files, and then starts Gunicorn. Nginx waits for Gunicorn's health

check before accepting traffic. Open:

\- GraphQL/GraphiQL: \<http\://localhost:8000/graphql/>

\- REST API: \<http\://localhost:8000/api/>

\- Django admin: \<http\://localhost:8000/admin/>

Run the optional sample-data command after the services are up:

\`\`\`bash

docker compose exec web python manage.py seed

\`\`\`

Create an administrator interactively:

\`\`\`bash

docker compose exec web python manage.py createsuperuser

\`\`\`

Useful lifecycle and diagnostic commands:

\`\`\`bash

docker compose up -d --build       # start in the background

docker compose ps                  # show service and health state

docker compose logs -f web         # follow application logs

docker compose logs -f nginx       # follow reverse-proxy access/error logs

docker compose exec web python manage.py check

docker compose down                # stop containers; keep database/cache data

docker compose down --volumes      # stop and permanently remove stored data

\`\`\`

Configuration comes from \`.env\`, which Compose loads automatically. The checked-in

\`.env.example\` documents every supported Compose option; \`.env\` itself is ignored

so credentials are not committed. Replace \`DJANGO\_SECRET\_KEY\` and \`DB\_PASSWORD\`

for any non-local deployment, and add its DNS names to \`DJANGO\_ALLOWED\_HOSTS\`.

\`WEB\_PORT\` changes the Nginx host-side port without changing its container port.

PostgreSQL data lives in the \`postgres-data\` named volume and Redis AOF data in

\`redis-data\`, so recreating a container does not erase state. Django reaches both

services by their Compose names (`db` and `redis`); their published ports are for

local development tools and can be removed for a production deployment.

The `web` service bind-mounts the source tree at `/app` and runs Gunicorn with

`--reload`. Python source edits are therefore available inside the container

immediately and automatically restart the web workers. Rebuild the image only

when dependencies, the Dockerfile, or entrypoint change. Collected static files

use a separate `staticfiles` volume so the bind mount remains development-friendly.

### Nginx reverse proxy

Only Nginx publishes an application port to the host. Gunicorn uses `expose`

instead of `ports`, so it remains reachable by other Compose services but cannot

be bypassed from the host. Nginx forwards `/api/`, `/graphql/`, `/admin/`, and all

other dynamic paths to `web:8000`. Requests to `/static/` are read directly from

the shared, read-only `staticfiles` volume populated by Django's `collectstatic`.

The proxy preserves the original `Host`, scheme, and client address headers. It

sets `X-Forwarded-For` from Nginx's direct client rather than trusting a value

supplied by the caller. `ORDER_RATE_LIMIT_TRUST_PROXY=true` lets Django's existing

order limiter use this address safely. The 120-second upstream timeout allows

local Ollama requests to finish, while the 20 MB body limit accommodates catalog

CSV imports. `/nginx-health` is an internal diagnostic endpoint used by Compose.

The request flow is:

```text
Client -> localhost:WEB_PORT -> Nginx -> web:8000 -> Django/Gunicorn
                                  |
                                  +-> /static/ from the staticfiles volume
```

After adding or changing the Nginx configuration, recreate the affected services:

```bash
docker compose up -d --build --force-recreate web nginx
docker compose ps
curl http://localhost:${WEB_PORT:-8000}/nginx-health
```

Use `docker compose exec web ...` for management commands because Gunicorn remains

the Django container even though Nginx is now the public HTTP endpoint.

\`RUN\_MIGRATIONS=false\` or \`SETUP\_ROLES=false\` can disable those automatic startup

steps when a deployment platform runs them as separate release tasks.

## Automatic cancellation of unpaid orders with Celery

In the current domain model there is no separate payment table or payment-status
field. Consequently, `PENDING` is treated as "created but not yet paid/confirmed."
An order that moves to `CONFIRMED`, `PROCESSING`, or another status is no longer
eligible for automatic cancellation.

Two additional containers run the background workflow:

- `celery-beat` is the clock. Every `ORDER_CANCELLATION_SCAN_SECONDS`, it sends the
  named `shop.tasks.cancel_expired_pending_orders` task to RabbitMQ.
- `celery-worker` consumes that message and executes the database update.

RabbitMQ is Celery's broker. Redis database 3 remains its result backend, separate
from JWT state in database 0 and catalog cache in database 1. PostgreSQL remains
the source of truth for order state.

When an order is created, `create_order` registers the confirmation task with
`transaction.on_commit`. RabbitMQ receives it only after the database transaction
succeeds. The worker then loads the order and sends an itemized confirmation with
Django's console email backend. This simulates delivery by printing the message in
the worker logs:

```bash
docker compose logs -f celery-worker
```

The defaults provide a 30-minute payment window and a scan once per minute:

```dotenv
ORDER_PENDING_TIMEOUT_SECONDS=1800
ORDER_CANCELLATION_SCAN_SECONDS=60
CELERY_WORKER_CONCURRENCY=2
```

Cancellation therefore occurs after roughly 30–31 minutes, not necessarily at the
exact 30-minute boundary. A shorter scan interval gives tighter timing at the cost
of more database queries. Apply configuration changes with:

```bash
docker compose up -d --build --force-recreate celery-worker celery-beat
```

Inspect and test the workflow:

```bash
docker compose logs -f celery-worker celery-beat
docker compose exec web python manage.py shell -c \
  "from shop.tasks import cancel_expired_pending_orders; print(cancel_expired_pending_orders.delay().get(timeout=10))"
```

### Why each Celery code line exists

`config/celery.py` creates the Celery application. `import os` allows setting
`DJANGO_SETTINGS_MODULE`; `setdefault` points worker and beat at `config.settings`
without overwriting an explicit alternative. `Celery("config")` creates the app.
`config_from_object(..., namespace="CELERY")` loads only settings beginning with
`CELERY_`, preventing name collisions. `autodiscover_tasks()` searches installed
Django apps for `tasks.py` modules.

`config/__init__.py` imports that app whenever the `config` package loads. Exporting
it through `__all__` identifies the public object and lets `celery -A config` find
the configured application.

In `shop/tasks.py`, `logging` reports useful work; `timedelta` calculates the expiry
boundary; `shared_task` registers the function; Django `settings` supplies the
configurable timeout; and timezone-aware `timezone.now()` matches `USE_TZ=True`.
Importing `Order` supplies the database model.

The decorator turns the function into a task, while its explicit name keeps the
beat schedule stable. `now` is captured once so all changed rows get one timestamp.
`cutoff` subtracts the allowed payment window. The query requires both a `PENDING`
status and `created_at` at or before the cutoff, then bulk-updates matching rows to
`CANCELLED`. It sets `updated_at` explicitly because bulk `update()` does not run
the field's `auto_now`. The affected-row count is logged and returned for
observability and testing.

The status condition and update execute as one SQL statement. There is no gap
between reading and writing in Python. If another request has already moved an
order away from `PENDING`, PostgreSQL excludes it, so the task does not overwrite
the newer state.

In `settings.py`, the broker URL selects RabbitMQ and the result URL selects an
isolated Redis database; task-start tracking aids inspection; the time limit bounds
stuck work; startup retry handles broker initialization; the order settings control
age and cadence; and `CELERY_BEAT_SCHEDULE` maps the cadence to the stable task name.

In `compose.yaml`, YAML anchors keep common application configuration identical for
web, worker, and beat. The Celery services build the same image as `web`, replacing
only the command. Their preparation flags are disabled because only `web` should
run migrations, create roles, and collect static files. Health dependencies keep
all application processes behind ready PostgreSQL, Redis, and RabbitMQ services.
The Docker image switches from root to the unprivileged `app` user before starting
any service. Worker concurrency defaults to two processes because this task is
small; `CELERY_WORKER_CONCURRENCY` allows deliberate scaling.

If a `.env` value contains `$`, single-quote the complete value—for example,
`DJANGO_SECRET_KEY='abc$def'`. Otherwise Compose treats `$def` as an environment
reference and silently changes the value.

## Order-creation rate limiting

Order creation through both REST and GraphQL is limited to three accepted requests
in any rolling hour for each client IP address and independently for each
authenticated user. A request proceeds only when both identities are below their
limits. This means changing accounts does not bypass an IP limit, and changing IPs
does not bypass a user limit.

The defaults are configurable in `.env`:

```dotenv
ORDER_RATE_LIMIT_REQUESTS=3
ORDER_RATE_LIMIT_WINDOW_SECONDS=3600
ORDER_RATE_LIMIT_TRUST_PROXY=false
```

Redis database 4 stores this state, isolated from authentication (0), cache (1),
Celery broker (2), and Celery results (3). No database migration is required.

`shop/services/rate_limit.py` contains the shared implementation. `_client_ip`
uses Django's `REMOTE_ADDR` by default. It reads the first `X-Forwarded-For` value
only when `ORDER_RATE_LIMIT_TRUST_PROXY=true`; enable that option only when a
trusted reverse proxy replaces the header, because clients can otherwise forge
it. IP addresses are SHA-256 hashed before becoming Redis keys. User keys contain
the stable database user ID.

The Lua script executes entirely inside Redis as one atomic operation. It reads
Redis server time, removes timestamps older than the configured rolling window,
counts the remaining IP and user entries, and rejects when either count is already
at the limit. For an accepted request it adds the same unique request identifier
to both sorted sets and refreshes their expiration. Atomic execution prevents two
simultaneous Gunicorn workers from both incorrectly accepting a fourth request.
The oldest retained timestamp determines the exact retry delay.

`OrderViewSet.create` invokes the limiter before REST payload validation. An
exceeded limit becomes DRF's `Throttled` exception, producing HTTP `429 Too Many
Requests` and a `Retry-After` header. A Redis outage produces HTTP 500 rather than
silently disabling protection. `CreateOrder.mutate` invokes the same limiter after
GraphQL authentication/permission checking and before the database transaction;
GraphQL returns the limiter message in its `errors` array.

Only admitted creation attempts consume quota. Failed authentication and requests
blocked by the limiter do not. REST requests admitted by the limiter but later
rejected by payload validation do consume quota, because they reached the protected
order-creation endpoint. GraphQL argument-shape errors are rejected by GraphQL
before its mutation resolver runs and therefore do not consume quota.

After changing limiter settings or code, rebuild and recreate the application:

```bash
docker compose up -d --build --force-recreate web
```

If multiple application deployments must share limits, point all of them at the
same `RATE_LIMIT_REDIS_URL` and retain the same key prefix.

## Local setup
### 1. Create and activate a virtual environment
\`\`\`bash

python3 -m venv venv

source venv/bin/activate

\`\`\`

On Windows PowerShell:

\`\`\`powershell

python -m venv venv

venv\Scripts\Activate.ps1

\`\`\`

### 2. Install dependencies
\`\`\`bash

pip install -r requirements.txt

\`\`\`

### 3. Start Redis
Refresh-token rotation and logout require Redis. The included service enables AOF

persistence and disables key eviction so logout state is not silently discarded:

\`\`\`bash

docker compose up -d redis

docker compose ps

\`\`\`

The application uses \`redis\://127.0.0.1:6379/0\` by default. These environment

variables can override the connection:

\| Variable | Default | Purpose |

\|---|---|---|

\| \`REDIS\_URL\` | \`redis\://127.0.0.1:6379/0\` | Redis connection URL and database |

\| \`REDIS\_TOKEN\_KEY\_PREFIX\` | \`graphql-shop\:tokens\` | Namespace for authentication keys |

\| \`REDIS\_SOCKET\_TIMEOUT\` | \`2\` | Connect/read timeout in seconds |

\| \`REDIS\_CACHE\_URL\` | \`redis\://127.0.0.1:6379/1\` | Product/category cache database |

\| \`CATALOG\_CACHE\_TIMEOUT\` | \`300\` | Catalog entry lifetime in seconds |

Redis is security-critical for this implementation. If it is unavailable, token

creation and authentication fail closed instead of accepting a token whose

revocation state cannot be checked.

Catalog caching is isolated in Redis database \`1\`. Product lists are cached per

filter/order combination, individual products by ID, and categories with their

prefetched products. Product or category writes increment a catalog version key,

making older entries immediately unreachable. Unlike token storage, catalog

caching fails open: if Redis is unavailable, queries use PostgreSQL and writes

continue normally.

### 4. Create the PostgreSQL database
The development settings currently expect:

\| Setting | Value |

\|---|---|

\| Database | \`graphql\_shop\` |

\| User | \`graphql\_user\` |

\| Password | \`graphql\_password\` |

\| Host | \`localhost\` |

\| Port | \`5432\` |





### 5. Apply migrations
\`\`\`bash

python manage.py migrate

\`\`\`

Migrations \`0003\` and \`0004\` created the original database token-state tables.

They remain in migration history for compatibility, but current authentication

uses Redis and no longer reads or writes those tables.

### 6. Create roles and permissions
\`\`\`bash

python manage.py setup\_roles

\`\`\`

This creates two Django groups:

\- \`Customer\`, with product/category viewing and order creation/viewing permissions.

\- \`Staff\`, with all product, category, and order permissions.

Signup expects the \`Customer\` group to exist, so run this command before using the

\`signup\` mutation.

### 7. Seed data
\`\`\`bash

python manage.py seed

\`\`\`

The seed command creates sample users, categories, products,

### 8. Create an administrator
\`\`\`bash

python manage.py createsuperuser

\`\`\`

### 9. Run the development server
\`\`\`bash

python manage.py runserver

\`\`\`

Open GraphiQL at \<http\://127.0.0.1:8000/graphql/>. 

Django Admin is available at\<http\://127.0.0.1:8000/admin/>.

## Authentication
Authenticated operations require an access token in the HTTP header:

\`\`\`http

Authorization: Bearer ACCESS\_TOKEN

\`\`\`



### Signup
The \`Customer\` role must already exist.

\`\`\`graphql

mutation Signup {

  signup(

    username: "customer"

    email: "customer\@example.com"

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

\`\`\`

### Login
\`\`\`graphql

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

\`\`\`

### Current user
Send the access token in the \`Authorization\` header.

\`\`\`graphql

query Me {

  me {

    id

    username

    email

  }

}

\`\`\`

### Refresh the token pair
\`\`\`graphql

mutation RefreshToken($token: String!) {

  refreshToken(refreshToken: "REFRESH\_TOKEN") {

    accessToken

    refreshToken

    user {

      id

      username

    }

  }

}

\`\`\`

### Logout
\`\`\`graphql

mutation Logout($token: String!) {

  logout(refreshToken: $token) {

    success

  }

}

\`\`\`

On logout, the server does two things in Redis:

1\. It stores \`graphql-shop\:tokens\:revoked:\<jti>\` with a TTL equal to the token's

   remaining lifetime.

2\. It increments \`graphql-shop\:tokens\:version:\<user\_id>\`.

Every access and refresh token contains the version active when it was issued.

Authentication compares that claim to Redis. Once logout increments the Redis

version, all older access and refresh tokens are rejected immediately. Logout

therefore signs the user out on every device.

Refresh rotation writes the revocation key with Redis \`SET NX EX\`. \`NX\` means

only the first concurrent attempt can consume a refresh token; \`EX\` removes the

key automatically when the JWT would have expired, so the blacklist does not

grow indefinitely.

After a successful logout, the client should delete its stored access and refresh

tokens.





## Queries
### List products
\`\`\`graphql

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

\`\`\`

Available filters include \`minPrice\`, \`maxPrice\`, and \`categoryId\`.

### Get one product
\`\`\`graphql

query Product($id: ID!) {

  product(id: $id) {

    id

    name

    description

    price

    priceWithTax

  }

}

\`\`\`

### List categories
\`\`\`graphql

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

\`\`\`

### List visible orders
This query requires authentication. Customers receive only their own orders.

Staff members with \`shop.view\_order\` and superusers receive all orders.

\`\`\`graphql

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

\`\`\`

### Get one order
Customers can retrieve only an order they own.

\`\`\`graphql

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

\`\`\`

## Product and category mutations
These operations require the corresponding Django permissions.

### Create a product
\`\`\`graphql

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

\`\`\`

### Update a product
\`\`\`graphql

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

\`\`\`

### Delete a product
\`\`\`graphql

mutation DeleteProduct($id: ID!) {

  deleteProduct(id: $id) {

    success

  }

}

\`\`\`

Category mutation classes exist internally, but they are not currently registered

on the root \`Mutation\` type and therefore are not exposed by the GraphQL API.

## Order mutations
### Create an order
Every \`productId\` must be a \`ProductType\` global ID. The operation is atomic: if

one item is invalid, the complete order creation is rolled back.

\`\`\`graphql

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

\`\`\`

Variables:

\`\`\`json

{

  "items": [

    { "productId": "PRODUCT\_GLOBAL\_ID", "quantity": 2 },

    { "productId": "ANOTHER\_PRODUCT\_GLOBAL\_ID", "quantity": 1 }

  ]

}

\`\`\`

### Add an item
Customers can modify only their own \`PENDING\` orders. Adding a product already in

the order increases its existing quantity.

\`\`\`graphql

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

\`\`\`

### Change an item quantity
\`\`\`graphql

mutation UpdateOrderItemQuantity($itemId: ID!, $quantity: Int!) {

  updateOrderItemQuantity(itemId: $itemId, quantity: $quantity) {

    order {

      id

      items { id quantity }

    }

  }

}

\`\`\`

### Remove an item
\`\`\`graphql

mutation RemoveOrderItem($orderId: ID!, $itemId: ID!) {

  removeOrderItem(orderId: $orderId, itemId: $itemId) {

    success

    order {

      id

      items { id quantity }

    }

  }

}

\`\`\`

### Cancel an order
Customers can cancel their own orders while the status is \`PENDING\` or

\`CONFIRMED\`. Staff with change permission and superusers can also cancel orders.

\`\`\`graphql

mutation CancelOrder($id: ID!) {

  cancelOrder(id: $id) {

    success

    order { id status }

  }

}

\`\`\`

### Update order status
This mutation requires \`shop.change\_order\`. Valid values are \`PENDING\`,

\`CONFIRMED\`, \`PROCESSING\`, \`SHIPPED\`, \`DELIVERED\`, and \`CANCELLED\`.

\`\`\`graphql

mutation UpdateOrderStatus($id: ID!, $status: OrderStatusEnum!) {

  updateOrderStatus(id: $id, status: "CONFIRMED") {

    order { id status }

  }

}

\`\`\`

## REST API
The REST API is available under \`/api/\` and uses the same services, permissions,

JWT tokens, Redis revocation state, and catalog cache as GraphQL. REST resources

use ordinary integer IDs; Relay global IDs remain specific to GraphQL.

Send authenticated requests with:

\`\`\`http

Authorization: Bearer ACCESS\_TOKEN

Content-Type: application/json

\`\`\`

### Authentication endpoints
\| Method | Endpoint | Purpose |

\|---|---|---|

\| \`POST\` | \`/api/auth/signup/\` | Create a customer and return a token pair |

\| \`POST\` | \`/api/auth/login/\` | Authenticate and return a token pair |

\| \`POST\` | \`/api/auth/refresh/\` | Rotate a refresh token |

\| \`POST\` | \`/api/auth/logout/\` | Revoke the refresh token and invalidate old tokens |

\| \`GET\` | \`/api/auth/me/\` | Return the authenticated user |

Signup body:

\`\`\`json

{

  "username": "customer",

  "email": "customer\@example.com",

  "password": "password"

}

\`\`\`

Login uses \`username\` and \`password\`. Refresh and logout accept:

\`\`\`json

{ "refresh\_token": "REFRESH\_TOKEN" }

\`\`\`

### Catalog endpoints
\| Method | Endpoint | Permission |

\|---|---|---|

\| \`GET\` | \`/api/products/\` | Public |

\| \`GET\` | \`/api/products/{id}/\` | Public |

\| \`POST\` | \`/api/products/\` | \`shop.add\_product\` |

\| \`PUT/PATCH\` | \`/api/products/{id}/\` | \`shop.change\_product\` |

\| \`DELETE\` | \`/api/products/{id}/\` | \`shop.delete\_product\` |

\| \`POST\` | \`/api/products/import/\` | Staff with \`shop.add\_product\` and \`shop.change\_product\` |

\| \`GET\` | \`/api/products/export/\` | Staff with \`shop.view\_product\` |

\| \`GET\` | \`/api/categories/\` | Public |

\| \`GET\` | \`/api/categories/{id}/\` | Public |

\| \`POST\` | \`/api/categories/\` | \`shop.add\_category\` |

\| \`PUT/PATCH\` | \`/api/categories/{id}/\` | \`shop.change\_category\` |

\| \`DELETE\` | \`/api/categories/{id}/\` | \`shop.delete\_category\` |

Product lists support pagination, search, ordering, and filters, for example:

\`\`\`text

/api/products/?page=1&search=keyboard&category\_id=1&price\_\_gte=10&price\_\_lte=500&ordering=-price

\`\`\`

Catalog GET responses use the same versioned Redis cache invalidated by product

and category model signals.

Product CSV imports use a multipart \`file\` field. Required columns are \`name\`,

\`price\`, and \`category\_id\`; optional columns are \`id\` and \`description\`.

A blank \`id\` creates a product, while an existing product ID updates it. The

complete file is validated before an atomic import, and validation errors include

CSV row numbers. Product exports use the same columns and add \`category\_name\`.

### Order endpoints
\| Method | Endpoint | Purpose |

\|---|---|---|

\| \`GET\` | \`/api/orders/\` | List orders visible to the user |

\| \`GET\` | \`/api/orders/{id}/\` | Retrieve a visible order |

\| \`POST\` | \`/api/orders/\` | Create an order |

\| \`POST\` | \`/api/orders/{id}/items/\` | Add an item or increase its quantity |

\| \`PATCH\` | \`/api/orders/{id}/items/{item\_id}/\` | Change item quantity |

\| \`DELETE\` | \`/api/orders/{id}/items/{item\_id}/\` | Remove an item |

\| \`POST\` | \`/api/orders/{id}/cancel/\` | Cancel an allowed order |

\| \`PATCH\` | \`/api/orders/{id}/status/\` | Staff status update |

\| \`GET\` | \`/api/orders/export/\` | Staff with \`shop.view\_order\`; one row per order item |

Create-order body:

\`\`\`json

{

  "items": [

    { "product\_id": 1, "quantity": 2 },

    { "product\_id": 3, "quantity": 1 }

  ]

}

\`\`\`

Customers see and modify only their own eligible orders. Staff users with the

corresponding Django permissions and superusers can operate across users.



## Postman Collection
GraphQL and REST Postman collections are included in the \`postman/\` directory.

For the REST API, import:

\- \`REST API.postman\_collection.json\`

\- \`GraphQL Shop REST Local.postman\_environment.json\`

Select the \`GraphQL Shop REST Local\` environment, configure the customer and

staff credentials, and run the numbered folders in order. Test scripts capture

access/refresh tokens and category, product, order, and order-item integer IDs.

The signup request is optional and tolerates an existing username during a

collection run. The final cleanup folder deletes the created product and logs out.

For GraphQL, import:

\- \`GraphQL.postman\_collection.json\`

\- \`GraphQL Shop Local.postman\_environment.json\`

Select the \`GraphQL Shop Local\` environment and configure its customer and staff

credentials. The collection stores returned tokens and Relay IDs automatically.

For a complete run, execute folders in this order:

1\. \`Authentication\` (use either signup or login for the customer)

2\. \`Catalog\`

3\. \`Orders\`

4\. \`Cleanup\` (optional; deletes the created product and logs out)

The staff account must belong to the \`Staff\` group created by \`setup\_roles\`.
