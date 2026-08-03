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

is_testing = os.environ.get('PYTEST_CURRENT_TEST') is not None or getattr(Config, 'TESTING', False)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

if __name__ == '__main__':
    celery_app.start()
