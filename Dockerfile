# Stage 1: Frontend Build
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Pass Railway backend URL at build time so Vite bakes it into the bundle
# Empty default = relative URLs, so the unified container works on any Railway URL.
# Override at build time (e.g. for a standalone Vercel frontend) if needed.
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2: Backend Dependencies
FROM python:3.11-slim AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
# uv sync (without --frozen) lets Docker resolve new deps not yet in uv.lock
# (e.g. flask-sock) while keeping all pinned packages at their locked versions.
# Run `uv lock` locally and commit the updated uv.lock to restore --frozen.
#
# CPU-only torch is pinned via [tool.uv.sources] in pyproject.toml, and all
# nvidia-*/triton transitive GPU packages are blocked via [tool.uv] override
# markers (sys_platform == 'never'). This eliminates the ~3GB CUDA download
# that previously caused Railway build timeouts.
RUN uv sync --extra dev

# Stage 3: Runtime
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY backend/ /app/backend/

# Copy built frontend dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN mkdir -p /app/backend/uploads /app/backend/uploads/simulations /app/backend/logs

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend/run.py

EXPOSE 5001

# Verify the app can be imported at build time — surfaces import errors in CI logs.
# SECRET_KEY is set to a dummy value just for the smoke test; the real key is
# provided at runtime via Railway environment variables.
RUN cd /app/backend && SECRET_KEY=build-smoke-test python -c "import sys; sys.path.insert(0, '.'); from app import create_app; app = create_app(); print('WSGI app import OK')"

# Run as non-root user for defense-in-depth
RUN useradd --create-home --shell /bin/false --uid 10001 app \
    && chown -R app:app /app
USER app

# Single worker + threads: keeps in-memory state (TaskManager, SimulationRunner) consistent.
# Timeout 300s: supports long-running report generation via background thread.
# --chdir ensures wsgi.py is loaded from /app/backend so `from app import ...` resolves correctly.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 4 --timeout 300 --chdir /app/backend wsgi:app"]

