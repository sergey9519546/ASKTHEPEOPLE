# Celery Worker Setup for Production

## Problem Summary

**Status:** P0 — Production Blocker  
**Impact:** 5 of 7 background job endpoints fail in production  
**Root Cause:** No Celery worker process is defined or running in any deployment configuration

## Current State

### What Exists (Backend Code)
- ✅ Celery app fully configured (`app/celery_app.py`)
- ✅ 5 task definitions across 3 modules
- ✅ 7 `.delay()` dispatch sites in API routes
- ✅ TaskManager with Redis fallback for state tracking

### What's Missing (Infrastructure)
- ❌ No Celery worker process in `Dockerfile` (only gunicorn)
- ❌ No worker service in `railway.toml` / `render.yaml` / `docker-compose.yml`
- ❌ No `Procfile` for multi-process deployment
- ❌ No `REDIS_URL` in any deployment configuration
- ❌ `task_always_eager = False` (no synchronous fallback mode)

### Measured Failure Mode

Against an unreachable broker, `.delay()` **blocks ~64s then raises:**

```
RuntimeError: Retry limit exceeded while trying to reconnect to the Celery result store backend.
```

With `--workers 1 --threads 4`, four concurrent requests exhaust the thread pool for a minute.

## Affected Endpoints

### ❌ Fail with no worker (5 endpoints, no fallback)

| Endpoint | Function | File | Line | User Impact |
|---|---|---|---|---|
| `POST /api/graph/ontology/generate` | `generate_ontology_task` | graph.py | 356 | Upload completes, ontology never generates |
| `POST /api/graph/build` | `build_graph_task` | graph.py | 498 | Graph task queued, never built |
| `POST /api/report/generate` | `generate_report_task` | report.py | 197 | Report stays at 0% forever |
| `POST /api/simulation/prepare` | `prepare_simulation_task` | simulation.py | 764 | Profile generation queued, never starts |
| `POST /api/simulation/prepare` | `prepare_simulation_task` | prep_routes.py | 326 | (duplicate registration, dead code) |

**Client experience:**  
- *Broker unreachable*: 64s block → HTTP 500
- *Broker reachable, no worker*: HTTP 202 success, task queued forever at 0% progress

### ✅ Degrade gracefully (2 endpoints with fallback)

| Endpoint | Function | File | Line | Fallback Behavior |
|---|---|---|---|---|
| `POST /api/simulation/start` | `run_simulation_task` | simulation.py | 1920-1945 | Catches dispatch failure, calls `SimulationRunner.start_simulation()` in-process |
| `POST /api/simulation/start` | `run_simulation_task` | execution_routes.py | 252-276 | (duplicate registration, dead code) |

## Required Infrastructure

### 1. Redis (required for broker + result backend)

**Default config** (`app/config.py:239-241`):
```python
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
```

**Railway setup:**
1. Dashboard → Add Plugin → Redis
2. Railway auto-injects `REDIS_URL` into your service

**Render setup:**
1. Dashboard → New → Redis
2. In your web service → Environment → Add `REDIS_URL` from the Redis instance

### 2. Celery Worker Process

**Option A: Multi-process via Procfile** (Railway/Render native)

Create `Procfile` at repo root:
```
web: cd backend && exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 4 --timeout 300 --graceful-timeout 240 --access-logfile - --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' wsgi:app
worker: cd backend && exec celery -A app.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=100
```

**Railway:** Detects `Procfile` automatically  
**Render:** Set "Build Command" to empty, uses `Procfile` by default

**Option B: Separate service (Railway multi-service)**

In Railway dashboard:
1. Create new service from same repo
2. Set Root Directory: `backend`
3. Set Start Command: `celery -A app.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=100`
4. Link same `REDIS_URL` variable as web service
5. Share all env vars: `SECRET_KEY`, `LLM_API_KEY`, `ZEP_API_KEY`, etc.

**Option C: docker-compose (local/self-hosted)**

Add to `docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery-worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=100
    working_dir: /app/backend
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      # Copy all env vars from web service
      - SECRET_KEY=${SECRET_KEY}
      - LLM_API_KEY=${LLM_API_KEY}
      - ZEP_API_KEY=${ZEP_API_KEY}
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis-data:
```

Then update the `askthepeople` service:
```yaml
  askthepeople:
    # ... existing config ...
    environment:
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
```

## Worker Configuration Tuning

### Concurrency
```bash
--concurrency=2  # CPU-bound: number of CPU cores
                 # I/O-bound: 2-4× cores
                 # Memory-constrained: lower
```

