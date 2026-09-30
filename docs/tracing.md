# Request tracing

Tracing is optional and disabled by default. The path is:

```text
Django / Celery → OTLP over HTTP → OpenTelemetry Collector → Tempo → Grafana
```

Django creates HTTP spans for REST and GraphQL. Psycopg, Redis, HTTPX (including
Ollama calls), and Celery create child spans. GraphQL adds operation names/types
and marks execution errors even when HTTP returns 200. Order creation and AI
filter extraction have their own application spans. Celery propagates trace
context through task message headers, connecting publishing and execution.
Nginx itself is not instrumented; request traces begin at Django. MinIO/S3 and
SMTP calls do not currently have dedicated instrumentation.

## Enable

Use the existing [Infisical setup](../README.md) to add
`GRAFANA_ADMIN_PASSWORD`, then synchronize it for Grafana:

```bash
SYNC_MONITORING_SECRETS=true ./docker/sync-infisical-secrets.sh
```

This writes `.secrets/grafana_admin_password`, which Compose mounts into Grafana.
It initializes new Grafana databases; existing accounts retain their passwords.
Then set these non-secret values in `.env`:

```dotenv
OTEL_ENABLED=true
OTEL_TRACES_SAMPLER_ARG=1.0
```

Build and start:

```bash
docker compose --profile monitoring config --quiet
docker compose --profile monitoring up -d --build
```

The profile starts the Collector and Tempo alongside the existing monitoring
services. Only the Collector joins both application and monitoring networks.
Neither tracing service publishes host ports. Grafana queries `http://tempo:3200`.
Tempo stores traces in `tempo-data` with 72-hour retention; this is not a disk-size
quota. This local storage configuration is intended for a single Docker host.

Open Grafana at `http://localhost:3000`, then **Explore → Tempo**. Make a request:

```bash
curl -G http://localhost:8000/graphql/ \
  --data-urlencode 'query=query TraceDemo { __typename }'
```

After a few seconds, search with TraceQL:

```traceql
{ resource.service.name = "graphql-shop-web" }
```

Open the trace to inspect its span timeline. Creating an order through an
existing authenticated REST or GraphQL client also produces a task publish span
and a related `graphql-shop-worker` execution span. Scheduled cancellation tasks
originate from `graphql-shop-beat` rather than a user request. Prometheus continues
storing infrastructure metrics; tracing does not add application metric dashboards.

## Operation and data capture

- Set `OTEL_TRACES_SAMPLER_ARG=0.1` to sample about 10% of root traces. Descendants
  follow their parent's sampling decision. Use 1.0 while testing.
- Export uses a bounded background queue and a five-second export timeout.
  Collector outages can lose spans but do not make requests wait for export.
- Exported span attributes use an explicit allowlist. Request bodies, GraphQL
  documents/variables, SQL statements, Redis arguments, headers, exception text,
  and URL query strings are removed. Operation names, routes, timings, status,
  service metadata and dependency hosts remain. Use descriptive GraphQL operation
  names without user data. Span events and links are omitted by this filter.
- Gunicorn initializes tracing while importing WSGI inside each worker. Keep
  `--preload` disabled. Celery uses `worker_process_init` for the configured prefork
  pool; alternative worker pools need their own initialization integration.
- Plain management commands do not initialize exporters. For local `runserver`,
  set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` to a reachable Collector;
  the Compose receiver is intentionally not published to the host.

To disable tracing, set `OTEL_ENABLED=false` and recreate application processes:

```bash
docker compose up -d web celery-worker celery-beat
docker compose --profile monitoring stop otel-collector tempo
```

Keep Grafana running for historical traces only if Tempo also remains running.
Avoid `docker compose down -v`, which deletes application and monitoring volumes.

For empty traces, check that all app processes were recreated after enabling
tracing, the monitoring profile is running, and sampling is nonzero:

```bash
docker compose --profile monitoring logs --tail=100 web celery-worker otel-collector tempo
```

## Validation

```bash
python manage.py test shop.tests.test_telemetry --settings=config.test_settings
```

These tests verify disabled behavior, incoming HTTP trace context, GraphQL errors
at HTTP 200, sensitive attribute filtering, and task context propagation using an
in-memory Celery broker and worker. They do not require the Docker stack.

References: [Django instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/django/django.html),
[Celery process initialization](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/celery/celery.html),
[Collector to Tempo](https://grafana.com/docs/tempo/latest/set-up-for-tracing/instrument-send/set-up-collector/otel-collector/).
