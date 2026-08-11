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
| `/api/simulation` | `simulation_bp` | [`api/simulation.py`](../../backend/app/api/simulation.py) + [`api/routes/`](../../backend/app/api/routes/) | ~0.5 kloc helpers + ~3.2 kloc routes | **CURRENT (decomposition)** — all 41 route handlers now live in `api/routes/`; `simulation.py` holds only the shared helpers |
| `/api/report` | `report_bp` | [`api/report.py`](../../backend/app/api/report.py) | 48 KB | CURRENT (route layer) |
| `/api/settings` | `settings_bp` | [`api/settings.py`](../../backend/app/api/settings.py) | 13 KB | CURRENT |
| WebSocket | (none — registered in [`api/ws.py`](../../backend/app/api/ws.py)) | `api/ws.py` | 10 KB | CURRENT |

`simulation_bp` was the 3,526-line, 54-function, 41-route controller identified
by the integration audit. The decomposition (ADR-0011) is complete: all 41
route handlers now live in `api/routes/`, and `simulation.py` is a 518-line
helper module only — no route decorators remain in it:

| Module | Route fns | Lines | Holds |
|---|---:|---:|---|
| [`api/simulation.py`](../../backend/app/api/simulation.py) | 0 | 508 | shared helpers `routes/` imports (`_safe_sim_dir`, `_with_*_truth`, `_enrich_simulation_summary`, `_validate_prepare_controls`, `_check_simulation_prepared`) |
| [`api/routes/read_routes.py`](../../backend/app/api/routes/read_routes.py) | 17 | 961 | list / history / profiles / config / observations / metrics / compare / status / actions / timeline / agent-stats / posts / comments / opinions |
| [`api/routes/execution_routes.py`](../../backend/app/api/routes/execution_routes.py) | 8 | 705 | start / stop / status / inject / env |
| [`api/routes/prep_routes.py`](../../backend/app/api/routes/prep_routes.py) | 6 | 557 | create / prepare / profiles / preflight |
| [`api/routes/interview_routes.py`](../../backend/app/api/routes/interview_routes.py) | 4 | 562 | generated-response routes |
| [`api/routes/export_routes.py`](../../backend/app/api/routes/export_routes.py) | 3 | 176 | config / script / survey download |
| [`api/routes/entity_routes.py`](../../backend/app/api/routes/entity_routes.py) | 3 | 138 | graph entity listing |

Every module in `api/routes/` must be listed in that package's `__init__.py`.
`entity_routes` once was not, and the decorators it replaced were commented
out in `api/simulation.py`, so `GET /api/simulation/entities/...` answered 404
from the decomposition commit until the import was restored.

The `/posts` and `/comments` read handlers dispatch to the
[`services/simulation_activity_reader.py`](../../backend/app/services/simulation_activity_reader.py)
service (read-only mode, typed `DatabaseUnavailable`/`Locked`/`Corrupt`
exceptions) rather than opening SQLite inline, so the route layer now fully
honors the auth → parse → authorize → dispatch → present contract.

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
  ([`apply_security_headers` after-request hook](../../backend/app/__init__.py:246-293)).
- `Cache-Control: no-store` for `/api/*`, `/health`, and every `/health/*`
  ([`create_app` after-request](../../backend/app/__init__.py:290-293)).
- Production stripping of `traceback` and 5xx `error` strings
  ([`strip_traceback_in_production` after-request](../../backend/app/__init__.py:295-326)).
- No request body logging in any debug path
  ([`log_request` before-request](../../backend/app/__init__.py:208-220)).
- `SafePathError` → `400 {"success": false, "error": "invalid_id"}`
  ([`create_app` error handler](../../backend/app/__init__.py:362-366)).
- `RateLimitExceeded` → `429 {"success": false, "error": "rate_limit_exceeded"}`
  ([`create_app` error handler](../../backend/app/__init__.py:351-360)).

`/health` is provider-independent liveness. `/health/readiness` additionally
declares `scope: web` and requires the cached ZEP dependency status to be
current and available; failure returns 503 and marks only
`web_graph_backed` unavailable while leaving canonical records intact
([`api/health.py:124-190`](../../backend/app/api/health.py:124),
[`services/zep_dependency_status.py:118-231`](../../backend/app/services/zep_dependency_status.py:118)).
The process-local probe performs only `project.get()` with a two-second timeout,
caches success for 30 seconds and failure for 10 seconds, and never accepts a
stale success. ZEP remains a derived, rebuildable index rather than a canonical
store. A context-scoped filter suppresses `httpx` and `httpcore` transport
records only while that probe runs; application diagnostics remain enabled
([`services/zep_dependency_status.py:48-74`](../../backend/app/services/zep_dependency_status.py:48),
[`services/zep_dependency_status.py:178-204`](../../backend/app/services/zep_dependency_status.py:178)).
This web readiness result does not establish worker-provider reachability.

