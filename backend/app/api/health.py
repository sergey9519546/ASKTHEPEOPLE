"""
Health & Readiness API Endpoints
"""
import os
from flask import Blueprint, jsonify, current_app
from redis import Redis
from sqlalchemy import text

health_bp = Blueprint('health', __name__)


def check_database():
    """Check database connectivity (PostgreSQL or SQLite)"""
    try:
        from app.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        # Database not configured or not available
        return False  # Report actual state instead of always True


def check_redis():
    """Check Redis connectivity"""
    try:
        redis_url = current_app.config.get('REDIS_URL')
        if redis_url and not redis_url.startswith('memory://'):
            client = Redis.from_url(redis_url, socket_timeout=1.0)
            return client.ping()
        else:
            return True  # Memory fallback or not configured
    except Exception:
        return False


def check_celery():
    """Check Celery worker availability"""
    try:
        from celery import current_app as celery_app
        inspector = celery_app.control.inspect(timeout=1.0)
        stats = inspector.stats()
        return stats is not None and len(stats) > 0
    except Exception:
        # Celery not configured or not available
        return True  # Don't fail health check if Celery not set up yet


@health_bp.route('/', methods=['GET'], strict_slashes=False)
def health():
    """Liveness probe with component status.
    
    Returns 503 only for FATAL conditions that mean the app cannot serve requests.
    Degraded conditions (Redis unavailable, Celery down) return 200 with
    status='degraded' so Railway doesn't kill the deployment unnecessarily.
    
    Fatal (503): storage not writable
    Degraded (200): database unavailable, Redis unavailable, Celery down
    """
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    
    # Ensure folder exists (create if needed for first-time startup)
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except (OSError, PermissionError):
        pass

    storage_writable = os.path.isdir(upload_folder) and os.access(
        upload_folder,
        os.W_OK,
    )

    # Check all components
    db_ok = check_database()
    redis_ok = check_redis()
    celery_ok = check_celery()

    # Only storage failure is fatal — the app cannot function without writable storage.
    # Redis and DB unavailability are degraded: app starts, tasks queue when Redis recovers.
    is_fatal = not storage_writable
    all_ok = storage_writable and db_ok and redis_ok

    payload = {
        'status': 'ok' if all_ok else ('error' if is_fatal else 'degraded'),
        'service': 'ASKTHEPEOPLE Backend',
        'revision': (
            os.environ.get('RAILWAY_GIT_COMMIT_SHA')
            or os.environ.get('BUILD_REVISION')
            or 'unknown'
        ),
        'components': {
            'storage': 'ok' if storage_writable else 'error',
            'database': 'ok' if db_ok else 'degraded',
            'redis': 'ok' if redis_ok else 'degraded',
            'celery': 'ok' if celery_ok else 'degraded',
        },
        # Deprecated fields (keep for backward compatibility)
        'storage_writable': storage_writable,
    }
    # 503 only when storage is broken — Railway liveness must pass for the app to serve
    return jsonify(payload), 503 if is_fatal else 200


@health_bp.route('/readiness', methods=['GET'], strict_slashes=False)
def readiness():
    """Readiness probe — all dependencies must be available."""
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])

    try:
        os.makedirs(upload_folder, exist_ok=True)
    except (OSError, PermissionError):
        pass

    storage_writable = os.path.isdir(upload_folder) and os.access(
        upload_folder,
        os.W_OK,
    )

    db_ok = check_database()
    redis_ok = check_redis()
    celery_ok = check_celery()

    ready = storage_writable and db_ok and redis_ok

    payload = {
        'status': 'ready' if ready else 'not_ready',
        'components': {
            'storage': 'ok' if storage_writable else 'error',
            'database': 'ok' if db_ok else 'error',
            'redis': 'ok' if redis_ok else 'error',
            'celery': 'ok' if celery_ok else 'degraded',
        }
    }

    return jsonify(payload), 200 if ready else 503