**Railway Starter plan:** 512MB RAM, 0.5 vCPU shared → use `--concurrency=1`  
**Render Starter:** 512MB RAM → use `--concurrency=1`

### Task Limits
```bash
--max-tasks-per-child=100  # Recycle worker after N tasks (prevents memory leaks)
--time-limit=3600          # Hard timeout per task (seconds)
--soft-time-limit=3000     # Soft timeout for cleanup (seconds)
```

### Monitoring
```bash
celery -A app.celery_app inspect active   # Show running tasks
celery -A app.celery_app inspect stats    # Worker statistics
celery -A app.celery_app control shutdown # Graceful shutdown
```

## Verification

### 1. Check Redis connectivity
```bash
curl http://localhost:5001/health
# Should show: "redis": "ok"
```

### 2. Check worker is consuming
```bash
# In worker logs, you should see:
# [tasks]
#   . tasks.generate_ontology_task
#   . tasks.build_graph_task
#   . tasks.prepare_simulation_task
#   . tasks.run_simulation_task
#   . tasks.generate_report_task

# Then try an ontology generation and watch logs:
# [INFO/MainProcess] Task tasks.generate_ontology_task[<uuid>] received
# [INFO/ForkPoolWorker-1] Task tasks.generate_ontology_task[<uuid>] succeeded in 23.4s
```

### 3. Full smoke test
```bash
# 1. Upload files → ontology generation
curl -X POST http://localhost:5001/api/graph/ontology/generate \
  -H "Authorization: Bearer $APP_TOKEN" \
  -F "files=@test.pdf" \
  -F "simulation_requirement=Test" \
  -F "project_name=Test"

# Response should be 202 with task_id
# Poll: GET /api/graph/task/{task_id}
# Should progress from pending → processing → completed

# 2. Build graph
curl -X POST http://localhost:5001/api/graph/build \
  -H "Authorization: Bearer $APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<id>"}'

# 3. Prepare simulation
curl -X POST http://localhost:5001/api/simulation/prepare \
  -H "Authorization: Bearer $APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"simulation_id": "<id>"}'

# 4. Generate report
curl -X POST http://localhost:5001/api/report/generate \
  -H "Authorization: Bearer $APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"simulation_id": "<id>"}'

# All should return 202 and progress to completion
```

## Known Limitations (Documented, Not Blocking)

Per `docs/architecture/adr/ADR-0003-durable-run-orchestration.md`, the following are deferred to "gate 2":
- No idempotency keys (duplicate POST → duplicate task)
- No heartbeat/TTL (stalled worker → task stuck forever)
- No fencing tokens (two workers can't safely coordinate)
- No graceful cancellation (client can't abort a running task)
- No retry classification (transient vs permanent failures)

These are **design-deferred, not bugs**. The current implementation is correct for gate 1.

## Cost Estimate

**Railway:**
- Redis plugin: ~$0.50/month (included in trial)
- Worker service: Uses compute time from your plan

**Render:**
- Redis instance: $7/month (Standard 25MB)
- Worker process: Shares web service dynos (Starter includes 1 instance)

**Self-hosted:**
- Redis: negligible (runs on same VM)
- Worker: negligible (same container image)

## Alternatives Considered (Not Recommended)

### ❌ Enable `task_always_eager`
Makes `.delay()` run synchronously. Problems:
- Long tasks block request threads (ontology/graph/report take 10s-5min)
- No parallel task execution
- Defeats the entire purpose of Celery

### ❌ Remove Celery entirely
Revert to the old ThreadPoolExecutor pattern. Problems:
- Commit `c98e20e` already deleted that code
- Tasks lost on web service restart
- No task retry or monitoring
- Doesn't scale beyond 1 process

### ✅ The Right Fix: Deploy Redis + Worker
The code is already correct. Just add the infrastructure.

## Questions?

- **Do I need separate Redis for dev?** No — workers can run alongside Flask in dev; `docker-compose.yml` already has a Redis service.
- **Can I deploy without Redis first?** Yes, but the 5 endpoints will fail. Only simulation *run* will work.
- **Will this double my costs?** On Railway/Render starter plans, minimal impact. Redis is pennies, worker shares your compute quota.
- **How do I monitor tasks?** Railway/Render show worker logs in dashboard. Sentry captures exceptions. Add a `/api/tasks` route if you need realtime visibility.

---

**Bottom Line:** The app is production-ready except for this gap. Add Redis + worker, and all 7 endpoints work.
