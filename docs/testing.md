# CI and unit tests

The initial suite uses Django's built-in test runner and Python's `unittest.mock`.
No additional testing dependencies are needed. It checks Relay ID validation,
order authorization, and the Python code that handles rate-limit decisions.

## Run locally

After activating a Python environment with the project's dependencies installed:

```bash
python -m pip install -r requirements.txt
python manage.py check --settings=config.test_settings
python manage.py test shop.tests --settings=config.test_settings --verbosity 2 --noinput
```

Run one module when working on a particular area:

```bash
python manage.py test shop.tests.test_order_permissions --settings=config.test_settings --verbosity 2
```

`--verbosity 2` prints each test name and result. `--noinput` prevents interactive
prompts. A failed assertion or unexpected exception makes the command exit with a
nonzero status, which fails its CI step.

## Workflow: `.github/workflows/ci.yml`

The workflow runs on every push and pull request. `workflow_dispatch` also enables
manual runs through GitHub's Actions interface once the workflow is on the default
branch. The single `unit-tests` job uses a hosted Ubuntu runner and has a ten-minute
timeout.

Its steps are:

1. **Check out source:** make the repository available to the runner. The workflow
   grants only `contents: read`, and checkout does not persist Git credentials.
2. **Set up Python:** select Python 3.12, matching the Dockerfile. Pip's download
   cache is keyed using `requirements.txt`, so changing dependency pins changes
   the cache key. Packages are still installed on every run.
3. **Install dependencies:** install the same pinned requirements as the app.
4. **Check Django configuration:** run `manage.py check` to catch configuration,
   model, and URL configuration problems reported by Django's system checks.
5. **Run unit tests:** discover and execute tests under `shop.tests`.

The job sets `DJANGO_SETTINGS_MODULE=config.test_settings`, so both Django commands
use the test configuration without repeating `--settings`. No service containers,
Infisical credentials, or GitHub secrets are required. The workflow validates code;
it does not deploy it. Repository branch protection must be configured separately
if passing CI should be required before merging.

## Settings: `config/test_settings.py`

The module imports the application settings so Django loads the real installed
apps, middleware, and URL configuration. It overrides the signing key with a fixed
test-only value, updates the JWT key to match, and disables debug mode.

It replaces PostgreSQL with in-memory SQLite and Django's Redis cache with the
in-process memory cache. These overrides avoid using the application's persistent
database or cache when test commands run. All current tests use `SimpleTestCase`,
which rejects database queries by default, so the runner skips database creation
entirely.

The cache override affects Django's cache API only. The rate limiter uses a direct
Redis client; its tests replace that client with a mock. Future tests of JWT token
storage or Celery publishing must also isolate those external dependencies.

Since this module imports the normal settings first, an explicitly configured
`*_FILE` secret path must still be readable. In a local shell, unset deployment
secret-file variables if they point to paths available only inside containers.

## Test package: `shop/tests/`

`__init__.py` makes this a Python package that Django's runner can discover. Each
`test_*.py` module groups related behavior, and methods beginning with `test_` are
individual test cases.

### Relay IDs: `test_id_service.py` — 3 tests

A valid Relay ID contains both a resource type and a database ID. The tests check
that a matching product ID returns its database ID as a string, that an order ID
cannot be used as a product ID, and that malformed or nonnumeric IDs are rejected.
The invalid-input test uses `subTest` so each input is identified independently
in failure output.

### Order permissions: `test_order_permissions.py` — 13 tests

These call the real authorization functions with lightweight order objects and a
mock user. `get_current_user` is patched where the permission module uses it,
isolating authorization rules from token parsing and Redis-backed token state.

The cases cover anonymous access, ownership, the required viewing permission,
modification of pending orders, cancellation of pending or confirmed orders,
rejection of later statuses, and staff/superuser access across customers.
The staff tests also check that group membership alone cannot grant viewing access.

Successful checks assert that the function returns the authorized user. Rejection
checks assert the expected error message, so an unrelated exception cannot silently
count as a correct denial. `addCleanup` removes patches even if a test fails.

### Rate limits: `test_rate_limit.py` — 9 tests

`RequestFactory` builds request objects without running an HTTP server. Four tests
check how client IPs are selected: forwarded headers are ignored by default,
trusted proxies use the first forwarded address, missing forwarded headers fall
back to the direct address, and a missing direct address becomes `unknown`.

Five more tests replace `_redis_client` and control the response of its `eval`
method. They verify allowed requests, rejected requests and retry delays, fallback
to the configured window, failure when Redis is unavailable, and a minimum retry
delay of one second. `override_settings` makes the relevant settings explicit and
restores them after each test.

## Scope and validation

This is an initial unit suite. It does not execute the Redis Lua script, database
transactions, HTTP endpoints, or Celery jobs. Those behaviors need integration
tests with suitable infrastructure. SQLite is not a substitute for validating
PostgreSQL-specific behavior.

Initial local validation passed all 25 tests and Django's system check using the
existing Python 3.14 environment. The GitHub workflow uses Python 3.12; its hosted
run and a fresh installation of dependencies must be verified by GitHub after the
changes are pushed.
