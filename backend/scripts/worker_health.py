"""
Minimal HTTP health server for the Celery worker.

Railway requires an HTTP health check at /health. Celery doesn't serve HTTP,
so this tiny server runs as a background thread alongside the worker process.

Usage (from Dockerfile.worker CMD):
    python /app/backend/scripts/worker_health.py &
    exec celery -A app.celery_app worker ...
"""

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/health/ready", "/health/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"celery-worker"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        # Suppress access logs — they clutter Celery output
        pass


def run():
    port = int(os.environ.get("PORT", 5001))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    # Run in daemon thread so it exits when Celery exits
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[worker_health] Health server listening on :{port}", flush=True)
    # Keep the main thread alive (Celery will be exec'd after this returns)
    # Actually we just return — the caller backgrounded us with &


if __name__ == "__main__":
    run()
    # Block until killed (when run directly as a background process)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        sys.exit(0)
