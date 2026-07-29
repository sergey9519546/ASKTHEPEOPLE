"""
ASKTHEPEOPLE Backend - Flask Application Factory
"""

import json
import os
import threading
import time
import warnings
import hmac

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Needs to be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .config import Config, credential_validation_error
from .extensions import sock
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get("REQUIRE_APP_AUTH"):
        token_error = credential_validation_error(
            "APP_TOKEN",
            app.config.get("APP_TOKEN"),
        )
        if token_error:
            raise RuntimeError(
                f"{token_error}. Refusing to create an application with "
                "weak or missing access control."
            )
    if not app.config.get("DEBUG", False):
        secret_error = credential_validation_error(
            "SECRET_KEY",
            app.config.get("SECRET_KEY"),
        )
        if secret_error:
            raise RuntimeError(secret_error)
    
    # Set JSON encoding: ensure characters are displayed directly (instead of \uXXXX format)
    # Flask >= 2.3 uses app.json.ensure_ascii, older versions use JSON_AS_ASCII configuration
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Set logging
    logger = setup_logger('askthepeople')
    
    # Only print startup info in reloader subprocess (avoid printing twice in debug mode)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("ASKTHEPEOPLE Backend starting...")
        logger.info("=" * 50)

    # Enable CORS
    _cors_origins = app.config.get('CORS_ORIGINS', '*')
    _is_production = not app.config.get('DEBUG', False)

    # H3: refuse wildcard CORS in production. Falling back to a local-only
    # origin keeps the app runnable (and tests green) while preventing any
    # remote website from driving the API. Operators must set CORS_ORIGINS
    # explicitly to expose the API to their frontend.
    if _is_production and _cors_origins.strip() == '*':
        logger.critical(
            "CORS_ORIGINS='*' is not allowed in production (DEBUG=False). "
            "Falling back to http://127.0.0.1 only — set CORS_ORIGINS to your "
            "frontend domain(s) to enable cross-origin access.",
            extra={"privacy_safe": True},
        )
        _cors_origins = 'http://127.0.0.1'
        _origins = [_cors_origins]
    else:
        _origins = [o.strip() for o in _cors_origins.split(',')] if _cors_origins != '*' else '*'
    app.config['CORS_ALLOWED_ORIGINS'] = _origins
    CORS(app, resources={r"/api/*": {"origins": _origins}})

    # Warn when auth is enabled but CORS is wide open (dev-only now: production
    # wildcard is refused above, so this only fires in DEBUG mode).
    if app.config.get('APP_TOKEN') and _cors_origins == '*':
        logger.warning(
            "APP_TOKEN is set (production mode) but CORS_ORIGINS=* — "
            "set CORS_ORIGINS to your frontend domain(s) in production.",
            extra={"privacy_safe": True},
        )

    # Initialise WebSocket extension (must happen before ws routes are registered/imported)
    sock.init_app(app)

    # In-memory rate limiting is intentional while task and simulation state
    # constrain the application to one worker.
    from .api import limiter as _limiter
    _limiter.init_app(app)
    
    # Register simulation process cleanup function (ensure all simulation processes are terminated when server closes)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulation process cleanup function registered")
    
    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('askthepeople.request')
        # Never log request bodies: settings and provider-test requests may
        # contain API keys, uploaded source text can contain personal data,
        # and DEBUG file logs otherwise turn those values into retained data.
        logger.debug(
            "Request: %s %s content_length=%s",
            request.method,
            request.path,
            request.content_length,
        )

    @app.before_request
    def require_auth():
        # create_app() has already failed closed when REQUIRE_APP_AUTH is true.
        # An unset token therefore means explicitly unauthenticated local dev.
        expected = app.config.get('APP_TOKEN')
        if not expected:
            return None
        # Health check always open
        if request.path == '/health':
            return None
        # Only protect API routes
        if not request.path.startswith('/api/'):
            return None
        auth = request.headers.get('Authorization', '')
        token = auth[7:] if auth.startswith('Bearer ') else None
        if not token or not hmac.compare_digest(str(token), str(expected)):
            return jsonify({"success": False, "error": "unauthorized"}), 401
    
    @app.after_request
    def log_response(response):
        logger = get_logger('askthepeople.request')
        logger.debug(f"Response: {response.status_code}")
        return response

    @app.after_request
    def apply_security_headers(response):
        """Apply browser and cache policy at the HTTP response seam."""
        if not app.config.get("DEBUG", False):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "base-uri 'self'; "
                "object-src 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:; "
                "worker-src 'self' blob:; "
                "manifest-src 'self'",
            )
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
            )
            response.headers.setdefault(
                "Cross-Origin-Opener-Policy",
                "same-origin",
            )
            response.headers.setdefault(
                "Cross-Origin-Resource-Policy",
                "same-origin",
            )
            forwarded_proto = request.headers.get(
                "X-Forwarded-Proto",
                "",
            ).split(",", 1)[0].strip().lower()
            if request.is_secure or forwarded_proto == "https":
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )

        if request.path == "/health" or request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.after_request
    def strip_traceback_in_production(response):
        """Remove internal tracebacks and error strings from JSON 5xx responses.

        In non-debug mode this strips the ``traceback`` key entirely and
        replaces the ``error`` field with a generic message for any 5xx
        response, so internal paths, credentials, or upstream API error
        bodies leaked via ``str(e)`` cannot reach clients. 4xx responses
        are left intact: client errors are informative (bad request, not
        found, unauthorized) and do not reflect server internals.
        """
        if not app.config.get('DEBUG') and response.is_json:
            try:
                data = response.get_json(silent=True)
                if isinstance(data, dict):
                    mutated = False
                    if 'traceback' in data:
                        data.pop('traceback')
                        mutated = True
                    # Scrub the error string on 5xx — str(e) commonly leaks
                    # internal hostnames, file paths, and upstream API bodies.
                    if response.status_code >= 500 and 'error' in data:
                        data['error'] = 'internal_server_error'
                        mutated = True
                    if mutated:
                        response.set_data(json.dumps(data, ensure_ascii=False))
            except Exception:
                pass
        return response
    
    # Periodic cleanup of stale completed/failed tasks (prevents unbounded memory growth)
    def _task_cleanup_worker():
        from .models.task import TaskManager
        while True:
            time.sleep(3600)  # Every hour
            try:
                TaskManager().cleanup_old_tasks(max_age_hours=24)
            except Exception:
                pass

    cleanup_thread = threading.Thread(target=_task_cleanup_worker, daemon=True, name="task-cleanup")
    cleanup_thread.start()

    # Register blueprints
    from .api import auth_bp, graph_bp, simulation_bp, report_bp, settings_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # Register WebSocket routes (imported here so sock is already init'd)
    from .api import ws  # noqa: F401
    
    # Rate-limit handler — must be registered before the catch-all so
    # flask_limiter.RateLimitExceeded returns 429 (not 500).
    try:
        from flask_limiter import RateLimitExceeded

        @app.errorhandler(RateLimitExceeded)
        def handle_rate_limit(e):
            return {"success": False, "error": "rate_limit_exceeded"}, 429
    except ImportError:
        pass  # flask-limiter not installed; rate limiting disabled

    from .utils.safe_path import SafePathError

    @app.errorhandler(SafePathError)
    def handle_unsafe_path(_error):
        return jsonify({"success": False, "error": "invalid_id"}), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Preserve intentional HTTP statuses and make API errors JSON."""
        if request.path == '/api' or request.path.startswith('/api/'):
            error_name = (error.name or 'http_error').lower().replace(' ', '_')
            return jsonify({"success": False, "error": error_name}), error.code
        return error

    # Global exception handler for uncaught API errors
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return handle_http_exception(e)
        logger.error(f"Uncaught exception: {str(e)}", exc_info=True)
        if app.config.get('DEBUG'):
            # In debug mode, expose the message for developer convenience
            return {"success": False, "error": str(e)}, 500
        # In production, never leak internal structure to clients
        return {"success": False, "error": "internal_server_error"}, 500

    # Health check
    @app.route('/health')
    def health():
        upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
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
        return payload, 200 if storage_writable else 503

    # Keep unknown API routes out of the SPA catch-all.  Without this route,
    # a misspelled API URL returned index.html with status 200.
    @app.route('/api', defaults={'path': ''})
    @app.route('/api/<path:path>')
    def api_not_found(path):
        return jsonify({"success": False, "error": "not_found"}), 404

    # Serve static frontend files
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        import flask
        static_dir = os.path.join(app.root_path, '../../frontend/dist')
        if path != "" and os.path.exists(os.path.join(static_dir, path)):
            return flask.send_from_directory(static_dir, path)
        else:
            return flask.send_from_directory(static_dir, 'index.html')

    if should_log_startup:
        logger.info("ASKTHEPEOPLE Backend started successfully")
    
    return app
