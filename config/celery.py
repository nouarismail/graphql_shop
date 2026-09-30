import os

from celery import Celery
from celery.signals import beat_init, worker_process_init, worker_process_shutdown

from config.telemetry import setup_tracing, shutdown_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# The prefork parent must not create an exporter thread before forking.


@worker_process_init.connect(weak=False)
def initialize_worker_tracing(**kwargs):
    setup_tracing("graphql-shop-worker")


@beat_init.connect(weak=False)
def initialize_beat_tracing(**kwargs):
    setup_tracing("graphql-shop-beat")


worker_process_shutdown.connect(shutdown_tracing, weak=False)
