"""
Health & Readiness API Endpoints
"""
import os
from flask import Blueprint, jsonify, current_app
from redis import Redis

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'], strict_slashes=False)
def health():
    """Liveness probe (existing behavior)"""
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
    payload = {
        'status': 'ok' if storage_writable else 'degraded',
        'service': 'ASKTHEPEOPLE Backend',
        'revision': (
            os.environ.get('RAILWAY_GIT_COMMIT_SHA')
            or os.environ.get('BUILD_REVISION')
            or 'unknown'
        ),
        'storage_writable': storage_writable,
    }
    return jsonify(payload), 200 if storage_writable else 503

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

    # 2. Redis Connectivity
    redis_ok = False
    try:
        redis_url = current_app.config.get('REDIS_URL')
        if redis_url and not redis_url.startswith('memory://'):
            client = Redis.from_url(redis_url, socket_timeout=1.0)
            redis_ok = client.ping()
        else:
            redis_ok = True  # Memory fallback
    except Exception:
        redis_ok = False

    # 3. Database Status (Placeholder for now until central DB is established)
    db_ok = True
    
    ready = storage_writable and redis_ok and db_ok

    payload = {
        'status': 'ok' if ready else 'degraded',
        'storage': 'ok' if storage_writable else 'error',
        'redis': 'ok' if redis_ok else 'error',
        'database': 'ok' if db_ok else 'error'
    }

    return jsonify(payload), 200 if ready else 503
