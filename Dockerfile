# Stage 1: Backend Dependencies
FROM python:3.11-slim AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen
# Replace GPU torch with CPU-only to keep image small (OASIS uses API-based LLMs, not local GPU inference)
RUN .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps -q

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app

# Install necessary system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend environment and source
COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY backend/ /app/backend/

# Ensure the upload directory exists
RUN mkdir -p /app/backend/uploads

# Set environment
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend/run.py

EXPOSE 5001

# Single worker + threads: keeps in-memory state (TaskManager, SimulationRunner) consistent.
# Timeout 300s: supports long-running report generation (up to 15 min via background thread).
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "4", "--timeout", "300", "backend.run:app"]
