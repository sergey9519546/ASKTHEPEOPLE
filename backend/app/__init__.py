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

from .config import Config
from .extensions import sock
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
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
            "frontend domain(s) to enable cross-origin access."
        )
        _cors_origins = 'http://127.0.0.1'
        _origins = [_cors_origins]
    else:
        _origins = [o.strip() for o in _cors_origins.split(',')] if _cors_origins != '*' else '*'
    CORS(app, resources={r"/api/*": {"origins": _origins}})

    # Warn when auth is enabled but CORS is wide open (dev-only now: production
    # wildcard is refused above, so this only fires in DEBUG mode).
    if app.config.get('APP_TOKEN') and _cors_origins == '*':
        logger.warning(
            "APP_TOKEN is set (production mode) but CORS_ORIGINS=* — "
            "set CORS_ORIGINS to your frontend domain(s) in production."
        )

    # Initialize Flask-Limiter (in-memory storage; no Redis dependency)
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
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")

    @app.before_request
    def require_auth():
        # Opt-in: if APP_TOKEN unset, auth is disabled (local dev compat)
        expected = app.config.get('APP_TOKEN')
        if not expected:
            return None
        # Health check always open
        if request.path == '/health':
            return None
        # Only protect API routes
        if not request.path.startswith('/api/'):
            return None
        # Browsers can't set headers on WS handshake — accept ?token= for WS routes only
        auth = request.headers.get('Authorization', '')
        token = None
        if auth.startswith('Bearer '):
            token = auth[7:]
        if token is None and request.args.get('token'):
            token = request.args.get('token')
        if not token or not hmac.compare_digest(str(token), str(expected)):
            return jsonify({"success": False, "error": "unauthorized"}), 401
    
    @app.after_request
    def log_response(response):
        logger = get_logger('askthepeople.request')
        logger.debug(f"Response: {response.status_code}")
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

    # Initialise WebSocket extension (must happen before ws routes are registered)
    sock.init_app(app)

    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp, settings_bp
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

    # Global exception handler for uncaught API errors
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Uncaught exception: {str(e)}", exc_info=True)
        if app.config.get('DEBUG'):
            # In debug mode, expose the message for developer convenience
            return {"success": False, "error": str(e)}, 500
        # In production, never leak internal structure to clients
        return {"success": False, "error": "internal_server_error"}, 500

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'ASKTHEPEOPLE Backend'}

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

