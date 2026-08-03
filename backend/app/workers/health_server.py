"""
Embedded health server for Railway worker deployment.

Runs in a background thread alongside Celery to provide Railway's required
TCP healthcheck endpoint without needing process supervision.
"""
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that always returns 200 OK."""
    
    def do_GET(self):
        """Handle GET requests to any path."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK\n')
    
    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


def start_health_server(port=8080, host='0.0.0.0'):
    """
    Start health server in a daemon thread.
    
    Args:
        port: TCP port to listen on (default 8080 for Railway)
        host: Interface to bind to (default all interfaces)
    """
    server = HTTPServer((host, port), HealthHandler)
    
    def serve():
        logger.info(f'[worker_health] Health server listening on {host}:{port}')
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f'[worker_health] Health server error: {e}')
    
    thread = threading.Thread(target=serve, daemon=True, name='health-server')
    thread.start()
    logger.info('[worker_health] Health server thread started')
