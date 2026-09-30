"""Export only operational metadata, never command arguments or exception text."""
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.trace import Status

# Explicit allowlist also prevents newly introduced instrumentation attributes
# from silently exporting credentials, query strings, or request payloads.
SAFE_ATTRIBUTES = frozenset({
    "http.method", "http.request.method", "http.status_code", "http.response.status_code",
    "http.route", "network.protocol.version", "network.protocol.name",
    "server.address", "server.port", "net.peer.name", "net.peer.port",
    "db.system", "db.system.name", "db.operation", "db.operation.name",
    "celery.action", "celery.task_name", "messaging.system", "messaging.operation",
    "graphql.operation.name", "graphql.operation.type", "graphql.error.count",
})


class SanitizingExporter(SpanExporter):
    def __init__(self, delegate):
        self.delegate = delegate

    def export(self, spans):
        sanitized = [ReadableSpan(
            name=s.name, context=s.context, parent=s.parent, resource=s.resource,
            attributes={k: v for k, v in s.attributes.items() if k in SAFE_ATTRIBUTES},
            events=(), links=(), kind=s.kind,
            status=Status(s.status.status_code),
            start_time=s.start_time, end_time=s.end_time,
            instrumentation_scope=s.instrumentation_scope,
        ) for s in spans]
        return self.delegate.export(sanitized)

    def shutdown(self):
        return self.delegate.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self.delegate.force_flush(timeout_millis)