The worker has a separate **CURRENT availability attestation**, not a
process-only liveness response. Its HTTP `/health` returns 200 only after
Celery emits `worker_ready`, and only while a heartbeat-refreshed marker still
matches the expected live worker process and the immutable 40- or 64-character
runtime revision. Missing, malformed, stale, mismatched, or shutdown markers
return 503. Both response states contain exactly `status`, `service`, and
`revision`; they contain no dependency value, process identifier, exception,
or provider result
([`worker_health.py:61-151`](../../backend/scripts/worker_health.py:61),
[`celery_app.py:84-130`](../../backend/app/celery_app.py:84)).

Before broker connection, the worker bootstep performs a pure no-network
configuration validation for the graph/report task boundary. It requires the
ZEP and primary LLM keys, explicit non-memory Redis coordination, Redis-backed
Celery broker/result URLs (which may inherit the same Redis URL), and an
immutable runtime revision. After validating the dedicated marker target, the
bootstep clears any stale marker before broker connection. The wrapper binds
the health process to the actual Celery PID and removes both marker and health
process on exit
([`worker_startup.py:56-159`](../../backend/app/utils/worker_startup.py:56),
[`celery_app.py:84-145`](../../backend/app/celery_app.py:84),
[`worker_wrapper.sh:6-57`](../../backend/scripts/worker_wrapper.sh:6)).
This attestation proves that the configured worker reached Celery readiness;
it still does not prove live provider reachability. That stronger technical
seam requires the protected fictional canary in the release runbook.
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

`TaskManager` ([`models/task.py:236`](../../backend/app/models/task.py:236))
retains a process-local cache, but idempotent task admission is now shared:
the semantic payload is hashed and the reservation plus task record are
created in one Redis `WATCH`/`MULTI` transaction
([`models/task.py:413-596`](../../backend/app/models/task.py:413)). A matching
in-flight request returns the reserved task ID across processes; a mismatched
payload conflicts; and a matching reservation whose task expired can create a
new task without overwriting another record. Updates use optimistic Redis CAS
and fail after bounded contention instead of falling through to an
unconditional write
([`models/task.py:842-1035`](../../backend/app/models/task.py:842)). Lifecycle is
a 5-state enum at [`models/task.py:94-101`](../../backend/app/models/task.py:94):

```text
PENDING → PROCESSING → COMPLETED
                  ├──→ FAILED
                  └──→ CANCELLED
```

Report generation has a **TRANSITION** worker fence: one Redis-backed owner can
claim a queued report task, and report checkpoints re-check that owner before
writes
([`models/task.py:662-791`](../../backend/app/models/task.py:662),
[`report_tasks.py:159-220`](../../backend/app/tasks/report_tasks.py:159),
[`report_tasks.py:329-339`](../../backend/app/tasks/report_tasks.py:329)). A
duplicate delivery fails without entering report generation or downgrading the
owner's task.

**Remaining defects / TARGET gaps:**

- The fence is intentionally fail-closed, not a complete renewable lease. It
  has no durable heartbeat, expiry/recovery transition, monotonic fencing
  token, or transactional artifact writer. A worker crash can therefore leave
  the report task in `PROCESSING`; automatic takeover remains unsafe until the
  TARGET job/lease tables and fenced artifact writes exist.
- Non-idempotent task creation and legacy progress paths still permit a
  process-local fallback when Redis is absent; those paths are not canonical
  durable workflow state. Redis records also expire after 24 hours.
- The process-local `_tasks` cache and Celery result fallback are not the
  TARGET PostgreSQL job/event history and cannot establish replay or disaster
  recovery.
- Tenant isolation in `TaskManager` is absent. **TARGET** per
  [`adr/ADR-0009-multi-tenant-isolation.md`](adr/ADR-0009-multi-tenant-isolation.md).

### Simulation aggregate — PARTIAL

State machine is defined in
[`services/simulation_runtime_contract.py`](../../backend/app/services/simulation_runtime_contract.py)
and driven from [`api/routes/`](../../backend/app/api/routes/).
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

### In-process daemon thread — CURRENT (gate 0 fix)

The preparation endpoint
([`api/routes/prep_routes.py`](../../backend/app/api/routes/prep_routes.py))
used to create a `threading.Thread(..., daemon=True)` to run preparation work. This was the
audit §5 P0 #2 finding. The route now enqueues
`prepare_simulation_task` via Celery and returns
**HTTP 202 Accepted** with `Location: /api/jobs/{task_id}`. The Celery task
lives in
[`tasks/simulation_tasks.py`](../../backend/app/tasks/simulation_tasks.py)
and persists FAILED state on task failure. The P0 is closed; the full
durable-workflow machinery (idempotency keys, leases, fencing tokens,
heartbeats, retry classification) is gate 2, owned by
`askthepeople-orchestration-engineer`. See
[`adr/ADR-0003-durable-run-orchestration.md`](adr/ADR-0003-durable-run-orchestration.md).

