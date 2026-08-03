---
title: "Harvest Framework Engineering Fixes"
status: "Proposed"
version: "1.0.0"
owner: "askthepeople-architect + askthepeople-persistence-engineer"
created: "2026-08-02"
last_reviewed: "2026-08-03"
gate: "Gate 1-3 accelerators"
baseline_commit: "67cd5484cb7b2dab22b6d134622cf9793b9c4e5d"
research_source: "ASKTHEPEOPLE_SOCIAL_FORECASTING_MASTER_FRAMEWORK_2026.md"
---

# Harvest Framework Engineering Fixes

## Purpose

The Social Forecasting Framework (dated 2026-08-02, baseline `9593e93`) identified five
engineering defects in the current repo that are **product-direction-neutral** — they block
progress whether we remain a synthetic-only engine or later expand to real data and forecasting.

This plan extracts only those fixes. It does NOT adopt the framework's product vision (real
Reddit data, forecasting, backtesting). It preserves the current Product Truth Contract and
synthetic-only positioning.

## Authority

This plan is subordinate to:
- [`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../product/PRODUCT_TRUTH_CONTRACT.md)
- [`docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md)
- [`docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md`](../architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md)

## Five Verified Defects

### 1. Dual SQLAlchemy bases with missing async drivers

**CURRENT:** Two declarative bases exist:
- Sync: `backend/app/db/schema.py:4-6` (dormant)
- Async: `backend/app/db/models/__init__.py:6-8` (active, used by all 6 models)

`backend/app/db/database.py:27-33` constructs `sqlite+aiosqlite://` and `postgresql+asyncpg://`
URLs, but `pyproject.toml` includes neither `aiosqlite` nor `asyncpg`. The async path cannot
import its driver.

