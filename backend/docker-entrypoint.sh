#!/bin/sh
set -eu

uploads_dir="/app/backend/uploads"
logs_dir="/app/backend/logs"

# A Railway volume replaces the image-owned directory with a root-owned mount.
# Fix only the two application-writable locations, then permanently drop
# privileges before starting Gunicorn or any simulation subprocess. Correct
# the mount roots before creating children so a restricted-capability Compose
# container can initialize a host bind mount. Avoid a full recursive chown on
# the common path where the stable application UID already owns every entry.
chown app:app "$uploads_dir" "$logs_dir"
gosu app install -d "$uploads_dir/simulations"
ownership_mismatch="$(
  find "$uploads_dir" "$logs_dir" \
    \( ! -user app -o ! -group app \) -print -quit
)"
if [ -n "$ownership_mismatch" ]; then
  chown -R app:app "$uploads_dir" "$logs_dir"
fi

if ! gosu app test -w "$uploads_dir"; then
  echo "fatal: application upload storage is not writable by UID 10001" >&2
  exit 1
fi

# Allow per-service start command override via env var.
# The worker service sets START_COMMAND=celery...; the web service leaves it
# unset and falls through to the Dockerfile CMD (gunicorn).
if [ -n "${START_COMMAND:-}" ]; then
  exec gosu app sh -c "$START_COMMAND"
fi

exec gosu app "$@"
