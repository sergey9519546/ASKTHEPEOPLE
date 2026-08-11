"""
Health & Readiness API Endpoints
"""
import os
from flask import Blueprint, jsonify, current_app
from redis import Redis
from sqlalchemy import text

from ..config import Config
from ..services.zep_dependency_status import (
    check_zep_dependency as _check_zep_dependency,
)
from ..utils.logger import get_logger
from ..utils.build_revision import resolve_deployed_revision

health_bp = Blueprint('health', __name__)
logger = get_logger('askthepeople.health')


def _revision() -> str:
    return resolve_deployed_revision() or 'unknown'


def check_zep_dependency():
    """Read the cached, sanitized status for the configured Zep project."""
    return _check_zep_dependency(Config.ZEP_API_KEY)


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
        # Keep web liveness independent, but never claim an unverified worker.
        return False


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
        # "degraded" covers both the fatal and non-fatal unhealthy cases. The
        # HTTP status carries the fatal/non-fatal distinction; splitting the
        # status string as well would break the established probe contract.
        'status': 'ok' if all_ok else 'degraded',
        'service': 'ASKTHEPEOPLE Backend',
        'revision': _revision(),
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
    """Readiness probe for required web and graph-backed dependencies."""
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

    try:
        zep_status = check_zep_dependency()
    except Exception as exc:
        logger.warning(
            "Zep readiness status failed reason=probe_failed exception=%s",
            type(exc).__name__,
            extra={"privacy_safe": True},
        )
        zep_status = {
            'status': 'error',
            'reason': 'probe_failed',
            'cached': False,
            'stale': False,
            'checked_at': None,
            'age_seconds': 0.0,
        }

    zep_ready = (
        zep_status.get('status') == 'ok'
        and zep_status.get('reason') == 'available'
        and zep_status.get('stale') is False
    )
    ready = storage_writable and db_ok and redis_ok and zep_ready

    payload = {
        'status': 'ready' if ready else 'not_ready',
        'scope': 'web',
        'revision': _revision(),
        'components': {
            'storage': 'ok' if storage_writable else 'error',
            'database': 'ok' if db_ok else 'error',
            'redis': 'ok' if redis_ok else 'error',
            'celery': 'ok' if celery_ok else 'degraded',
            'zep': 'ok' if zep_ready else 'error',
        },
        'dependencies': {
            'zep': zep_status,
        },
        'capabilities': {
            'web_graph_backed': 'ready' if zep_ready else 'unavailable',
        },
        # Flat keys for backward compatibility with test_health_readiness
        'storage': 'ok' if storage_writable else 'error',
        'database': 'ok' if db_ok else 'error',
        'redis': 'ok' if redis_ok else 'error',
    }

    return jsonify(payload), 200 if ready else 503
# Health endpoint with component status