**IMPACT:** Database initialization will fail when async path is triggered. Silent today only
because the graceful fallback (defect #3) hides it.

### 2. Eval results writer produces contradictory counts

**CURRENT:** `backend/tests/evals/results.json` reports:
```json
{
  "_test_summary": {
    "total_tests": 5,
    "passed": 52,
    "failed": 8,
    "exit_status": 1
  }
}
```

`passed + failed = 60`, but `total_tests = 5`. The cause is in
`backend/tests/evals/conftest.py:165-170`: `total_tests` counts only tests whose path contains
`evals`, while `passed`/`failed` are summed from the full pytest session.

**IMPACT:** Eval evidence is untrustworthy. Cannot use `results.json` to support any quality
claim in a release bundle.

### 3. Production falls back to filesystem when DB unavailable

**CURRENT:** `backend/app/__init__.py:160-173` catches database-init exceptions, logs a warning,
and continues:
```python
except Exception as db_error:
    logger.warning(
        f"Database initialization failed: {str(db_error)}. "
        "Falling back to filesystem storage.",
        ...
    )
    # Application continues with filesystem-based storage
```

**IMPACT:** Production deployment silently degrades to JSON files when PostgreSQL is
misconfigured or unreachable. State is lost across restarts. Multi-worker coordination fails.

### 4. Follower/karma counts violate truth contract

**CURRENT:** `backend/app/services/oasis_profile_generator.py:250-253` fabricates social-graph
metrics via unconstrained `random.randint`:
```python
karma=profile_data.get("karma", random.randint(500, 5000)),
friend_count=profile_data.get("friend_count", random.randint(50, 500)),
follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
```

None of these fields are requested from the LLM. All fall through to `random.randint`. Then
`backend/app/services/archetype_engine.py:252-306` clones these numbers across the population
with 7–13% jitter (`random.uniform(0.7, 1.3)`).

**CONTRAST:** Demographic fields (`age`, `gender`, `mbti`, `country`) use disciplined neutral
placeholders (`age=30`, `gender="other"`, `mbti="ISTJ"`) when source material is silent, per
`oasis_profile_generator.py:66-69` and the prompt at
`backend/app/prompts/definitions/profile_generation_v1.yaml:27-38`.

**IMPACT:** Truth-contract violation. Fabricated follower counts appear quantitative but are
ungoverned random integers with no "fictional, non-quantitative" disclosure comparable to
demographic placeholders. Exposed in exports and reports as if meaningful.

### 5. Location header points at non-existent `/api/jobs/{id}`

**CURRENT:** `backend/app/api/routes/prep_routes.py:359` returns:
```python
return jsonify({...}), 202, {"Location": f"/api/jobs/{task_id}"}
```

No `/api/jobs/{id}` endpoint exists. The actual endpoints are
`/api/graph/task/<task_id>` and `/api/simulation/task/<task_id>/status`, which are
blueprint-specific and return identical structures.

**IMPACT:** HTTP 202 / Location contract is broken. Clients following the `Location` header
receive a 404.

---

## Fix 1: Collapse to One SQLAlchemy Path

### Decision

Use **synchronous SQLAlchemy 2 + psycopg** for the current Flask application.

### What Actually Runs Today

**Verified 2026-08-02:**

- `app/__init__.py:162-164` calls `from .db.database import init_db` (async path)
- `app/api/health.py:14` imports `from app.db.database import get_db_session` (async)
- **BUT:** `health.py:16` uses synchronous `with get_db_session()` instead of `async with`, which would fail at runtime. The broad `except Exception` at `:20` catches it and returns `True` anyway, so the health check is fake.
- **AND:** Zero ORM usage anywhere in `app/api/` or `app/services/` — no `session.query`, `session.add`, `session.commit`. All real persistence is via filesystem JSON (`ProjectManager`, `SimulationManager`) and Redis.

**Result:** The async database layer is wired into app init but (a) cannot initialize (missing drivers), (b) is never used by any request handler, and (c) the health check that pretends to test it is broken.

The sync database layer (`db/__init__.py`, `db/schema.py`) exists but is completely unreachable — nothing imports it.

### Rationale for Sync

- Flask request handlers are synchronous today (no `async def`).
- Celery tasks are synchronous.
- The async models (`db/models/`) are defined but unreachable (engine can't initialize).
- The ORM is scaffolding only — no route or service uses it for real data.
- Adding `aiosqlite` / `asyncpg` fixes the import but leaves architectural mismatch (async SQLAlchemy in a sync WSGI app).
- ADR-0012 mandates PostgreSQL as canonical; SQLite is dev/test only.

### Changes

#### 1.1 Install production driver

**FILE:** `backend/pyproject.toml`

```diff
dependencies = [
    ...
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
-   "psycopg2-binary>=2.9.9",
+   "psycopg[binary]>=3.2.0",  # PostgreSQL driver for SQLAlchemy 2 sync
    ...
]
```

**RATIONALE:** `psycopg` 3.x is the maintained driver; `psycopg2-binary` is legacy.

#### 1.2 Delete async database infrastructure

**FILES TO DELETE:**
- `backend/app/db/database.py` (async engine, `create_async_engine`, `async_sessionmaker`)
- `backend/app/db/models/__init__.py` (async `Base(AsyncAttrs, DeclarativeBase)`)
- All 6 model files in `backend/app/db/models/` (`project.py`, `simulation.py`, `graph.py`,
  `source.py`, `ontology.py`, `report.py`)

**KEEP:**
- `backend/app/db/schema.py` (sync `Base = declarative_base()`)
- `backend/app/db/__init__.py` (sync engine + `sessionmaker`)

#### 1.3 Rewrite models as synchronous SQLAlchemy 2

**NEW FILE:** `backend/app/db/models.py`

Define all canonical models here (Project, Simulation, Task, etc.) using the sync Base from
`db/schema.py`. Import from `db/__init__.py` for the sync engine.

**ACCEPTANCE:**
- One `Base` class.
- One `create_engine` call.
- One `sessionmaker`.
- Alembic `env.py` imports `Base` and sees all models.
- No `async def` in model layer.

#### 1.4 Update config to remove async URL construction

**FILE:** `backend/app/config.py`

Remove lines 239-243 (the `postgres://` → `postgresql+asyncpg://` conversion). Use
`postgresql://` or `postgresql+psycopg://` for PostgreSQL.

#### 1.5 Rewire app initialization to use sync path

**FILE:** `backend/app/__init__.py`

**LINES 162-164:** Replace:
```python
from .db.database import init_db
```

With:
```python
from .db import get_engine, init_db
```

Then call:
```python
engine = get_engine(database_url)
init_db(engine)
```

#### 1.6 Fix health check to use sync session

**FILE:** `backend/app/api/health.py`

**CURRENT PROBLEM:** Line 16 uses `with get_db_session()` (sync context manager) on an async
context manager, which fails. The broad `except` at line 20 always returns `True`, making the
check fake.

**LINES 11-22:** Replace entire `check_database()`:

```python
def check_database():
    """Check database connectivity (PostgreSQL or SQLite)"""
    try:
        from app.db import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        # Database not configured or not available
        return False  # Report actual state instead of always True
```

**CHANGE:** Return `False` on failure instead of `True`. Let the health endpoint report `degraded`
when DB is unreachable.

---

## Fix 2: Eval Results Writer Consistency

### Changes

#### 2.1 Rewrite `_test_summary` logic

**FILE:** `backend/tests/evals/conftest.py`

**CURRENT PROBLEM:** Lines 165-170 count `eval_tests` (filtered) for `total_tests` but sum
`self.test_outcomes` (all tests) for `passed` / `failed`.

**FIX:**

```python
@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(self, session, exitstatus):
    """Write eval results after session"""
    results_file = self.results_dir / "results.json"
    
    # Count only eval tests (path contains 'evals')
    eval_tests = [
        item for item in session.items 
        if 'evals' in str(item.fspath)
    ]
    
    # Filter outcomes to eval tests only
    eval_test_ids = {item.nodeid for item in eval_tests}
    eval_outcomes = {
        nodeid: outcome 
        for nodeid, outcome in self.test_outcomes.items() 
        if nodeid in eval_test_ids
    }
    
    passed = sum(1 for o in eval_outcomes.values() if o == 'passed')
    failed = sum(1 for o in eval_outcomes.values() if o == 'failed')
    skipped = sum(1 for o in eval_outcomes.values() if o == 'skipped')
    
    total = len(eval_test_ids)
    
    # Sanity check
    assert passed + failed + skipped == total, \
        f"Eval count mismatch: {passed}+{failed}+{skipped} != {total}"
    
    results = {
        "_test_summary": {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "exit_status": exitstatus,
        },
        # ... metrics
    }
    
    results_file.write_text(json.dumps(results, indent=2))
```

#### 2.2 Add metrics persistence

**CURRENT PROBLEM:** `results.json` contains only `_test_summary`, no actual eval metrics.

**FIX:** In the same hook, iterate over `eval_tests` and extract metrics from test metadata or
store them in `self.eval_metrics` during `pytest_runtest_logreport` (when outcome is `passed`).

**ACCEPTANCE:**
- `total_tests == passed + failed + skipped`
- `exit_status == 0` when all eval tests pass
- Metrics are present (not just the summary)
- CI can parse and validate the file

---

## Fix 3: Fail Closed on Database Unavailability

### Changes

#### 3.1 Remove silent fallback in production

**FILE:** `backend/app/__init__.py`

**CURRENT:** Lines 160-173 catch DB errors and continue.

**FIX:**

```python
# Initialize database connection (fail closed in production)
try:
    from .db import init_db
    init_db()
    logger.info("Database initialized successfully")
except Exception as db_error:
    if app.config.get("ENV") == "production":
        logger.critical(
            f"Database initialization failed in production: {str(db_error)}. "
            "Refusing to start. Check DATABASE_URL and connectivity."
        )
        raise RuntimeError("Database required in production") from db_error
    else:
        logger.warning(
            f"Database initialization failed in development: {str(db_error)}. "
            "Falling back to filesystem storage."
        )
        # Fallback allowed in dev/test only
```

#### 3.2 Add DATABASE_URL presence check

**FILE:** `backend/app/config.py`

```python
@property
def DATABASE_URL(self) -> str:
    url = os.environ.get("DATABASE_URL")
    if self.ENV == "production" and not url:
        raise RuntimeError(
            "DATABASE_URL is required in production. "
            "Set it to a PostgreSQL connection string."
        )
    return url or "sqlite:///./askthepeople_dev.db"
```

**ACCEPTANCE:**
- Production start fails loudly when `DATABASE_URL` is unset or DB is unreachable
- Dev/test may fall back to filesystem (local iteration convenience)
- Health check (`/health`) reports DB status accurately

---

## Fix 4: Follower/Karma Count Truth Compliance

### Decision

**Option A (RECOMMENDED):** Omit ungoverned counts. Only include `karma`, `follower_count`,
`friend_count`, `statuses_count` when they are **explicitly derived from source material**.

**Option B:** Keep them but tag as `"fictional_non_quantitative"` everywhere they appear, with
the same disclosure rigor as demographic placeholders.

We choose **Option A** — omission is cleaner than proliferating fictional numbers.

### Changes

#### 4.1 Remove random fallbacks

**FILE:** `backend/app/services/oasis_profile_generator.py`

**LINES 250-253:** Replace:

```python
karma=profile_data.get("karma", random.randint(500, 5000)),
friend_count=profile_data.get("friend_count", random.randint(50, 500)),
follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
```

With:

```python
karma=profile_data.get("karma"),  # None if not source-derived
friend_count=profile_data.get("friend_count"),
follower_count=profile_data.get("follower_count"),
statuses_count=profile_data.get("statuses_count"),
```

#### 4.2 Update dataclass to allow None

**FILE:** `backend/app/services/oasis_profile_generator.py`

**LINES 28-57:** Update `OasisAgentProfile`:

```python
@dataclass
class OasisAgentProfile:
    ...
    karma: int | None = None
    friend_count: int | None = None
    follower_count: int | None = None
    statuses_count: int | None = None
    ...
```

#### 4.3 Update clone expansion to preserve None

**FILE:** `backend/app/services/archetype_engine.py`

**LINES 276-283:** Replace jitter logic:

```python
# Only jitter if base value exists and is source-derived
karma = (
    int(base_profile.karma * random.uniform(0.7, 1.3))
    if base_profile.karma is not None
    else None
)
follower_count = (
    int(base_profile.follower_count * random.uniform(0.7, 1.3))
    if base_profile.follower_count is not None
    else None
)
# ... same for friend_count, statuses_count
```

#### 4.4 Update export/report logic to handle None

**FILES:** 
- `backend/app/services/export_service.py`
- `backend/app/services/report_agent.py`

When serializing profiles, render `None` counts as `"not observed"` or omit the field entirely.
Do not render as `0` (which implies measurement).

**ACCEPTANCE:**
- No `random.randint` fallback for social-graph counts
- Profiles derived from source material MAY have these counts (if the source provided them)
- Profiles without source grounding have `None` for all four counts
- Exports/reports omit or label them as `"not observed"`
- CI linter passes (no new prohibited language introduced)

---

## Fix 5: Canonical `/api/jobs/{id}` Endpoint

### Decision

Create a unified job-status endpoint at `/api/jobs/{task_id}` that works for all task types.
Preserve existing blueprint-specific endpoints for backward compatibility but mark them
deprecated.

### Changes

#### 5.1 New jobs blueprint

**NEW FILE:** `backend/app/api/jobs.py`

```python
from flask import Blueprint, jsonify
from ..models.task import TaskManager

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

@jobs_bp.route("/<task_id>", methods=["GET"])
def get_job_status(task_id: str):
    """
    Canonical job-status endpoint.
    
    Returns task state for any background job (graph build, preparation, execution).
    This is the endpoint referenced in HTTP 202 Location headers.
    """
    task_manager = TaskManager.get_instance()
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": "task_not_found",
            "message": f"No task with ID {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "job": task.to_public_dict()
    }), 200
```

#### 5.2 Register blueprint

**FILE:** `backend/app/__init__.py`

```python
from .api.jobs import jobs_bp
app.register_blueprint(jobs_bp)
```

#### 5.3 Update Location headers

**FILE:** `backend/app/api/routes/prep_routes.py:359` (and any other 202 responses)

Already correct — `Location: /api/jobs/{task_id}` now resolves.

#### 5.4 Mark old endpoints deprecated

**FILES:** 
- `backend/app/api/graph.py:522,542`
- `backend/app/api/routes/execution_routes.py:582`

Add deprecation headers:

```python
response.headers["Deprecation"] = "true"
response.headers["Link"] = f'</api/jobs/{task_id}>; rel="alternate"'
```

**ACCEPTANCE:**
- `GET /api/jobs/{task_id}` returns task state for any task type
- HTTP 202 `Location` headers resolve successfully
- Old endpoints work but carry `Deprecation: true` header
- OpenAPI/docs updated

---

## Implementation Order

1. **Fix 1 (DB stack)** — Blocks everything else; do first
2. **Fix 5 (jobs endpoint)** — Quick win; unblocks HTTP 202 contract
3. **Fix 3 (fail closed)** — Requires Fix 1 complete; production safety
4. **Fix 4 (follower counts)** — Independent; truth-contract compliance
5. **Fix 2 (eval writer)** — Independent; evidence quality

## Acceptance Criteria

### Fix 1: DB Stack
- [ ] One `Base` class in `backend/app/db/schema.py`
- [ ] No `db/database.py` or `db/models/` directory
- [ ] `psycopg[binary]>=3.2.0` in `pyproject.toml`
- [ ] No async DB URL construction in `config.py`
- [ ] Alembic migration runs successfully
- [ ] All models import from the sync Base

### Fix 2: Eval Writer
- [ ] `results.json` totals are internally consistent
- [ ] `passed + failed + skipped == total_tests`
- [ ] `exit_status` matches pytest exit code
- [ ] Metrics are present (not just summary)
- [ ] CI can parse and validate

### Fix 3: Fail Closed
- [ ] Production start fails when `DATABASE_URL` is unset
- [ ] Production start fails when DB connection fails
- [ ] Dev/test may fall back (logged warning)
- [ ] Health check reports DB state accurately

### Fix 4: Follower Counts
- [ ] No `random.randint` for `karma`, `follower_count`, `friend_count`, `statuses_count`
- [ ] Dataclass fields allow `None`
- [ ] Clone expansion preserves `None` (does not fabricate)
- [ ] Exports omit or label `None` as `"not observed"`
- [ ] CI linter passes

### Fix 5: Jobs Endpoint
- [ ] `GET /api/jobs/{task_id}` returns 200 + task state
- [ ] HTTP 202 `Location` header resolves successfully
- [ ] Old endpoints return `Deprecation: true` header
- [ ] OpenAPI docs updated

## Test Plan

### Fix 1
- Unit: sync models round-trip through PostgreSQL
- Integration: Alembic upgrade/downgrade
- Deployment: Railway worker starts with `DATABASE_URL` set

### Fix 2
- Run `pytest backend/tests/evals/` and verify `results.json` is consistent
- Inject a failing eval and confirm `exit_status: 1`

### Fix 3
- Set `ENV=production` with no `DATABASE_URL` → start fails
- Set `ENV=production` with bad `DATABASE_URL` → start fails
- Set `ENV=development` with no `DATABASE_URL` → start succeeds (warning logged)

### Fix 4
- Generate profile with no source material → `karma` is `None`
- Expand archetype with `karma=None` → all variants have `karma=None`
- Export run → CSV/JSON omits or labels ungoverned counts as `"not observed"`

### Fix 5
- `POST /api/simulation/prepare` → returns `202` with `Location: /api/jobs/{id}`
- `GET /api/jobs/{id}` → returns task state
- `GET /api/graph/task/{id}` → returns `Deprecation: true` header

## Rollback Plan

Each fix is independently reversible:

1. **DB stack:** Restore `db/database.py`, `db/models/`, and `psycopg2-binary`
2. **Eval writer:** Revert `conftest.py` changes
3. **Fail closed:** Restore `try/except` fallback in `__init__.py`
4. **Follower counts:** Restore `random.randint` fallback
5. **Jobs endpoint:** Delete `api/jobs.py` blueprint

## Migration Notes

### For users with existing runs

**Fixes 1, 2, 3, 5:** No user-visible change. Backend only.

**Fix 4:** Existing serialized profiles with fabricated `karma`/`follower_count` remain as-is in
old runs. New runs will have `None` for these fields. Exports should handle both.

### For API clients

**Fix 5:** Clients using `/api/graph/task/{id}` or `/api/simulation/task/{id}/status` continue
to work. They should migrate to `/api/jobs/{id}` before the next major version.

## Timeline Estimate

| Fix | Effort | Dependencies |
|---|---|---|
| 1. DB stack | 2-3 days | None |
| 5. Jobs endpoint | 1 day | None |
| 3. Fail closed | 1 day | Fix 1 |
| 4. Follower counts | 1-2 days | None |
| 2. Eval writer | 1 day | None |

**Total:** 6-8 days for implementation + testing.

## What This Does NOT Do

This plan does NOT:
- Add real Reddit/social data collection
- Add backtesting or forecast validation
- Add data-rights contracts or deletion sync
- Change the Product Truth Contract
- Add statistical behavioral policies (LLM still generates personas end-to-end, we just omit
  ungoverned counts)
- Add immutable dataset snapshots
- Add `available_at` timestamps or leakage controls

Those are the **Social Forecasting Framework** additions. They require a separate product
decision and are out of scope here.

## References

- Source: `ASKTHEPEOPLE_SOCIAL_FORECASTING_MASTER_FRAMEWORK_2026.md`
- Verification: Agent sweeps completed 2026-08-02
- Current baseline: `67cd5484cb7b2dab22b6d134622cf9793b9c4e5d`
- ADR-0012: [Canonical Transactional and Object Persistence](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md)
- ADR-0011: [Incremental Modernization over Rewrite](../architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md)
