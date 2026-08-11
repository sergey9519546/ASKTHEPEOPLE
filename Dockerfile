# syntax=docker/dockerfile:1.7

ARG NODE_IMAGE=node:24.18.0-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d
ARG PYTHON_IMAGE=python:3.11.15-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

FROM ${NODE_IMAGE} AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM ${PYTHON_IMAGE} AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:0.9.26@sha256:9a23023be68b2ed09750ae636228e903a54a05ea56ed03a934d00fe9fbeded4b /uv /uvx /bin/
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM ${PYTHON_IMAGE} AS runtime
WORKDIR /app

ARG GOSU_VERSION=1.17-3+b4
RUN apt-get update \
    && apt-get install -y --no-install-recommends "gosu=${GOSU_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

ARG BUILD_REVISION
LABEL org.opencontainers.image.title="ASKTHEPEOPLE" \
    org.opencontainers.image.description="Synthetic scenario explorer" \
    org.opencontainers.image.source="https://github.com/sergey9519546/ASKTHEPEOPLE" \
    org.opencontainers.image.licenses="AGPL-3.0-only" \
    org.opencontainers.image.revision="${BUILD_REVISION}"
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=backend/run.py \
    FLASK_DEBUG=false \
    PORT=5001

COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY backend/app/ /app/backend/app/
COPY backend/scripts/ /app/backend/scripts/
COPY backend/run.py backend/wsgi.py /app/backend/
COPY backend/docker-entrypoint.sh /usr/local/bin/askthepeople-entrypoint
COPY LICENSE /usr/share/licenses/askthepeople/AGPL-3.0.txt
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN printf '%s' "$BUILD_REVISION" \
      | grep -Eq '^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$' \
    && install -d -m 0755 /usr/share/askthepeople \
    && printf '%s\n' "$BUILD_REVISION" \
      > /usr/share/askthepeople/build-revision \
    && chmod 0444 /usr/share/askthepeople/build-revision

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 app \
    && install -d -o app -g app \
      /app/backend/uploads \
      /app/backend/uploads/simulations \
      /app/backend/logs \
    && chmod 0755 /usr/local/bin/askthepeople-entrypoint

EXPOSE 5001
STOPSIGNAL SIGTERM

RUN cd /app/backend \
    && python -c "import os, secrets; os.environ.update({'SECRET_KEY': secrets.token_urlsafe(32), 'APP_TOKEN': secrets.token_urlsafe(32), 'REQUIRE_APP_AUTH': 'true', 'LLM_API_KEY': 'build-validation-model-key', 'ZEP_API_KEY': 'build-validation-zep-key', 'CORS_ORIGINS': 'http://127.0.0.1', 'DATABASE_URL': 'sqlite:////tmp/build-validation.db'}); from wsgi import app; print('Validated WSGI import OK')" \
    && rm -f /tmp/build-validation.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '5001') + '/health', timeout=3).read()" || exit 1

# One worker is intentional while task/simulation state is process-local.
ENTRYPOINT ["/usr/local/bin/askthepeople-entrypoint"]
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 4 --timeout 300 --graceful-timeout 240 --access-logfile - --access-logformat '%(h)s %(l)s %(u)s %(t)s \"%(m)s %(U)s %(H)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\"' --error-logfile - --chdir /app/backend wsgi:app"]
