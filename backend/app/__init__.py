"""
ASKTHEPEOPLE Backend - Flask Application Factory
"""

import json
import os
import threading
import time
import warnings

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Needs to be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
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
    
    # Warn when running with the default hardcoded SECRET_KEY
    _DEFAULT_SECRET = 'askthepeople-secret-key'
    if app.config.get('SECRET_KEY') == _DEFAULT_SECRET:
        logger.warning(
            "SECRET_KEY is using the insecure default value. "
            "Set SECRET_KEY in your .env file before deploying to production."
        )

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
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
    
    @app.after_request
    def log_response(response):
        logger = get_logger('askthepeople.request')
        logger.debug(f"Response: {response.status_code}")
        return response

    @app.after_request
    def strip_traceback_in_production(response):
        """Remove internal tracebacks from JSON error responses in non-debug mode."""
        if not app.config.get('DEBUG') and response.is_json:
            try:
                data = response.get_json(silent=True)
                if isinstance(data, dict) and 'traceback' in data:
                    data.pop('traceback')
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
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    
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

