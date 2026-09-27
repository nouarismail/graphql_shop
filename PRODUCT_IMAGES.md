# Product images with MinIO

## Request flow

1. An authenticated user with `shop.add_product` or `shop.change_product` sends a multipart REST request containing an `image` file.
2. DRF checks the file with Pillow. Only JPEG, PNG, and WebP are accepted, up to 5 MiB. Invalid uploads return HTTP 400 before the product service runs.
3. The product service saves the file through Django's default storage backend, `django-storages` S3 storage. MinIO implements the S3 API.
4. MinIO stores the bytes in the `product-images` bucket under `products/<uuid>.<extension>`. PostgreSQL stores only that object key in `Product.image`.
5. REST and GraphQL return a public URL. The browser fetches the bytes directly from MinIO on port 9000.

## Every code/configuration change

- `requirements.txt`: adds `django-storages[s3]` (including the boto3 S3 client) and Pillow for image decoding/validation.
- `shop/models.py`: adds an optional `ImageField`. The `product_image_path` callable generates a fresh UUID instead of using the original filename, preventing two uploads with the same filename from overwriting each other.
- `shop/migrations/0006_product_image.py`: adds the image column. Existing products have an empty image value; they do not require placeholder files.
- `config/settings.py`: changes the default file storage to S3-compatible MinIO storage. Static files still use WhiteNoise. `endpoint_url` is the server-side address; `custom_domain` and `url_protocol` generate browser URLs. Path-style addressing and Signature V4 support MinIO. Public image URLs do not expire, so catalog caches do not retain expired signatures. The public origin is validated at startup.
- `.env.example`: documents MinIO credentials, bucket name, and internal/public endpoints. Django also supports `MINIO_ACCESS_KEY_FILE` and `MINIO_SECRET_KEY_FILE` through its existing secret-file helper when configuring a deployment outside this local Compose setup.
- `compose.yaml`: adds persistent MinIO storage, the API on port 9000, and a console bound to localhost on port 9001. A separate `minio-init` container waits for MinIO, creates the bucket idempotently, and allows anonymous downloads under `products/`. Application services wait for initialization to finish. Uploads still require credentials.
- `shop/rest_api/serializers.py`: accepts multipart image uploads, validates the size and actual decoded format, and returns the image URL or `null`.
- `shop/rest_api/views.py`: forwards uploaded/cleared images during updates, distinguishing an omitted field from an explicit clear.
- `shop/services/product_service.py`: saves optional uploads on create/update, preserving existing images for callers that do not supply an image (including existing GraphQL mutations and CSV updates). Also fixes the existing create path to accept an omitted optional description, which multipart image uploads exposed.
- `shop/graphql/types.py`: exposes the nullable `image` URL. Binary uploads use REST; the GraphQL endpoint continues accepting its existing JSON requests and has no multipart upload scalar.
- `shop/audit.py`: includes the image object key in product change events and converts `FieldFile` values to JSON-safe strings. It records neither image bytes nor credentials.
- `config/test_settings.py`: uses Django's in-memory storage so unit tests require neither MinIO nor external credentials.
- `shop/tests/test_product_images.py`: covers uploading, replacement, clearing, preservation, invalid/oversized uploads, permissions, GraphQL URL output, audit changes, cache refresh, and separation of the internal S3 address from the public URL.
- `README.md`: links this guide.

## Start the Docker setup

Compose pulls the pinned server and client images from MinIO's `quay.io/minio` repositories. The previous Docker Hub reference returned `pull access denied` for `minio/mc`; both Quay references successfully began downloading. MinIO's [client build script](https://github.com/minio/mc/blob/master/docker-buildx.sh) documents publishing to this registry. Registry login is not required for these public pulls.

Merge the MinIO variables from `.env.example` into your existing `.env`; do not replace your existing database or application settings. Compose reads `.env` automatically. Direct `manage.py` commands do not, so export the variables when running Django on the host.

```dotenv
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=product-images
MINIO_PUBLIC_URL=http://localhost:9000
```

These are local development credentials. For a remote deployment, set strong credentials, use an HTTPS public origin reachable by clients, and provision a bucket-scoped application account instead of sharing the MinIO root account. This Compose configuration passes MinIO credentials through environment variables; it does not extend the existing Infisical synchronization script.

```bash
docker compose up -d minio minio-init
docker compose logs minio-init
docker compose up -d --build web celery-worker celery-beat nginx
```

The existing web entrypoint applies migrations when `RUN_MIGRATIONS=true` (the default). If disabled, run:

```bash
docker compose run --rm web python manage.py migrate
```

The console is at `http://localhost:9001`; log in with the configured MinIO credentials. Image URLs use port **9000**, not 9001. For access from another computer, `MINIO_PUBLIC_URL` must use your server's hostname instead of `localhost`. Django containers always upload through `http://minio:9000` in this Compose setup.

## Upload and retrieve images

Create a product (replace the access token, category ID, and local file path):

```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'name=Camera' \
  -F 'price=149.99' \
  -F 'category_id=1' \
  -F 'image=@/path/to/camera.png'
```

Replace the image on product 1:

```bash
curl -X PATCH http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'image=@/path/to/replacement.webp'
```

Do not manually set `Content-Type` on these multipart requests: curl supplies the required boundary. Existing product permission checks apply. Ordinary customers and anonymous users cannot upload.

REST includes an `image` value resembling:

```json
{"image": "http://localhost:9000/product-images/products/0123456789abcdef0123456789abcdef.png"}
```

Query the same URL with GraphQL:

```graphql
query {
  products {
    edges {
      node { id name image }
    }
  }
}
```

GraphQL clients can create a product through their existing mutation, upload using REST with the product's integer database ID, then query `image` through GraphQL. GraphQL Relay IDs are base64-encoded `ProductType:<database-id>`; REST endpoints take the integer ID.

Remove the reference:

```bash
curl -X PATCH http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"image": null}'
```

Omitting `image` preserves the current value. Products without an image return `null`. Existing product save signals invalidate the catalog cache after updates.

## Object lifetime and verification

Old files remain in MinIO after replacement, clearing, or product deletion. A storage upload cannot participate in a database transaction: if a database save fails after uploading, an unreferenced object may remain too. A separate cleanup process should compare retained object keys with database references according to your retention policy. Clearing a product's field is not a revocation of the old public URL. Do not use this bucket for private images.

Run local checks after installing requirements:

```bash
venv/bin/python manage.py check --settings=config.test_settings
venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
venv/bin/python manage.py test shop.tests --settings=config.test_settings
```

For a live integration check, upload through REST, open the returned URL without authorization, then verify the object in the MinIO console. Anonymous writes should be rejected. The named `minio-data` volume preserves objects across container restarts; deleting that volume deletes the stored images.

Implementation verification: all 44 tests in `shop.tests` passed, including the four image test cases. Django system checks, migration consistency, Compose configuration validation, and `git diff --check` passed. Live MinIO verification was blocked by a Docker Hub TLS timeout; the application image build was stopped after its base-image download stalled. The migration has been exercised in the test database but has not been applied to the deployed database.

Storage settings follow the [django-storages S3 documentation](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html). Public downloads are configured with [MinIO's anonymous access commands](https://docs.min.io/aistor/reference/cli/mc-anonymous/).
