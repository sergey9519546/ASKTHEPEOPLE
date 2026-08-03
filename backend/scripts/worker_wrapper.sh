#!/bin/sh
# Wrapper script to run health server and Celery worker together
# The health server runs in the background; Celery runs in foreground

set -e

# Start health server in background
python /app/backend/scripts/worker_health.py &
HEALTH_PID=$!

echo "[wrapper] Started health server (PID $HEALTH_PID)"

# Start Celery in foreground (replaces this shell)
exec celery -A app.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --max-tasks-per-child=100 \
  --time-limit=3600 \
  --soft-time-limit=3000
