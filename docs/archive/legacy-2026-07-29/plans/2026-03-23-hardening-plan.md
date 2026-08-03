# ASKTHEPEOPLE Hardening Plan

**Date:** 2026-03-23
**Scope:** Rate limiting, report generation timeout, CORS production config
**Status:** Superseded historical plan

> Do not use this file as current configuration guidance. Its line references,
> defaults, and “not installed” statements describe the March 2026 baseline.
> The implemented controls and remaining risks are recorded in
> [`../AUDIT-2026-07-28.md`](../AUDIT-2026-07-28.md) and
> [`../DEPLOYMENT.md`](../DEPLOYMENT.md).

---

## Phase 0 — Documentation Discovery (COMPLETE)

### Allowed APIs & Confirmed Signatures

#### Report Generation (report.py)

- Background thread launched at `backend/app/api/report.py:191-193`
- `generate_report()` signature: `def generate_report(self, progress_callback=None, report_id=None) -> Report`
  — located at `backend/app/services/report_agent.py:1588`
- LLM call loop (per-section ReACT): `report_agent.py:1350-1586` — up to 5 iterations × N sections = 16–26 LLM calls per report
- Timeout approach: `concurrent.futures.ThreadPoolExecutor.future.result(timeout=seconds)`
  — works on Windows, is already the pattern used elsewhere in Python stdlib
- Config key for LLM per-call timeout already exists: `Config.LLM_TIMEOUT = 120` (`config.py:34`)
- Task status tracking in `run_generate()`: lines 144–164 of `report.py`

#### Flask-Limiter

- **Not installed** — must be added to `backend/pyproject.toml`
- `create_app()` extension init pattern: CORS added at line 54, blueprints registered at 103–106
- Limiter must be initialized in `create_app()` and exposed so blueprints can import it
- Blueprint files follow identical import pattern: `from . import <name>_bp` then decorators on routes

#### High-Risk Endpoints (confirmed with file:line)

| Risk | Endpoint | File:Line |
|------|----------|-----------|
| CRITICAL | `POST /api/report/generate` | `report.py:42` |
| CRITICAL | `POST /api/report/chat` | `report.py:610` |
| HIGH | `POST /api/graph/ontology/generate` | `graph.py:121` |
| HIGH | `POST /api/simulation/prepare` | `simulation.py:376` |
| MEDIUM | `POST /api/simulation/create` | `simulation.py:170` |
| MEDIUM | `POST /api/graph/build` | `graph.py:259` |
| MEDIUM | `POST /api/simulation/generate-profiles` | `simulation.py:1460` |

### Anti-Patterns to Avoid

- Do NOT use `signal.alarm()` for timeout — not supported on Windows
- Do NOT apply `@limiter.limit()` from a blueprint-level import — must use the `limiter` instance from `app/__init__.py` (or from `app/api/__init__.py`)
- Do NOT use `storage_uri="redis://"` unless Redis is available — use `"memory://"` for single-process

---

## Phase 1 — Report Generation Wall-Clock Timeout

### What to implement

Wrap the `agent.generate_report()` call inside the background thread (`report.py:142`) with a `ThreadPoolExecutor` timeout. If generation exceeds `REPORT_GENERATION_TIMEOUT` seconds, mark the task as failed with a clear error message.

### Files to modify

1. `backend/app/config.py` — add `REPORT_GENERATION_TIMEOUT`
2. `backend/app/api/report.py` — wrap the generate call in `concurrent.futures`

### Step-by-step

**Step 1.1 — Add config key (`config.py`)**

```python
# After REPORT_AGENT_TEMPERATURE line
REPORT_GENERATION_TIMEOUT = int(os.environ.get('REPORT_GENERATION_TIMEOUT', '900'))  # 15 minutes
```

**Step 1.2 — Wrap generate call (`report.py`)**

Find the `run_generate()` inner function (around line 142). The current pattern is:

```python
# CURRENT (no timeout):
report = agent.generate_report(
    progress_callback=update_progress,
    report_id=report_id
)
```

Replace with:

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# NEW (with wall-clock timeout):
timeout_secs = Config.REPORT_GENERATION_TIMEOUT
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(
        agent.generate_report,
        update_progress,
        report_id
    )
    try:
        report = future.result(timeout=timeout_secs)
    except FuturesTimeoutError:
        task_manager.fail_task(
            task_id,
            f"Report generation exceeded the {timeout_secs}s time limit"
        )
        return
```

**Step 1.3 — Verify**

- Read `report.py` around the modified section to confirm structure is intact
- Grep for `FuturesTimeoutError` to confirm it's imported and used
- Check that `task_manager.fail_task()` is already imported in `report.py`

### Verification checklist

- [ ] `Config.REPORT_GENERATION_TIMEOUT` exists and defaults to 900
- [ ] `concurrent.futures` imported in `report.py`
- [ ] `future.result(timeout=...)` wraps the `generate_report()` call
- [ ] `fail_task()` is called on timeout with a descriptive message
- [ ] No change to the progress callback signature

### Anti-pattern guards

- Do NOT import `signal` — not needed and not Windows-safe
- Do NOT change `generate_report()` internals — wrap at the call site only

---

## Phase 2 — Rate Limiting

### What to implement

Install Flask-Limiter, initialize it in `create_app()`, and apply per-route limits on the 7 high-risk endpoints.

### Files to modify

1. `backend/pyproject.toml` — add dependency
2. `backend/app/api/__init__.py` — expose limiter instance
3. `backend/app/__init__.py` — initialize Limiter in `create_app()`
4. `backend/app/api/graph.py` — decorate 2 routes
5. `backend/app/api/simulation.py` — decorate 3 routes
6. `backend/app/api/report.py` — decorate 2 routes
7. `backend/app/config.py` — add rate limit config keys

### Step-by-step

**Step 2.1 — Add dependency (`pyproject.toml`)**

```toml
"flask-limiter>=3.5.0",
```

Add after `flask-cors>=6.0.0`.

**Step 2.2 — Add config keys (`config.py`)**

```python
# Rate Limiting
RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day;50 per hour')
RATELIMIT_LLM_HEAVY = os.environ.get('RATELIMIT_LLM_HEAVY', '10 per hour')
RATELIMIT_LLM_MEDIUM = os.environ.get('RATELIMIT_LLM_MEDIUM', '20 per hour')
```

**Step 2.3 — Initialize Limiter in `create_app()` (`__init__.py`)**

Import at top of file:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
```

