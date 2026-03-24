# Stage 1: Backend Dependencies
FROM python:3.11-slim AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen
# Swap GPU torch for CPU-only and strip all NVIDIA/CUDA packages
# (OASIS uses API-based LLMs via OpenRouter, not local GPU inference)
RUN uv pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps && \
    uv pip uninstall \
        nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 \
        nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 \
        nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 \
        nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvtx-cu12 triton \
        2>/dev/null || true

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /app/backend/.venv /app/backend/.venv
COPY backend/ /app/backend/

RUN mkdir -p /app/backend/uploads

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend/run.py

EXPOSE 5001

# Verify the app can be imported at build time — surfaces import errors in CI logs.
RUN cd /app/backend && python -c "import sys; sys.path.insert(0, '.'); from app import create_app; app = create_app(); print('WSGI app import OK')"

# Single worker + threads: keeps in-memory state (TaskManager, SimulationRunner) consistent.
# Timeout 300s: supports long-running report generation via background thread.
# --chdir ensures wsgi.py is loaded from /app/backend so `from app import ...` resolves correctly.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "4", "--timeout", "300", "--chdir", "/app/backend", "wsgi:app"]
