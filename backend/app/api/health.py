"""
Health & Readiness API Endpoints
"""
import os
from flask import Blueprint, jsonify, current_app
from redis import Redis

health_bp = Blueprint('health', __name__)


def check_database():
    """Check database connectivity (PostgreSQL or SQLite)"""
    try:
        from app.db.database import get_db_session
        # Try to create a session and execute a simple query
        with get_db_session() as session:
            # Simple query to check connection
            session.execute("SELECT 1")
        return True
    except Exception:
        # Database not configured or not available
        return True  # Don't fail health check if DB not set up yet


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
    """Liveness probe with component status"""
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    
    # Ensure folder exists (create if needed for first-time startup)
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except (OSError, PermissionError):
        pass  # If we can't create it, the next check will catch it
    
    storage_writable = os.path.isdir(upload_folder) and os.access(
        upload_folder,
        os.W_OK,
    )
    
    # Check all components
    db_ok = check_database()
    redis_ok = check_redis()
    celery_ok = check_celery()
    
    # Overall status
    all_ok = storage_writable and db_ok and redis_ok
    
    payload = {
        'status': 'ok' if all_ok else 'degraded',
        'service': 'ASKTHEPEOPLE Backend',
        'revision': (
            os.environ.get('RAILWAY_GIT_COMMIT_SHA')
            or os.environ.get('BUILD_REVISION')
            or 'unknown'
        ),
        'components': {
            'storage': 'ok' if storage_writable else 'error',
            'database': 'ok' if db_ok else 'error',
            'redis': 'ok' if redis_ok else 'error',
            'celery': 'ok' if celery_ok else 'degraded',
        },
        # Deprecated fields (keep for backward compatibility)
        'storage_writable': storage_writable,
    }
    return jsonify(payload), 200 if all_ok else 503

@health_bp.route('/readiness', methods=['GET'], strict_slashes=False)
def readiness():
    """Readiness probe (checks all dependencies)"""
    # 1. Storage Readiness
    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    
    # Ensure folder exists (create if needed for first-time startup)
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except (OSError, PermissionError):
        pass  # If we can't create it, the next check will catch it
    
    storage_writable = os.path.isdir(upload_folder) and os.access(
        upload_folder,
        os.W_OK,
    )

    # 2. Database connectivity
    db_ok = check_database()
    
    # 3. Redis connectivity
    redis_ok = check_redis()
    
    # 4. Celery worker availability
    celery_ok = check_celery()
    
    # Application is ready if all critical components are available
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