Add after the CORS line (line 54):

```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config.get('RATELIMIT_DEFAULT', '200 per day;50 per hour')],
    storage_uri="memory://",
)
app.extensions['limiter'] = limiter
```

**Step 2.4 — Expose limiter in `api/__init__.py`**

After `current_app` is available, blueprints get the limiter via:

```python
from flask import current_app

def get_limiter():
    return current_app.extensions['limiter']
```

Add this helper to `backend/app/api/__init__.py`.

**Step 2.5 — Decorate high-risk routes**

In each blueprint file, add at the top of the route handler:

`graph.py` — `generate_ontology` (line 121) and `build_graph` (line 259):

```python
@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    get_limiter().limit(Config.RATELIMIT_LLM_HEAVY)(lambda: None)()
    ...
```

**Simpler pattern** using the limiter directly via `current_app`:

```python
from flask import current_app

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    limiter = current_app.extensions['limiter']
    # OR: decorate at registration time — see Flask-Limiter docs on blueprints
```

**Recommended approach — decorate at route level using `limiter` from `app/api/__init__.py`:**

In `backend/app/api/__init__.py`:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# This is populated during create_app() — see __init__.py
limiter = Limiter(key_func=get_remote_address)
```

Then in `create_app()` call `limiter.init_app(app)` instead of `Limiter(app=app, ...)`.

In each blueprint:

```python
from . import graph_bp, limiter

@graph_bp.route('/ontology/generate', methods=['POST'])
@limiter.limit("10 per hour")
def generate_ontology():
    ...
```

**Step 2.6 — Verify**

```bash
cd backend && uv add flask-limiter
python -c "from app import create_app; app = create_app(); print(app.extensions.get('limiter'))"
```

### Verification checklist

- [ ] `flask-limiter` in `pyproject.toml`
- [ ] `Limiter` initialized in `create_app()`
- [ ] All 7 high-risk endpoints have `@limiter.limit(...)` decorator
- [ ] `RATELIMIT_LLM_HEAVY` and `RATELIMIT_LLM_MEDIUM` in Config
- [ ] 429 response returned when limit exceeded (manual test or unit test)

### Anti-pattern guards

- Do NOT use `storage_uri="redis://"` (Redis not installed)
- Do NOT apply limits as `default_limits` only — critical routes need explicit limits
- Do NOT skip the `limiter.init_app(app)` step if using the blueprint pattern

---

## Phase 3 — CORS Production Hardening

### What to implement

Replace `origins: "*"` with an allowlist read from environment. During development the default remains `*`; in production, set `CORS_ORIGINS` to your frontend domain.

### Files to modify

1. `backend/app/config.py` — add `CORS_ORIGINS`
2. `backend/app/__init__.py` — use config value in CORS init

### Step-by-step

**Step 3.1 — Add config key (`config.py`)**

```python
# CORS — comma-separated list of allowed origins, or * for development
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
```

**Step 3.2 — Use in `__init__.py`**

Current (line 54):

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

Replace with:

```python
cors_origins = app.config.get('CORS_ORIGINS', '*')
origins_list = [o.strip() for o in cors_origins.split(',')] if cors_origins != '*' else '*'
CORS(app, resources={r"/api/*": {"origins": origins_list}})
```

**Step 3.3 — Document in `.env.example`**

```bash
# Allowed frontend origins (comma-separated, or * for dev)
# CORS_ORIGINS=https://yourapp.com,https://www.yourapp.com
```

### Verification checklist

- [ ] `Config.CORS_ORIGINS` defaults to `'*'`
- [ ] CORS initialized with the resolved origins list
- [ ] With `CORS_ORIGINS=*`, API still accessible from any origin (dev compat)
- [ ] With `CORS_ORIGINS=https://example.com`, cross-origin requests from other domains return 403

### Anti-pattern guards

- Do NOT hardcode domain names in source code — always env var
- Do NOT split `*` by comma (it's a single wildcard token)

---

## Phase 4 — Final Verification

### Checks

1. **Import verification:** `python -c "from app import create_app; app = create_app()"` — no import errors
2. **Timeout active:** Grep `concurrent.futures` in `report.py` — should appear
3. **Limiter active:** Grep `limiter.limit` in `graph.py`, `simulation.py`, `report.py`
4. **CORS config:** Grep `Config.CORS_ORIGINS` in `__init__.py`
5. **No regressions:** Run existing tests with `cd backend && uv run pytest`

### Anti-pattern guards

- Do NOT merge if any grep check above returns no results
- Do NOT skip the import check — Flask extension init errors are silent if not caught early
