---
title: "Architecture Overview — ASKTHEPEOPLE"
status: "Normative"
version: "1.1.0"
owner: "Architect + Security + Persistence + Orchestration"
last_reviewed: "2026-07-29"
review_cycle: "Per gate; at minimum quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §1–§6"
---

# Architecture overview

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.

This document is the project-specific architecture entry point for
**ASKTHEPEOPLE / Synthetic Decision Explorer** at the current implementation
baseline. It is derived from the actual code under
[`backend/app/`](../../backend/app/) and the integration audit recorded in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md).
The target state described in the original audit and in
[`data-model.md`](data-model.md) / [`state-machines.md`](state-machines.md) is
still aspirational; current-versus-target divergences are listed explicitly so
that no PR can claim the target without an acceptance-evidence bundle.

## State legend used in this document

- **CURRENT** — implemented and verified at the baseline commit
  `8b616dc7fa02eeed5ada8c51998d8b197be28f8d` on `main`.
- **PARTIAL** — implemented but materially deficient; a release-blocker finding
  is open against the implementation. Cites the audit section.
- **TARGET** — approved production design that the implementation has not
  reached. Implementation is recorded against the corresponding ADR.
- **TRANSITION** — work required to move from CURRENT/PARTIAL to TARGET.
  Tracked in [`docs/exec-plans/`](../exec-plans/README.md).

## System at a glance

```text
                                  ┌────────────────────────────┐
   Vue 3 / Vite frontend  ───────►│  Flask app (single process)│
   (frontend/dist served by        │  app/__init__.py:25-330   │
    app/__init__.py:317-325)       │                            │
                                   │  Blueprints (api/__init__.py:13-17)│
                                   │   /api/auth       auth_bp           │
                                   │   /api/graph      graph_bp (29 KB)  │
                                   │   /api/simulation simulation_bp (130 KB) ─── P0/P1 cluster
                                   │   /api/report     report_bp  (48 KB)│
                                   │   /api/settings   settings_bp        │
                                   │   WebSocket       api/ws.py (flask-sock)│
                                   └────────────┬───────────────────────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       │                        │                        │
              ┌────────▼────────┐       ┌────────▼────────┐       ┌───────▼────────┐
              │  SQLite/JSONL   │       │  Filesystem     │       │  Redis         │
              │  state.json     │       │  uploads/       │       │  broker, cache,│
              │  per simulation │       │  projects/,     │       │  task state,   │
              │  (CURRENT)      │       │  simulations/,  │       │  rate limit    │
              │                 │       │  reports/       │       │  (CURRENT)     │
              └─────────────────┘       │  (CURRENT)      │       └────────────────┘
                                        └─────────────────┘
                                                ▲
                                                │  SimulationRunner (services/simulation_runner.py, 82 KB)
                                                │  IPC: simulation_ipc.py
                                                │  invoked by:
                                                │   • Celery task app/tasks/simulation_tasks.py
                                                │   • in-process daemon thread (P0)
                                                │
                                                ▼
                                        OASIS / CAMEL runtime
                                        (python subprocess or in-process)
```

## HTTP layer — CURRENT

