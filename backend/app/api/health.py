"""
Health & Readiness API Endpoints
"""
import os
import threading
import time

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

# Hard wall-clock ceiling for every /health probe (seconds). /health is the
# container HEALTHCHECK target (Dockerfile: urllib timeout=3, HEALTHCHECK
# timeout=5) and must answer even when Redis/Celery/DB are dead or
# black-holed (SYN dropped, no RST). A probe that cannot answer inside the
# budget degrades its component instead of stalling liveness. The original
# implementation took ~10s when the broker was down — an unbounded Redis
# connect plus Celery's broker connection retry — which tripped the
# HEALTHCHECK and would restart the container on any broker hiccup.
PROBE_DEADLINE_SECONDS = 1.5


def _revision() -> str:
    return resolve_deployed_revision() or 'unknown'


def _probe_with_deadline(fn):
    """Run fn on a daemon thread; return its result iff it finishes within
    PROBE_DEADLINE_SECONDS, else None (reported as degraded).

    The daemon thread keeps running after a timeout but cannot stall the
    process or the request: it is a liveness probe, not a critical task, and
    the socket timeouts inside each probe bound it to a few seconds at most.
    """
    box = {}

    def _target():
        # Never let a probe exception escape into a background thread: an
        # abandoned thread must exit silently when its own socket timeout
        # fires, not print an unhandled traceback to stderr on every
        # degraded health check.
        try:
            box['value'] = fn()
        except Exception:
            box['value'] = False

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(PROBE_DEADLINE_SECONDS)
    if worker.is_alive():
        logger.warning(
            "health probe exceeded deadline reason=probe_timeout "
            "timeout_s=%s",
            PROBE_DEADLINE_SECONDS,
            extra={"privacy_safe": True},
        )
        return None
    return box.get('value')


def _run_probes_concurrently():
    """Run the database, redis and celery probes concurrently so /health
    latency tracks the slowest single probe (~1.5s) instead of their sum.

    Flask's app context does not propagate into child threads (verified
    against Flask 3.1 / Werkzeug 3.1), so the app object is captured in the
    request thread and pushed into each capture thread; the module-level
    check_* functions remain the patch seam used by tests.
    """
    app = current_app._get_current_object()
    results = {}

    def _capture(name):
        fn = {
            'database': check_database,
            'redis': check_redis,
            'celery': check_celery,
        }[name]
        with app.app_context():
            try:
                results[name] = fn()
            except Exception:
                results[name] = False

    workers = [
        threading.Thread(target=_capture, args=(name,), daemon=True)
        for name in ('database', 'redis', 'celery')
    ]
    for worker in workers:
        worker.start()

    # Shared deadline with budget accounting: concurrent threads must not be
    # joined for the full deadline each (that would reserialize the sum).
    deadline = PROBE_DEADLINE_SECONDS + 0.5
    start = time.monotonic()
    for worker in workers:
        remaining = deadline - (time.monotonic() - start)
        if remaining > 0:
            worker.join(remaining)

    return (
        results.get('database') is True,
        results.get('redis') is True,
        results.get('celery') is True,
    )


def check_zep_dependency():
    """Read the cached, sanitized status for the configured Zep project."""
    return _check_zep_dependency(Config.ZEP_API_KEY)


def check_database():
    """Check database connectivity (PostgreSQL or SQLite), deadline-bounded."""
    try:
        return _probe_with_deadline(_database_probe) is True
    except Exception:
        return False


def _database_probe() -> bool:
    from app.db import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def check_redis():
    """Check Redis connectivity, deadline-bounded."""
    try:
        app = current_app._get_current_object()
        return _probe_with_deadline(lambda: _redis_probe(app)) is True
    except Exception:
        return False


def _redis_probe(app) -> bool:
    redis_url = app.config.get('REDIS_URL')
    if redis_url and not redis_url.startswith('memory://'):
        client = Redis.from_url(
            redis_url,
            socket_timeout=PROBE_DEADLINE_SECONDS,
            socket_connect_timeout=PROBE_DEADLINE_SECONDS,
        )
        try:
            return client.ping()
        finally:
            client.close()
    else:
        return True  # Memory fallback or not configured


def check_celery():
    """Deadline-bounded Celery worker availability check."""
    try:
        return _probe_with_deadline(_celery_probe) is True
    except Exception:
        return False


def _celery_probe() -> bool:
    from urllib.parse import urlsplit
    import socket
    from celery import current_app as celery_app

    # Fast-fail at the TCP layer before kombu's broker-connection retry loop
    # can engage. A dead broker would otherwise keep the abandoned probe
    # thread alive retrying for minutes after the deadline gives up on it
    # (a thread leak on every degraded health check).
    broker_url = celery_app.conf.broker_url or ''
    if not broker_url.startswith('memory://'):
        parts = urlsplit(broker_url)
        host = parts.hostname or 'localhost'
        if parts.scheme in ('amqp', 'amqps'):
            port = parts.port or 5672
        else:
            port = parts.port or 6379
        with socket.create_connection(
            (host, port),
            timeout=PROBE_DEADLINE_SECONDS,
        ):
            pass  # broker answers at TCP level; proceed to the real probe

    inspector = celery_app.control.inspect(timeout=PROBE_DEADLINE_SECONDS)
    stats = inspector.stats()
    return stats is not None and len(stats) > 0


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

    # Check all components concurrently, each deadline-bounded
    db_ok, redis_ok, celery_ok = _run_probes_concurrently()

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

    db_ok, redis_ok, celery_ok = _run_probes_concurrently()

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

    # readiness reflects a measured state today, not an optimistic prediction:
    # it is locked by the deploy workflow's "verify Zep-backed production
    # readiness" step, which blocks gate passes on an honest probe.
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