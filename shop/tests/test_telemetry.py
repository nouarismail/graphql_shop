"""Exercise instrumentation in isolated processes to avoid global SDK state."""
import os
import subprocess
import sys
from textwrap import dedent

from django.test import SimpleTestCase


BOOTSTRAP = '''
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.test_settings'
from unittest.mock import patch
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
memory = InMemorySpanExporter()
with patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter', return_value=memory):
    from config.telemetry import setup_tracing
    setup_tracing('test-web', django=True)
import django
django.setup()
from config import telemetry
from opentelemetry import trace
from django.test import Client, override_settings
'''


class TelemetryTests(SimpleTestCase):
    def run_script(self, script, *, enabled=True):
        env = {**os.environ, 'OTEL_ENABLED': str(enabled).lower(),
               'OTEL_TRACES_SAMPLER': 'always_on'}
        result = subprocess.run(
            [sys.executable, '-c', dedent(script)], env=env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_disabled_does_not_load_sdk(self):
        self.run_script('''
            import sys
            from config.telemetry import setup_tracing, span
            setup_tracing('disabled', django=True)
            with span('disabled') as current:
                assert current is None
            assert 'opentelemetry.sdk.trace' not in sys.modules
        ''', enabled=False)

    def test_http_parent_and_graphql_error_at_http_200(self):
        self.run_script(BOOTSTRAP + '''
with override_settings(ALLOWED_HOSTS=['testserver']):
    client = Client()
    response = client.post('/graphql/',
        data={'query': 'query TraceProbe { __typename }'}, content_type='application/json',
        HTTP_TRACEPARENT='00-12345678901234567890123456789012-1234567890123456-01')
    assert response.status_code == 200, response.content
    # Protected field returns a GraphQL error while the HTTP request succeeds.
    response = client.post('/graphql/',
        data={'query': 'query Forbidden { orders { id } }'}, content_type='application/json')
    assert response.status_code == 200, response.content
    assert response.json().get('errors'), response.content
telemetry._provider.force_flush()
spans = memory.get_finished_spans()
operation = next(s for s in spans if s.name == 'graphql.query TraceProbe')
assert operation.context.trace_id == int('12345678901234567890123456789012', 16)
server = next(s for s in spans if s.context.span_id == operation.parent.span_id)
assert server.parent.span_id == int('1234567890123456', 16)
assert server.attributes['http.route'] == 'graphql/'
failed = next(s for s in spans if s.name == 'graphql.query Forbidden')
assert failed.status.status_code.name == 'ERROR'
assert failed.attributes['graphql.error.count'] > 0
telemetry.shutdown_tracing()
''')

    def test_export_removes_sensitive_data(self):
        self.run_script(BOOTSTRAP + '''
from opentelemetry.trace import Status, StatusCode
with trace.get_tracer('test').start_as_current_span('safe.operation') as current:
    current.set_attribute('db.statement', 'SELECT secret')
    current.set_attribute('db.query.text', 'SELECT secret')
    current.set_attribute('http.url', 'http://example.com/?token=secret')
    current.set_attribute('http.request.header.authorization', 'secret')
    current.set_attribute('graphql.operation.name', 'Example')
    current.record_exception(ValueError('secret'))
    current.set_status(Status(StatusCode.ERROR, 'secret'))
telemetry._provider.force_flush()
exported = memory.get_finished_spans()[0]
assert dict(exported.attributes) == {'graphql.operation.name': 'Example'}
assert not exported.events
assert exported.status.description is None
assert exported.status.status_code == StatusCode.ERROR
telemetry.shutdown_tracing()
''')

    def test_celery_publish_propagates_parent(self):
        self.run_script(BOOTSTRAP + '''
from celery import Celery
from celery.signals import before_task_publish
app = Celery('tracing-test', broker='memory://', backend='cache+memory://')
headers_seen = []
@before_task_publish.connect(weak=False)
def capture(headers=None, **kwargs):
    headers_seen.append(dict(headers))
@app.task(name='tracing-test.noop')
def noop():
    return True
from celery.contrib.testing.worker import start_worker
with start_worker(app, pool='solo', perform_ping_check=False):
    with trace.get_tracer('test').start_as_current_span('request') as parent:
        result = noop.apply_async()
    assert result.get(timeout=10) is True
telemetry._provider.force_flush()
producer = next(s for s in memory.get_finished_spans() if s.name == 'apply_async/tracing-test.noop')
assert producer.parent.span_id == parent.get_span_context().span_id
assert headers_seen[0]['traceparent'].split('-')[1] == format(parent.get_span_context().trace_id, '032x')
consumer = next(s for s in memory.get_finished_spans() if s.name == 'run/tracing-test.noop')
assert consumer.context.trace_id == producer.context.trace_id
assert consumer.parent.span_id == producer.context.span_id
telemetry.shutdown_tracing()
''')