The Flask application is created by [`create_app()`](../../backend/app/__init__.py:25).
The route responsibility contract is
[`auth → parse → authorize → dispatch → present`](../..//ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#7-correct-target-architecture).
Current implementation of that contract is **PARTIAL**: most routes handle all
five steps inline and additionally start threads, open SQLite, scan report
directories, and build exports.

### Blueprints

| URL prefix | Blueprint | File | Size | Status |
|---|---|---|---:|---|
| `/api/auth` | `auth_bp` | [`api/auth.py`](../../backend/app/api/auth.py) | 1 KB | CURRENT |
| `/api/graph` | `graph_bp` | [`api/graph.py`](../../backend/app/api/graph.py) | 29 KB | CURRENT |
| `/api/simulation` | `simulation_bp` | [`api/simulation.py`](../../backend/app/api/simulation.py) | 130 KB | **PARTIAL** — release-blocker; see audit §5 P0/P1 cluster |
| `/api/report` | `report_bp` | [`api/report.py`](../../backend/app/api/report.py) | 48 KB | CURRENT (route layer) |
| `/api/settings` | `settings_bp` | [`api/settings.py`](../../backend/app/api/settings.py) | 13 KB | CURRENT |
| WebSocket | (none — registered in [`api/ws.py`](../../backend/app/api/ws.py)) | `api/ws.py` | 10 KB | CURRENT |

`simulation_bp` is the 3,526-line, 54-function, 41-route controller identified
by the integration audit. Decomposition is the
[`askthepeople-architect`](../..//README.md) agent's primary deliverable per
[`docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md`](adr/ADR-0011-incremental-modernization-over-rewrite.md).

### Authentication and security headers — CURRENT

All implemented at the request/response seam in
[`create_app()`](../../backend/app/__init__.py:25):

- Bearer-token auth on every `/api/*` route when `APP_TOKEN` is set
  ([`require_auth` middleware](../../backend/app/__init__.py:125-141));
  constant-time comparison via [`hmac.compare_digest`](../../backend/app/__init__.py:140).
- Production CORS lockdown: `CORS_ORIGINS='*'` is refused in production and
  replaced with `http://127.0.0.1`
  ([`create_app` CORS branch](../../backend/app/__init__.py:74-82)).
- Security response headers (production only):
  Content-Security-Policy, X-Content-Type-Options: nosniff, X-Frame-Options:
  DENY, Referrer-Policy: no-referrer, Permissions-Policy with all sensitive
  features disabled, Cross-Origin-Opener-Policy: same-origin,
  Cross-Origin-Resource-Policy: same-origin, and HSTS when forwarded-proto is
  https
  ([`apply_security_headers` after-request hook](../../backend/app/__init__.py:149-196)).
- `Cache-Control: no-store` for `/api/*` and `/health`
  ([`create_app` after-request](../../backend/app/__init__.py:193-195)).
- Production stripping of `traceback` and 5xx `error` strings
  ([`strip_traceback_in_production` after-request](../../backend/app/__init__.py:198-226)).
- No request body logging in any debug path
  ([`log_request` before-request](../../backend/app/__init__.py:111-123)).
- `SafePathError` → `400 {"success": false, "error": "invalid_id"}`
  ([`create_app` error handler](../../backend/app/__init__.py:263-267)).
- `RateLimitExceeded` → `429 {"success": false, "error": "rate_limit_exceeded"}`
  ([`create_app` error handler](../../backend/app/__init__.py:254-261)).
- In-memory rate limiter (CURRENT); Redis-backed rate limiter is **TARGET** per
  [`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](adr/ADR-0012-canonical-transactional-and-object-persistence.md).

## State and persistence — CURRENT and TARGET

### Project aggregate — CURRENT

Source: [`backend/app/models/project.py`](../../backend/app/models/project.py).

The `Project` dataclass is persisted as JSON at
`backend/uploads/projects/{project_id}/project.json`. Lifecycle is a 5-state
enum defined in [`models/project.py:18-25`](../../backend/app/models/project.py:18):

```text
CREATED → ONTOLOGY_GENERATED → GRAPH_BUILDING → GRAPH_COMPLETED
                                                       │
                                                       ▼
                                                    FAILED
```

`ProjectManager` ([`models/project.py:102-310`](../../backend/app/models/project.py:102))
reads and writes this JSON directly. **Defects:**

- `save_project` writes JSON non-atomically
  ([`models/project.py:168-175`](../../backend/app/models/project.py:168)) —
  matches audit P1 "Non-atomic file persistence."
- `list_projects` does `os.listdir` + per-project `get_project` JSON read
  ([`models/project.py:198-225`](../../backend/app/models/project.py:198)) —
  matches audit P2 "Nested report-directory scans."
- `delete_project` uses `shutil.rmtree` with no audit log or soft delete
  ([`models/project.py:227-244`](../../backend/app/models/project.py:227)).
- There is no `organization_id` or `workspace_id` on the `Project` aggregate
  — multi-tenant isolation is **TARGET**, not CURRENT.

### Task aggregate — PARTIAL

Source: [`backend/app/models/task.py`](../../backend/app/models/task.py).

`TaskManager` ([`models/task.py:114`](../../backend/app/models/task.py:114))
is a process-local singleton with a thread-safe in-memory dict
(`_tasks: Dict[str, Task]`) plus a best-effort Redis snapshot
([`_save_to_redis` / `_load_from_redis`](../../backend/app/models/task.py:152-175))
plus a Celery result-backend fallback
([`get_task` chain](../../backend/app/models/task.py:202-250)). Lifecycle is a
4-state enum at [`models/task.py:21-26`](../../backend/app/models/task.py:21):

```text
PENDING → PROCESSING → COMPLETED
                  └──→ FAILED
```

**Defects:**

- The in-memory `_tasks` dict is process-local and will not survive
  multi-worker or restart.
- `_save_to_redis` swallows all exceptions
  ([`models/task.py:160-162`](../../backend/app/models/task.py:160)) —
  durability is best-effort.
- The hourly cleanup worker `_task_cleanup_worker` is a daemon thread
  ([`app/__init__.py:229-239`](../../backend/app/__init__.py:229)) — same
  pattern as the audit's P0 finding on in-process threads.
- Tenant isolation in `TaskManager` is absent. **TARGET** per
  [`adr/ADR-0009-multi-tenant-isolation.md`](adr/ADR-0009-multi-tenant-isolation.md).

### Simulation aggregate — PARTIAL

State machine is defined in
[`services/simulation_runtime_contract.py`](../../backend/app/services/simulation_runtime_contract.py)
and driven from [`api/simulation.py`](../../backend/app/api/simulation.py).
The integration audit identified it as conflating preparation, simulation,
runtime, environment, task, and report states (audit §5 P1 "Contradictory
lifecycle semantics"). The target is the four independent state machines
defined in [`state-machines.md`](state-machines.md); they are not yet
implemented.

### Persistence — TARGET

PostgreSQL is canonical for state, lifecycle, jobs, leases, and audit. Object
storage is canonical for immutable artifacts. Redis is permitted for broker,
cache, rate-limit, and pub/sub. The current implementation uses filesystem
JSON, SQLite, and Redis only. See
[`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](adr/ADR-0012-canonical-transactional-and-object-persistence.md).

## Asynchronous execution — CURRENT and PARTIAL

The application has two asynchronous-execution paths in production today.
The integration audit identified only the in-process one as a P0; the Celery
path exists but the route still uses the in-process one.

### Celery path — CURRENT (wrapper), PARTIAL (semantics)

[`celery_app.py`](../../backend/app/celery_app.py) configures Celery against
the Redis broker and result backend. The single registered task is
[`run_simulation_task`](../../backend/app/tasks/simulation_tasks.py:16),
which calls
[`SimulationRunner.start_simulation`](../../backend/app/tasks/simulation_tasks.py:55)
and polls every 0.5 s for status
([`simulation_tasks.py:69-116`](../../backend/app/tasks/simulation_tasks.py:69)).
The task is real and used; the polling loop is a smell — the audit
recommends push-based event delivery.

### In-process daemon thread — PARTIAL (release-blocker)

The preparation endpoint in
[`api/simulation.py`](../../backend/app/api/simulation.py) still creates a
`threading.Thread(..., daemon=True)` to run preparation work. This is the
audit §5 P0 finding. The web route MUST enqueue work and return; it MUST NOT
create threads or own long-running execution. See
[`adr/ADR-0003-durable-run-orchestration.md`](adr/ADR-0003-durable-run-orchestration.md).

### Hourly cleanup daemon thread — PARTIAL

[`_task_cleanup_worker`](../../backend/app/__init__.py:229) is started from
`create_app()` and runs forever. It is another instance of the same
in-process-thread pattern.

## Simulation runtime — CURRENT

The actual OASIS / CAMEL simulation is driven by
[`services/simulation_runner.py`](../../backend/app/services/simulation_runner.py)
(82 KB) and the IPC layer in
[`services/simulation_ipc.py`](../../backend/app/services/simulation_ipc.py)
(14 KB). Configuration is generated by
[`services/simulation_config_generator.py`](../../backend/app/services/simulation_config_generator.py)
(52 KB). Observations are persisted by
[`services/simulation_observation_store.py`](../../backend/app/services/simulation_observation_store.py)
(21 KB). Artifacts are managed by
[`services/simulation_artifacts.py`](../../backend/app/services/simulation_artifacts.py)
(16 KB).

This is process-local: the runner registers a cleanup hook at app startup
([`create_app` → `SimulationRunner.register_cleanup`](../../backend/app/__init__.py:106-109))
that terminates spawned processes when the web process exits. The audit
identifies this as a horizontal-scaling blocker: another web worker cannot see
or control the process. **TARGET** is a dedicated simulation worker process
with a persistent lease and heartbeat
([`adr/ADR-0003-durable-run-orchestration.md`](adr/ADR-0003-durable-run-orchestration.md)).

## AI and reporting layer — CURRENT

- Profile generation: [`services/oasis_profile_generator.py`](../../backend/app/services/oasis_profile_generator.py) (56 KB)
- Ontology generation: [`services/ontology_generator.py`](../../backend/app/services/ontology_generator.py) (16 KB)
- Graph builder: [`services/graph_builder.py`](../../backend/app/services/graph_builder.py) (19 KB)
- Validation engine: [`services/validation_engine.py`](../../backend/app/services/validation_engine.py) (14 KB)
- Report agent: [`services/report_agent.py`](../../backend/app/services/report_agent.py) (114 KB)
- Claim boundary: [`services/claim_boundary.py`](../../backend/app/services/claim_boundary.py) (3 KB)
- Export service: [`services/export_service.py`](../../backend/app/services/export_service.py) (15 KB)

The prompt registry, prompt versioning, and evaluation harness required by
[`docs/ai/PROMPT_REGISTRY.md`](../ai/PROMPT_REGISTRY.md),
[`docs/ai/EVALS.md`](../ai/EVALS.md), and
[`adr/ADR-0004-provider-adapters-and-prompt-registry.md`](adr/ADR-0004-provider-adapters-and-prompt-registry.md)
are **TARGET** — they are not yet centralized.

## Frontend — CURRENT

Vue 3 + Vue Router + Vite + D3, built into `frontend/dist/` and served by
[`create_app` static handler](../../backend/app/__init__.py:317-325). The
Civic Wayfinding design direction
([`docs/design/DIRECTION_C.md`](../design/DIRECTION_C.md)) is implemented
in CSS and SVG; the semantic route list required by
[`adr/ADR-0006-route-map-list-parity.md`](adr/ADR-0006-route-map-list-parity.md)
is **TARGET**.

## Gaps to the target architecture

The integration audit identifies six release gates
([`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §13](../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md#13-highest-value-implementation-order)).
The TRANSITION work for each is owned by the corresponding agent and tracked
in [`docs/exec-plans/`](../exec-plans/README.md):

| Gate | Theme | Owner | Status |
|---|---|---|---|
| 0 | Immediate correctness and security | `askthepeople-security-reviewer` | NOT STARTED |
| 1 | Typed API boundary | `askthepeople-architect` | NOT STARTED |
| 2 | Durable workflows | `askthepeople-orchestration-engineer` | NOT STARTED |
| 3 | Canonical persistence and provenance | `askthepeople-persistence-engineer` | NOT STARTED |
| 4 | Scale and operations | `askthepeople-release-operator` | NOT STARTED |
| 5 | Advanced simulation methodology | `askthepeople-ai-eval-steward` + `askthepeople-architect` | NOT STARTED |

The Product Truth Contract
([`docs/product/PRODUCT_TRUTH_CONTRACT.md`](../product/PRODUCT_TRUTH_CONTRACT.md))
and the Product Truth Claim Block
([`docs/product/TERMINOLOGY.md`](../product/TERMINOLOGY.md)) outrank every
implementation detail in this document. Where the implementation and the truth
contract disagree, the truth contract wins until superseded by an accepted
ADR.

## How to read the rest of the architecture documentation

- [`data-model.md`](data-model.md) — the aggregates, the canonical store, the
  target persistence model, and the divergence between current and target.
- [`state-machines.md`](state-machines.md) — the four independent state
  machines (preparation, execution, environment, report) and the four-state
  task envelope that wraps them.
- [`adr/`](adr/README.md) — every accepted architecture decision. 12 ADRs
  are accepted as of the baseline.
- [`../exec-plans/`](../exec-plans/README.md) — the implementation program
  in dependency order.
- [`../release/ACCEPTANCE.md`](../release/ACCEPTANCE.md) — what every
  release must produce.
