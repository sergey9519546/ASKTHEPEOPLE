"""
Celery worker entrypoint with embedded health server.

This module is the worker process entrypoint. It starts the health server
in a background thread before initializing Celery, ensuring Railway's
TCP healthcheck passes.
"""
import logging
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Start health server first
try:
    from app.workers.health_server import start_health_server
    start_health_server(port=8080)
    logger.info('[worker_init] Health server started successfully')
except Exception as e:
    logger.error(f'[worker_init] Failed to start health server: {e}')
    # Continue anyway - health server is nice-to-have, not critical

# Now import and configure Celery
from app.celery_app import celery_app

logger.info('[worker_init] Celery configuration loaded')

if __name__ == '__main__':
    # Start Celery worker with standard arguments
    celery_app.worker_main(argv=[
        'worker',
        '--loglevel=INFO',
        '--pool=prefork',
        '--concurrency=2',
    ])
