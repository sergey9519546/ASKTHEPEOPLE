"""
Celery Application Setup
Configures Celery with Redis broker and result backend.
"""

import os
from celery import Celery, bootsteps, signals
from .config import Config
from .utils.worker_startup import (
    clear_worker_ready_marker,
    publish_worker_ready_marker,
    remove_worker_ready_marker,
    validate_worker_configuration,
)

broker_url = (
    getattr(Config, 'CELERY_BROKER_URL', None)
    or getattr(Config, 'REDIS_URL', None)
    or 'redis://localhost:6379/0'
)
result_backend = (
    getattr(Config, 'CELERY_RESULT_BACKEND', None)
    or getattr(Config, 'REDIS_URL', None)
    or 'redis://localhost:6379/0'
)

celery_app = Celery(
    'askthepeople',
    broker=broker_url,
    backend=result_backend,
    include=[
        'app.tasks.simulation_tasks',
        'app.tasks.graph_tasks',
        'app.tasks.report_tasks',
        'app.tasks.zep_canary_tasks',
    ],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Periodic task schedule. The stale-task cleanup that used to run in a
    # daemon thread inside create_app() is now a Celery beat job owned by the
    # worker process (ADR-0003 §"same pattern as the P0 finding"). The
    # beat_schedule is a class attribute on the celery app; assigning it via
    # update() lets operators override it through celery_app.conf without
    # editing source. To enable beat, run `celery -A app.celery_app beat`
    # alongside the worker; in test/CI the cleanup task can be invoked
    # directly via cleanup_old_tasks_task.delay/max_age_hours.
    beat_schedule={
        'cleanup-old-stale-tasks': {
            'task': 'tasks.cleanup_old_tasks',
            'schedule': 3600.0,  # hourly, matching the former thread interval
            'kwargs': {'max_age_hours': 24},
        },
        'reconcile-stale-simulation-runs': {
            'task': 'tasks.reconcile_stale_simulation_runs',
            'schedule': 30.0,
            'kwargs': {'limit': 100},
        },
    },
)


def _worker_health_environment():
    """Return worker configuration without logging or contacting dependencies."""
    return {
        # Read deployed process variables directly. Config's localhost Redis
        # defaults are useful for development but are not release evidence.
        "ZEP_API_KEY": os.environ.get("ZEP_API_KEY"),
        "LLM_API_KEY": os.environ.get("LLM_API_KEY"),
        "REDIS_URL": os.environ.get("REDIS_URL"),
        "CELERY_BROKER_URL": os.environ.get("CELERY_BROKER_URL"),
        "CELERY_RESULT_BACKEND": os.environ.get("CELERY_RESULT_BACKEND"),
        "RAILWAY_GIT_COMMIT_SHA": os.environ.get("RAILWAY_GIT_COMMIT_SHA"),
        "BUILD_REVISION": os.environ.get("BUILD_REVISION"),
        "WORKER_HEALTH_MARKER": os.environ.get("WORKER_HEALTH_MARKER"),
    }


def _validate_worker_boot_configuration():
    environment = _worker_health_environment()
    validate_worker_configuration(environment)
    clear_worker_ready_marker(environment)


_ready_worker_pid = None


@signals.worker_ready.connect(weak=False)
def _on_worker_ready(sender=None, **_kwargs):
    """Publish availability only after Celery's consumer is ready."""
    del sender
    global _ready_worker_pid
    worker_pid = os.getpid()
    publish_worker_ready_marker(
        _worker_health_environment(),
        worker_pid=worker_pid,
    )
    _ready_worker_pid = worker_pid


@signals.heartbeat_sent.connect(weak=False)
def _on_worker_heartbeat(sender=None, **_kwargs):
    """Keep the attestation fresh only while the ready worker is heartbeating."""
    del sender
    if _ready_worker_pid == os.getpid():
        publish_worker_ready_marker(
            _worker_health_environment(),
            worker_pid=_ready_worker_pid,
        )


def _on_worker_shutdown(sender=None, **_kwargs):
    """Make the endpoint unavailable before the worker process exits."""
    del sender
    global _ready_worker_pid
    worker_pid = _ready_worker_pid
    if worker_pid is not None:
        remove_worker_ready_marker(
            _worker_health_environment(),
            worker_pid=worker_pid,
        )
    _ready_worker_pid = None


signals.worker_shutting_down.connect(_on_worker_shutdown, weak=False)
signals.worker_shutdown.connect(_on_worker_shutdown, weak=False)


class _WorkerConfigurationStep(bootsteps.StartStopStep):
    """Abort the real Celery worker blueprint before broker connection."""

    label = "Validate worker runtime configuration"

    def __init__(self, worker, **kwargs):
        _validate_worker_boot_configuration()
        super().__init__(worker, **kwargs)


celery_app.steps["worker"].add(_WorkerConfigurationStep)

if __name__ == '__main__':
    celery_app.start()