### Hourly cleanup daemon thread — CURRENT (gate 2 fix)

The `_task_cleanup_worker` daemon thread that used to be started from
`create_app()` is gone. Stale-task cleanup now runs as a periodic Celery
beat job (`tasks.cleanup_old_tasks`, hourly, 24h cutoff) registered in
[`celery_app.conf.beat_schedule`](../../backend/app/celery_app.py). This
closes the second daemon-thread finding from ADR-0003 ("the same pattern as
the P0 finding"). The Celery tasks also now classify exceptions and retry
only transient failures (connection/timeout/5xx) with exponential backoff,
and the prepare route accepts an `Idempotency-Key` header that dedupes
double-submits. Full durable machinery (leases, fencing tokens, heartbeats,
the four independent state machines) remains gate 2 work.

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

### Live scenario injection — CURRENT

[`POST /api/simulation/<id>/inject`](../../backend/app/api/routes/execution_routes.py)
publishes real-time intervention payloads (breaking news, persona
modifications, dynamic instructions) to the Redis Pub/Sub channel
`simulation:<id>:events` and falls back to a process-local in-memory
queue (`push_in_memory_event` /
`pop_in_memory_events` in
[`services/simulation_observation_store.py`](../../backend/app/services/simulation_observation_store.py))
when Redis is unavailable. The runner consumes the channel via
`RedisEventConsumer` in
[`scripts/run_parallel_simulation.py`](../../backend/scripts/run_parallel_simulation.py)
and applies the events through
`apply_injected_events` in
[`services/simulation_runtime_contract.py`](../../backend/app/services/simulation_runtime_contract.py),
which logs each event to `injected_events.jsonl` and records it in the
new `injected_events` SQLite table populated by
`sync_observation_store`. Tests live in
[`tests/test_scenario_injection.py`](../../backend/tests/test_scenario_injection.py).

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
| 0 | Immediate correctness and security | `askthepeople-security-reviewer` | PARTIAL — secrets hardened, MIME/magic-byte upload validation wired onto the live route, path-traversal/SSRF defenses, source-as-data prompt guard in place. Open P0s: multi-tenant isolation (deferred; needs a user-identity model), privacy/retention architecture, source-rights attestation. |
| 1 | Typed API boundary | `askthepeople-architect` | CURRENT — `simulation.py` is now a 518-line helper module; all 41 routes live in `api/routes/` (prep, execution, interview, export, entity, read). No thread/subprocess/SQLite-directory-scan violations remain in routes; the `/posts` and `/comments` handlers now dispatch to a `simulation_activity_reader` service rather than opening SQLite inline. The typed request/response schema layer and `app/application/`+`app/domain/` packages remain gate 1 work. |
| 2 | Durable workflows | `askthepeople-orchestration-engineer` | PARTIAL — cleanup runs in Celery beat; Celery tasks classify transient retries; idempotent task admission uses an atomic cross-process Redis reservation with payload-conflict and missing-record recovery semantics; task updates fail closed after CAS contention; report deliveries use a durable single-owner execution fence. Open: renewable leases, heartbeats, monotonic fencing tokens enforced by artifact persistence, recovery/takeover, push-based event delivery, the four independent state machines, and process-local `SimulationRunner` ownership. |
| 3 | Canonical persistence and provenance | `askthepeople-persistence-engineer` | PARTIAL — atomic writes (`save_project`, `save_extracted_text`) and source sha256 hashing at ingest are in; run-artifact digests exist. Open: PostgreSQL/object-storage canonical store (schema is dead scaffolding), soft-delete/audit-log, provenance-edge write-time validation. |
| 4 | Scale and operations | `askthepeople-release-operator` | NOT STARTED — observability (no metrics/tracing; Sentry PARTIAL), SLOs/cost budgets, Redis-backed rate limiting, horizontal scaling (process-local runner, `--workers 1`), alerting. Runbook and incident-response docs are concrete but the procedures are unimplemented. |
| 5 | Advanced simulation methodology | `askthepeople-ai-eval-steward` + `askthepeople-architect` | PARTIAL — CoT scrubbing is IMPLEMENTED (ADR-0010); a versioned prompt registry and a single OpenAI-compatible adapter exist; a narrow eval suite passes in CI. Open: most prompts still inlined, model-release gating, failure-mode catalogue, adversarial/sensitivity evals. |

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
