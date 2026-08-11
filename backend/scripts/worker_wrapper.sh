#!/bin/sh
# Own the Celery worker and its revision-bound HTTP availability attestation.

set -eu

WORKER_HEALTH_MARKER="${WORKER_HEALTH_MARKER:-/tmp/askthepeople-worker-ready.json}"
export WORKER_HEALTH_MARKER
CELERY_PID=""
HEALTH_PID=""

cleanup() {
  trap - EXIT
  if [ -n "${HEALTH_PID:-}" ]; then
    kill "$HEALTH_PID" 2>/dev/null || true
    wait "$HEALTH_PID" 2>/dev/null || true
  fi
  rm -f -- "$WORKER_HEALTH_MARKER"
}

forward_shutdown() {
  if [ -n "${CELERY_PID:-}" ]; then
    kill -TERM "$CELERY_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT
trap forward_shutdown INT TERM

# Pure configuration validation happens before either process can advertise
# availability. It performs no provider or dependency I/O.
python /app/backend/scripts/check_worker_zep_config.py

# A validated marker from an earlier process must never attest this worker.
rm -f -- "$WORKER_HEALTH_MARKER"

cd /app/backend

celery -A app.celery_app worker \
  --loglevel=info \
  --concurrency=1 \
  --max-tasks-per-child=100 \
  --time-limit=3600 \
  --soft-time-limit=3000 &
CELERY_PID=$!
export WORKER_PARENT_PID="$CELERY_PID"

# The server starts unavailable. Celery's worker_ready signal owns the first
# valid marker and worker heartbeats keep it fresh.
python /app/backend/scripts/worker_health.py &
HEALTH_PID=$!
echo "[wrapper] Worker availability endpoint started"

set +e
wait "$CELERY_PID"
WORKER_STATUS=$?
set -e
exit "$WORKER_STATUS"
