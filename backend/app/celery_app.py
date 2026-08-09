"""
Celery Application Setup
Configures Celery with Redis broker and result backend.
"""

import os
from celery import Celery
from .config import Config

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

if __name__ == '__main__':
    celery_app.start()
