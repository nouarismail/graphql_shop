"""Opt-in tracing. Initialize only inside serving/worker processes."""
import os
from contextlib import contextmanager

_provider = None


def enabled():
    return os.getenv("OTEL_ENABLED", "false").lower() == "true"


@contextmanager
def span(name):
    if not enabled():
        yield None
        return
    from opentelemetry import trace
    with trace.get_tracer("graphql-shop").start_as_current_span(
        name, record_exception=False, set_status_on_exception=False,
    ) as current:
        try:
            yield current
        except Exception:
            from opentelemetry.trace import StatusCode
            current.set_status(StatusCode.ERROR)
            raise


def setup_tracing(service_name, *, django=False):
    global _provider
    if not enabled() or _provider is not None:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from config.trace_exporter import SanitizingExporter

    provider = TracerProvider(resource=Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
    }))
    provider.add_span_processor(BatchSpanProcessor(SanitizingExporter(OTLPSpanExporter())))
    trace.set_tracer_provider(provider)
    _provider = provider
    PsycopgInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)
    if django:
        DjangoInstrumentor().instrument(tracer_provider=provider)


def shutdown_tracing(**kwargs):
    if _provider is not None:
        _provider.shutdown()
