---
title: "Architecture Overview — ASKTHEPEOPLE"
status: "Normative"
version: "1.3.0"
owner: "Architect + Security + Persistence + Orchestration"
last_reviewed: "2026-10-02"
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
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](ASKTHEPEOPLE_GODMODE_BUILDPLAN.md).
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
   (frontend/dist served by        │  app/__init__.py (create_app)│
    serve_frontend)                │                            │
                                   │  Blueprints (api/__init__.py:13-17)│
                                   │   /api/auth       auth_bp           │
                                   │   /api/graph      graph_bp (29 KB)  │
                                   │   /api/simulation simulation_bp (routes/ + helpers)
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
                                                │   • runner-owned monitor thread for the child process
                                                │
                                                ▼
                                        OASIS / CAMEL runtime
                                        (python subprocess or in-process)
```

## HTTP layer — CURRENT

The Flask application is created by [`create_app()`](../../backend/app/__init__.py).
The route responsibility contract — **auth → parse → authorize → dispatch →
present** — is stated here and is this document's own terminology; it is not
defined in the build plan or any ADR. The architectural decision to decompose
`simulation_bp` into per-resource modules is
[ADR-0011](adr/ADR-0011-incremental-modernization-over-rewrite.md). Current
implementation of the contract is **PARTIAL**: most routes handle all five steps
inline and additionally start threads, open SQLite, scan report directories, and
build exports.

### Blueprints

| URL prefix | Blueprint | File | Size | Status |
|---|---|---|---:|---|
| `/api/auth` | `auth_bp` | [`api/auth.py`](../../backend/app/api/auth.py) | 1 KB | CURRENT |
| `/api/graph` | `graph_bp` | [`api/graph.py`](../../backend/app/api/graph.py) | 29 KB | CURRENT |
| `/api/simulation` | `simulation_bp` | [`api/simulation.py`](../../backend/app/api/simulation.py) + [`api/routes/`](../../backend/app/api/routes/) | 0.5 kloc helpers + ~4.0 kloc routes | **CURRENT (decomposition)** — all simulation routes live in `api/routes/`; `simulation.py` holds only shared helpers |
| `/api/report` | `report_bp` | [`api/report.py`](../../backend/app/api/report.py) + [`api/report_routes/`](../../backend/app/api/report_routes/) | 24-line helper + ~1.6 kloc routes | **CURRENT (decomposition)** — all report routes live in `api/report_routes/`; `report.py` holds no handler |
| `/api/settings` | `settings_bp` | [`api/settings.py`](../../backend/app/api/settings.py) | 13 KB | CURRENT |
| WebSocket | (none — registered in [`api/ws.py`](../../backend/app/api/ws.py)) | `api/ws.py` | 10 KB | CURRENT |

`simulation_bp` was the 3,526-line controller identified by the integration
audit. The decomposition (ADR-0011) is complete: all simulation route
handlers now live in `api/routes/`, and `simulation.py` is a 406-line helper
module only — no route decorators remain in it. Line counts below were
re-measured on 2026-10-02; an earlier revision of this
table carried stale counts, including a 510-line figure for `simulation.py`
that no longer matched the file, and a later revision still carried 364. This
class of drift is why §0 of `AGENTS.md` forbids quoting a number that was not
produced by running the command. Re-measure before re-quoting.

| Module | Route decorators | Lines | Holds |
|---|---:|---:|---|
| [`api/simulation.py`](../../backend/app/api/simulation.py) | 0 | 406 | shared helpers imported by `routes/` (`_safe_sim_dir`, `_with_*_truth`, `_enrich_simulation_summary`, `_validate_prepare_controls`, `_check_simulation_prepared`) |
| [`api/routes/read_routes.py`](../../backend/app/api/routes/read_routes.py) | 19 | 978 | list / history / profiles / config / observations / metrics / compare / status / actions / timeline / agent-stats / posts / comments / opinions |
| [`api/routes/execution_routes.py`](../../backend/app/api/routes/execution_routes.py) | 10 | 917 | start / stop / status / inject / env / durable runtime controls |
| [`api/routes/interview_routes.py`](../../backend/app/api/routes/interview_routes.py) | 8 | 521 | generated-response routes |
| [`api/routes/prep_routes.py`](../../backend/app/api/routes/prep_routes.py) | 6 | 563 | create / prepare / profiles / preflight |
| [`api/routes/source_routes.py`](../../backend/app/api/routes/source_routes.py) | 5 (+ dynamic) | 378 | feature-gated source-ingestion capability and commands; registered onto `simulation_bp` by `register_source_routes()` (`routes/__init__.py:29`) |
| [`api/routes/decision_lens_routes.py`](../../backend/app/api/routes/decision_lens_routes.py) | 0 (+ dynamic) | 221 | immutable decision-lens review, registered dynamically |
| [`api/routes/entity_routes.py`](../../backend/app/api/routes/entity_routes.py) | 3 | 159 | graph entity listing |
| [`api/routes/export_routes.py`](../../backend/app/api/routes/export_routes.py) | 4 | 166 | config / script / survey download |
| [`api/routes/workspace_routes.py`](../../backend/app/api/routes/workspace_routes.py) | 1 | 27 | decision-workspace manifest |
| [`api/routes/__init__.py`](../../backend/app/api/routes/__init__.py) | 0 | 29 | registers every module in this package |

Report routes were decomposed the same way by exec-plan T25, into a sibling
package because they serve `report_bp` rather than `simulation_bp`. Measured
2026-10-02:

| Module | Routes | Lines | Holds |
|---|---|---|---|
| [`api/report_routes/report_lifecycle_routes.py`](../../backend/app/api/report_routes/report_lifecycle_routes.py) | 5 | 598 | generate / generate-status / progress / delete / check |
| [`api/report_routes/report_read_routes.py`](../../backend/app/api/report_routes/report_read_routes.py) | 5 | 265 | single report / by-simulation / list / sections / one section |
| [`api/report_routes/report_export_routes.py`](../../backend/app/api/report_routes/report_export_routes.py) | 4 | 169 | download / export pdf, csv, executive |
| [`api/report_routes/report_log_routes.py`](../../backend/app/api/report_routes/report_log_routes.py) | 4 | 216 | agent-log, console-log, and both streams |
| [`api/report_routes/report_tool_routes.py`](../../backend/app/api/report_routes/report_tool_routes.py) | 2 | 163 | tools/search / tools/statistics |
| [`api/report_routes/report_evidence_routes.py`](../../backend/app/api/report_routes/report_evidence_routes.py) | 2 | 66 | related-records + evidence (one handler, two rules) |
| [`api/report_routes/report_interaction_routes.py`](../../backend/app/api/report_routes/report_interaction_routes.py) | 1 | 139 | chat |
| [`api/report_routes/__init__.py`](../../backend/app/api/report_routes/__init__.py) | 0 | 57 | `register_report_routes(blueprint)` |
| **Total** | **23** | | `api/report.py` is 24 lines, 0 route decorators |

Registration here is **explicit** — `register_report_routes(report_bp)` called
from `api/__init__.py` — rather than `@blueprint.route` at import time, because
Flask 3 refuses to add rules to a blueprint that has already been registered on
an app, and `api/__init__.py` imports every route module eagerly. That makes the
404-before/200-after property testable, which
[`test_report_route_decomposition.py`](../../backend/tests/test_report_route_decomposition.py)
asserts, along with the same `entity_routes`-style "module written but never
registered" guard.

`api/report.py` survives as a 24-line module re-exporting `ReportManager`,
because `tests/test_task5_run_control_fixes.py` imports it through that path.
**No handler may be added back there**; the same test fails if one appears.

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

All implemented at the request/response seam in `create_app()` in
[`backend/app/__init__.py`](../../backend/app/__init__.py). Each item below
names the **symbol** rather than a line, on purpose: this module was 438 lines
on 2026-10-01, 496 when measured on 2026-10-02, and 519 by the end of that
session, so a line anchor measured twice in one day was already stale twice.
Grep the symbol name; do not re-add line numbers without re-measuring.

- Bearer-token auth on every `/api/*` route when `APP_TOKEN` is set
  ([`require_auth` before-request hook](../../backend/app/__init__.py));
  constant-time comparison via [`hmac.compare_digest`](../../backend/app/__init__.py).
  `/health` is exempt; unknown `/api` paths fail closed via
  [`api_not_found`](../../backend/app/__init__.py) rather than falling
  through to the SPA catch-all.
- Production CORS lockdown: `CORS_ORIGINS='*'` is refused in production and
  replaced with `http://127.0.0.1`
  ([`create_app` CORS branch](../../backend/app/__init__.py)).
- Security response headers (production only):
  Content-Security-Policy, X-Content-Type-Options: nosniff, X-Frame-Options:
  DENY, Referrer-Policy: no-referrer, Permissions-Policy with all sensitive
  features disabled, Cross-Origin-Opener-Policy: same-origin,
  Cross-Origin-Resource-Policy: same-origin, and HSTS when forwarded-proto is
  https
  ([`apply_security_headers` after-request hook](../../backend/app/__init__.py)).
- `Cache-Control: no-store` for `/api/*`, `/health`, and every `/health/*`
  (same `apply_security_headers` hook,
  [`backend/app/__init__.py`](../../backend/app/__init__.py)).
- Production stripping of `traceback` and 5xx `error` strings
  ([`strip_traceback_in_production` after-request](../../backend/app/__init__.py)).
- No request body logging in any debug path
  ([`log_request` before-request](../../backend/app/__init__.py)).
- `SafePathError` → `400 {"success": false, "error": "invalid_id"}`
  ([`handle_unsafe_path`](../../backend/app/__init__.py)).
- `RateLimitExceeded` → `429 {"success": false, "error": "rate_limit_exceeded"}`
  ([`handle_rate_limit`](../../backend/app/__init__.py), registered only
  when `flask-limiter` imports). The catch-all
  [`handle_exception`](../../backend/app/__init__.py) returns a scrubbed
  `internal_server_error` outside DEBUG.

`/health` is provider-independent liveness. `/health/readiness` additionally
declares `scope: web` and requires the cached ZEP dependency status to be
current and available; failure returns 503 and marks only
`web_graph_backed` unavailable while leaving canonical records intact
([`api/health.py:257`](../../backend/app/api/health.py:257),
[`services/zep_dependency_status.py:118`](../../backend/app/services/zep_dependency_status.py:118)).
The process-local probe performs only `project.get()` with a two-second timeout,
caches success for 30 seconds and failure for 10 seconds, and never accepts a
stale success. ZEP remains a derived, rebuildable index rather than a canonical
store. A context-scoped filter suppresses `httpx` and `httpcore` transport
records only while that probe runs; application diagnostics remain enabled
([`services/zep_dependency_status.py:54-76`](../../backend/app/services/zep_dependency_status.py:54),
[`services/zep_dependency_status.py:229`](../../backend/app/services/zep_dependency_status.py:229)).
This web readiness result does not establish worker-provider reachability.

The worker has a separate **CURRENT availability attestation**, not a
process-only liveness response. Its HTTP `/health` returns 200 only after
Celery emits `worker_ready`, and only while a heartbeat-refreshed marker still
matches the expected live worker process and the immutable 40- or 64-character
runtime revision. Missing, malformed, stale, mismatched, or shutdown markers
return 503. Both response states contain exactly `status`, `service`, and
`revision`; they contain no dependency value, process identifier, exception,
or provider result
([`worker_health.py:60-163`](../../backend/scripts/worker_health.py:60),
[`celery_app.py:146`](../../backend/app/celery_app.py:146)).

Before broker connection, the worker bootstep performs a pure no-network
configuration validation for the graph/report task boundary. It requires the
ZEP and primary LLM keys, explicit non-memory Redis coordination, Redis-backed
Celery broker/result URLs (which may inherit the same Redis URL), and an
immutable runtime revision. After validating the dedicated marker target, the
bootstep clears any stale marker before broker connection. The wrapper binds
the health process to the actual Celery PID and removes both marker and health
process on exit
([`worker_startup.py:58`](../../backend/app/utils/worker_startup.py:58),
[`celery_app.py:55-60`](../../backend/app/celery_app.py:55),
[`worker_wrapper.sh:1-57`](../../backend/scripts/worker_wrapper.sh:1)).
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
enum defined in [`models/project.py:87-93`](../../backend/app/models/project.py:87):

```text
CREATED → ONTOLOGY_GENERATED → GRAPH_BUILDING → GRAPH_COMPLETED
                                                       │
                                                       ▼
                                                    FAILED
```

`ProjectManager` ([`models/project.py:171`](../../backend/app/models/project.py:171))
reads and writes this JSON directly. **One audit finding is closed, two remain
partly open.** Re-measured 2026-10-02:

- **CLOSED — `save_project` is atomic.** It writes through
  `ProjectManager._atomic_write_text`
  ([`models/project.py:236-265`](../../backend/app/models/project.py:236)),
  which writes a sibling temp file, `fsync`s it, then `os.replace`s onto the
  final path; `save_project` calls it at
  [`models/project.py:345`](../../backend/app/models/project.py:345). Audit P1
  "Non-atomic file persistence" no longer describes this path, and the
  method's own docstring records the fix. An earlier revision of this section
  still listed it as a defect; that was stale.
- OPEN — `list_projects` does `os.listdir` + per-project `get_project` JSON
  read ([`models/project.py:605-621`](../../backend/app/models/project.py:605)) —
  matches audit P2 "Nested report-directory scans." A per-directory
  `SafePathError` is caught so one malformed entry cannot break the listing.
- PARTLY CLOSED — `delete_project` still hard-deletes with `shutil.rmtree`
  ([`models/project.py:651`](../../backend/app/models/project.py:651)), but it
  now writes an audit event **before** the removal
  ([`models/project.py:645-650`](../../backend/app/models/project.py:645)) with
  `reason="hard_delete"`, deliberately ordered so the record survives a partial
  removal. "No audit log" is therefore closed; **soft delete is not.**
- There is no `organization_id` or `workspace_id` on the `Project` aggregate
  — multi-tenant isolation is **TARGET**, not CURRENT.

### Task aggregate — PARTIAL

Source: [`backend/app/models/task.py`](../../backend/app/models/task.py).

`TaskManager` ([`models/task.py:342`](../../backend/app/models/task.py:342))
retains a process-local cache, but idempotent task admission is now shared:
the semantic payload is hashed and the reservation plus task record are
created in one Redis `WATCH`/`MULTI` transaction
([`models/task.py:539-648`](../../backend/app/models/task.py:539)). A matching
in-flight request returns the reserved task ID across processes; a mismatched
payload conflicts; and a matching reservation whose task expired can create a
new task without overwriting another record. Updates use optimistic Redis CAS
and fail after bounded contention instead of falling through to an
unconditional write
([`models/task.py:1201-1276`](../../backend/app/models/task.py:1201)). Lifecycle
is a 5-state enum at [`models/task.py:95-101`](../../backend/app/models/task.py:95):

```text
PENDING → PROCESSING → COMPLETED
                  ├──→ FAILED
                  └──→ CANCELLED
```

Report generation has a **TRANSITION** worker fence: one Redis-backed owner can
claim a queued report task, and report checkpoints re-check that owner before
writes
([`models/task.py:778-924`](../../backend/app/models/task.py:778),
[`report_tasks.py:139-220`](../../backend/app/tasks/report_tasks.py:139),
[`report_tasks.py:329-338`](../../backend/app/tasks/report_tasks.py:329)). A
duplicate delivery fails without entering report generation or downgrading the
owner's task.

**Remaining defects / TARGET gaps:**

- CURRENT: the report execution fence is now a renewable lease, not fail-closed.
  `claim_task_execution` sets `lease_expires_at`
  ([`models/task.py:880`](../../backend/app/models/task.py:880)) and permits
  takeover once a worker's lease lapses — incrementing the monotonic
  `fencing_token`
  ([`models/task.py:879`](../../backend/app/models/task.py:879)). Each
  takeover emits an operator `task_execution_takeover` warning naming the
  displaced and seizing owner and the new token
  ([`models/task.py:886-895`](../../backend/app/models/task.py:887)), so a
  wedged worker is visible in logs. The lease horizon is env-tunable
  ([`models/task.py:260`](../../backend/app/models/task.py:260)) so a slow
  LLM provider can raise it at deploy; the legacy-lease migration grace is
  independently env-tunable
  ([`models/task.py:273`](../../backend/app/models/task.py:273)) so an
  operator can widen it during a rolling deploy without slowing new-code crash
  recovery. The report agent renews the lease *before* the write-time
  validation at every checkpoint cadence
  ([`report_agent.py:1186-1204`](../../backend/app/services/report_agent.py:1186)),
  so a self-lapsed lease (a slow step that exceeded the horizon, with no
  takeover) is recovered for the rightful owner rather than aborting the
  report; transient heartbeat contention is best-effort, only a real fence
  loss (`TaskExecutionConflict`) propagates. `TaskExecutionFence.checkpoint`
  still enforces the live lease and the fencing token
  ([`models/task.py:325`](../../backend/app/models/task.py:325)), so a
  dead worker's stale fence fails closed once a newer claim takes over. A
  legacy record with `lease_expires_at is None` (claimed before leases
  existed) falls back to the task's last progress write (`updated_at`)
  rather than being instantly lapsed; old-code report workers do not refresh
  `updated_at` mid-run, so the grace window must exceed the longest plausible
  report run or a slow-but-alive legacy worker is seized after it expires. The fencing credentials
  (`execution_owner`, `fencing_token`, `lease_expires_at`) are stripped from
  `to_public_dict` so they never reach API clients.
- TARGET gaps that remain: the artifact writer is not transactional with the
  fence, so a write can land without the fence being verified as a single
  atomic unit; and the job/event history still lives in Redis with a 24-hour TTL,
  not in the TARGET PostgreSQL append-only tables, so replay/disaster recovery
  is not established.
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
[`run_simulation_task`](../../backend/app/tasks/simulation_tasks.py:40),
which calls
[`SimulationRunner.start_simulation`](../../backend/app/tasks/simulation_tasks.py:79)
and polls in a loop
([`simulation_tasks.py:95`](../../backend/app/tasks/simulation_tasks.py:95)).
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
([`create_app` → `SimulationRunner.register_cleanup`](../../backend/app/__init__.py))
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
[`create_app` static handler](../../backend/app/__init__.py). The
Civic Wayfinding design direction
([`docs/design/DIRECTION_C.md`](../design/DIRECTION_C.md)) is implemented
in CSS and SVG; the semantic route list required by
[`adr/ADR-0006-route-map-list-parity.md`](adr/ADR-0006-route-map-list-parity.md)
is **TARGET**.

The workspace is a persistent desktop shell
([`frontend/src/components/DesktopShell.vue`](../../frontend/src/components/DesktopShell.vue)):
a masthead, a journey step-spine launcher, draggable/tileable windows that
host the existing route views, and a taskbar. The shell owns the permanent
five-fact Truth Rail, so every primary route carries the disclosure. Window
state persists across refresh and deep links resolve through the router.

## Status of record

> **This section is the single authoritative statement of gate status.** Six
> other locations previously asserted gate status independently and had
> drifted apart; they are now pointers to this section. Per
> [`docs/README.md`](../README.md), every claim below cites `file:line` so it
> can be checked rather than trusted. **Do not restate gate status in another
> document.** If code changes, update this table.
>
> **Mixed baselines, declared.** This section is not measured at a single
> commit and must not be read as if it were. Three kinds of statement appear
> here, and each carries its own provenance:
>
> - **Gate and backlog claims** were reconciled against `b868477` on 2026-10-01.
> - **Schema-convergence claims** were measured on 2026-10-02 and are recorded
>   in [ADR-0013](adr/ADR-0013-schema-source-convergence.md).
> - **Gate 4 observability** moved again in commit `6e71f39` and is described
>   in its own subsection below with its own test citations.
> - **Gate 3 schema creation** moved on 2026-10-02 and is measured in its own
>   subsection below, with the two defects that were found and the tests that
>   pin them.
> - **ADR-0014 island deletion** landed in commit `8739d10` on 2026-10-02.
>   Claims that described the deleted files as present are corrected in place
>   and marked as such; they are not silently dropped, because a reader who
>   remembers the old text needs to see that it was wrong and why.
> - **Citation sweep, 2026-10-02.** Every `backend/app/__init__.py` anchor in
>   this document was re-measured; `models/project.py` and `models/task.py`
>   anchors were re-measured against 743 and 1473 lines. Two counts in this
>   document were found **overstated** — the typed-boundary ratio and the "other
>   five models" `extra="forbid"` tally — and are corrected with the
>   measurement shown.
> - **`backend/app/__init__.py` is cited by symbol, not by line, throughout
>   this document.** It was 438 lines on 2026-10-01, 496 when measured, and 519
>   by the end of the same session — a concurrent change to that module moved
>   every line anchor twice. `AGENTS.md` §5 rule 1 permits `file` + symbol where
>   a line was not pinned, and a wrong line number is worse than none. Grep the
>   symbol. The same treatment was applied to the security, privacy, design, and
>   release documents that cited it by line.
>
> Line counts anywhere in this document were true at the commit named beside
> them and go stale silently. Per `AGENTS.md` §0, re-measure before quoting: the
> commands that produce each number are in `AGENTS.md` §9.1.

There are **six** release gates and no seventh. An earlier roadmap in this
directory listed a seventh; it was archived as
[`../archive/misc/IMPLEMENTATION_ROADMAP-2026-08-18.md`](../archive/misc/IMPLEMENTATION_ROADMAP-2026-08-18.md).

**Where the six gates come from.** The gate *themes and owners* in the table
below are stated here; this is their only definition. The *rollout order* and
per-gate ownership were adopted in
[ADR-0011](adr/ADR-0011-incremental-modernization-over-rewrite.md#gate-ownership),
whose status column is frozen at that ADR's baseline. The build plan does **not**
define the gates: it has no gate section, and its §7 is *P2 gaps* while its §13
is *Permanent truth statements*. Two links here once pointed at
`#7-correct-target-architecture` and `#13-highest-value-implementation-order`;
both anchors were fabricated and have been removed.

| Gate | Theme | Owner | Status | Remaining |
|---|---|---|---|---|
| 0 | Immediate correctness and security | `askthepeople-security-reviewer` | PARTIAL | Multi-tenant isolation (deferred; needs a user-identity model), privacy/retention architecture, source-rights attestation |
| 1 | Typed API boundary | `askthepeople-architect` | PARTIAL | Complete schema enforcement across legacy handlers; finish the route responsibility contract |
| 2 | Durable workflows | `askthepeople-orchestration-engineer` | PARTIAL | Transactional (fenced) artifact writes; push-based event delivery; the four independent state machines; TARGET PostgreSQL job/event history; process-local `SimulationRunner` ownership |
| 3 | Canonical persistence and provenance | `askthepeople-persistence-engineer` | PARTIAL | Production object-storage cutover; outbox events; soft-delete/audit-log; complete provenance-edge write-time validation |
| 4 | Scale and operations | `askthepeople-release-operator` | PARTIAL | Request metrics exist (`app/utils/metrics.py`, `GET /health/metrics`, bounded labels). Remaining: distributed tracing, SLOs/cost budgets, alerting, Redis-backed rate limiting, horizontal scaling (process-local runner, `--workers 1`); Sentry PARTIAL |
| 5 | Advanced simulation methodology | `askthepeople-ai-eval-steward` + `askthepeople-architect` | PARTIAL | Most prompts still inlined; model-release gating; failure-mode catalogue; adversarial/sensitivity evals |

### Gate evidence

**Gate 0.** Path-escape defense (`backend/app/utils/safe_path.py`); SSRF
defense on source ingestion (`backend/app/utils/safe_url.py`); bearer auth on
`/api/*` and signed WebSocket tickets (`backend/app/__init__.py`,
`backend/app/api/ws.py`); fail-closed `SECRET_KEY`/`APP_TOKEN` and production
CORS refusal (`backend/app/config.py:117-121`, and the
  `_is_production and _cors_origins.strip() == "*"` branch in `create_app`);
5xx traceback scrubbing (`backend/app/__init__.py`). Remaining P0 coverage is
specified in [`../security/THREAT_MODEL.md`](../security/THREAT_MODEL.md).

**Gate 1.** `backend/app/api/simulation.py` is a **406-line** helper module
that holds only shared helpers; it contains no request handler. Simulation
      handlers live in `backend/app/api/routes/` (9 route modules). Report
      handlers were decomposed on 2026-10-02 by exec-plan T25: `api/report.py`
      is a 24-line module with no route decorators and all 23 report handlers
      live in `backend/app/api/report_routes/` (7 modules). Typed schemas and
the `app/application/` + `app/domain/` foundations are present —
`backend/app/application/decision_workspace_service.py` and nine modules under
`backend/app/domain/` (`run_attempt.py` 469 lines, `source_ingestion.py` 831
lines, `decision_lens.py` 379, `possible_path.py` 354, `decision_workspace.py`
281, `authorization.py` 139, `identifiers.py` 138, `actor_context.py` 82). No
route owns a preparation daemon thread or opens the activity SQLite directly.

The typed request boundary is **partial, and deliberately so**. **Correction
(2026-10-02):** an earlier revision of this paragraph claimed "27 of 99 routes
carry a schema". Measured against the live app, that is wrong in both numbers.
The denominator is **102** unique `/api` endpoints
(`create_app()` → `url_map.iter_rules()`, excluding `HEAD`/`OPTIONS`), and the
numerator is **18** — counted as every `@enforce_schema(...)` and
`@validate_schema(...)` decorator plus the two handler-wrapping
`enforce_schema(...)` calls in `api/settings.py`:

| Where | Count | Mechanism |
|---|---:|---|
| `api/routes/prep_routes.py` | 2 | `@validate_schema` |
| `api/routes/execution_routes.py` | 3 | `@validate_schema` |
| `api/sources.py` | 1 | `@validate_schema` |
| `api/report_routes/report_lifecycle_routes.py` | 1 | `@enforce_schema` |
| `api/report_routes/report_interaction_routes.py` | 1 | `@enforce_schema` |
| `api/report_routes/report_tool_routes.py` | 2 | `@enforce_schema` |
| `api/routes/interview_routes.py` | 4 | `@enforce_schema` |
| `api/routes/export_routes.py` | 1 | `@enforce_schema` |
| `api/graph.py` | 1 | `@enforce_schema` |
| `api/settings.py` | 2 | `enforce_schema(...)` call, not a decorator |

Two corrections inside the old claim survive scrutiny: the two settings routes
*are* typed, but by function call (`api/settings.py:309`, `:391`) rather than a
decorator, which is why a decorator-only grep misses them; and
`decision_lens_routes` is **not** part of this boundary — it imports from
`app/api/decision_lens_schemas.py` (`api/routes/decision_lens_routes.py:25`),
a different module from the request-boundary schemas in `api/schemas.py`.

Roughly twenty routes were left untyped **on purpose**, because a body schema on
them would validate `{}` and never fire: `read_routes` and `entity_routes` are
GET-only, `graph.py`'s upload seam is `multipart/form-data`, two graph routes
take `project_id` in the query string, and `GET/POST generate/status` reads
identifiers from the query string on GET.
`test_read_typed_boundary.py` and `test_graph_typed_boundary.py` assert that
those stay untyped, so the decision cannot silently reverse.

`enforce_schema()` in [`api/schemas.py`](../../backend/app/api/schemas.py)
preserves each endpoint's existing `400` `{success, error}` envelope rather than
`validate_schema`'s `422` Problem Details, so typing was additive rather than a
breaking change. Two routes use `extra="ignore"` on purpose — `/report/generate`
and `/graph/build` — because each has a test that posts a canary field
(`user_prompt`, `graph_name`) to prove client data is discarded before it reaches
a canonical record. Forbidding extras would reject the request before the handler
could demonstrate that, making the payload-provenance guarantee in
`test_report_worker_dispatch.py` and `test_graph_worker_final_fixes.py`
**vacuous** (`AGENTS.md` §5 rule 5). **Correction (2026-10-02):** an earlier
revision said "the other five models use `extra="forbid"`". Re-read on
2026-10-02, **at least twelve** bound models declare `extra="forbid"` — the
four `schemas_interview_export.py` interview models, `ExportGeneratedResponsesRequest`,
`ReportChatRequest`, `GraphSearchRequest`, `GraphStatisticsRequest`,
`StopSimulationRequest`, and `SimulationControlRequest`. Two further bound
models (`CreateSimulationRequest`, `PrepareSimulationRequest`) declare **no**
`model_config` at all, so they inherit Pydantic's default `extra="ignore"`
and are **not** strict. A model is only `strict=True` if it says so: the
`extra="ignore"` pair and every `extra="forbid"` model in `api/schemas.py`
carry `strict=True`, and the two unconfigured models do not. The coercion the
rule is protecting against is real and is covered where `strict=True` is set —
`"force_regenerate": "yes"` cannot become `True` on
`PrepareSimulationRequest`'s sibling graph model, and `simulation_id: 5`
cannot become `"5"` — but do not restate it as a property of *every* model.

**Gate 2.** Routes enqueue to Celery and return 202 rather than spawning daemon
threads (`backend/app/api/routes/prep_routes.py`,
`backend/app/tasks/simulation_tasks.py`); cleanup runs in Celery beat; task state
is shared through Redis with atomic compare-and-swap updates
(`backend/app/models/task.py`). Report delivery uses a durable, renewable
single-owner execution fence with monotonic fencing tokens, renew-before-validate
heartbeat self-recovery, env-tunable lease horizon, expired-lease takeover, and
fencing-credential stripping in `to_public_dict`
(`backend/app/models/task.py:276`, `backend/app/models/task.py:321`,
`backend/app/models/task.py:949`, `backend/app/models/task.py:1030`).

**Gate 3.** Tenant/workspace-scoped PostgreSQL repositories cover projects,
sources, runs, decision lenses, and first-class path aggregates
(`backend/app/services/project_repository.py`,
`backend/app/services/source_repository.py`,
`backend/app/services/run_repository.py`,
`backend/app/services/path_repository.py`,
`backend/app/services/decision_lens_repository.py`), with three migrations
(`backend/migrations/versions/384c98f88d53_initial_schema.py`,
`backend/migrations/versions/a1b2c3d4e5f6_domain_aggregates.py`,
`backend/migrations/versions/b2c3d4e5f6a7_path_aggregates.py`). Persistence is
opt-in behind `USE_SUPABASE_PERSISTENCE`
(`backend/app/config.py:354-356`).

**Schema creation is now performed by something.** Measured 2026-10-02, this
was the open half of exec-plan 08 fix 1, and both halves turned out to be broken
rather than merely unwired:

- `alembic upgrade head` could not run at all without production credentials.
  `backend/migrations/env.py` imported `app.db.schema` at module scope;
  importing any `app.*` submodule executes `backend/app/__init__.py`, whose
  `Config` class body raises `SECRET_KEY must be set in production`. The
  migration tool aborted before reaching the database, even against a throwaway
  SQLite file. `env.py` now loads the ORM metadata lazily and only for
  autogenerate, so `upgrade`/`downgrade` depend on no credentials at all.
- `alembic revision --autogenerate` generated a **schema wipe**. ADR-0013 left
  `app/db/schema.py` declaring `Base` and no tables, so autogenerate diffed an
  empty target against a live database and read all 16 canonical tables as
  removed. Run against a database at head, it wrote a revision whose `upgrade()`
  was 16 `op.drop_table` and 43 `op.drop_index` calls, exited 0, and reported
  success. It is the standard tool for the documented workflow, so this was a
  live landmine rather than a theoretical one. `env.py` now refuses autogenerate
  by name and tells the operator to hand-write the revision.
- A required `migrations` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
  asserts a single linear head, applies all three revisions to an empty database
  with no credentials in the environment, asserts the canonical tables exist and
  the recorded head is reached, round-trips downgrade and upgrade, and asserts
  autogenerate still refuses and writes nothing. Operator entry points are
  `npm run backend:migrate` and `npm run backend:migrate:status`. All of it is
  pinned by
  [`backend/tests/test_migrations_are_runnable.py`](../../backend/tests/test_migrations_are_runnable.py).

**The divergence as measured before it was closed.** Recorded because the
measurement is what justified stripping rather than mirroring: `schema.py`
declared **6** tables against the migrations' **16**; only `projects` and
`simulations` appeared in both, and those two did not even agree on a primary
key (`sa.Integer()` autoincrement in
`backend/migrations/versions/384c98f88d53_initial_schema.py:25` versus
`Column(Uuid, ...)` in the ORM). The two shared tables were not the same
tables: `projects` shared 4 of 6 ORM columns with its 16-column migration
counterpart, `simulations` 5. **The live code targeted the migration** —
`backend/app/services/project_repository.py:241` queries
`WHERE project_id = :project_id`, a column only the migration has. There is no
longer a second source to compare, so this is history; the current measurement
is that `backend/app/db/schema.py` is a 63-line module declaring zero tables
and zero columns, and `backend/tests/test_schema_parity.py` asserts exactly
that rather than comparing allowances.

**Exec-plan T2 as written was rejected; the divergence is now closed.** Adding
the four ORM-only tables as migrations would have enshrine a stub, and could not
work: their foreign keys point at `projects.organization_id`, which the
migration does not have. Instead `backend/app/db/schema.py` was **stripped to
`Base` alone** on 2026-10-02, and its six stub classes removed rather than
mirrored — 198 columns of hand-maintained duplication would have recreated a
second source of truth with more places to forget than the six tables it
replaced.

**T4 is done.** `create_app` no longer materializes schema. It imports
`get_engine` only, creates the engine and opens a connection — a real
connectivity probe that still drives the existing fail-closed branch for an
unreachable `DATABASE_URL` in production — and issues no DDL. `init_db()` now
**raises** rather than being deleted, so any surviving caller fails loudly
instead of silently reinstating the old behaviour. Removing `create_all` was
safe precisely because it was harmful: it built a `projects` table with no
`project_id`, which is the column
`backend/app/services/project_repository.py:241` queries.

Two guards pin this, both proven by planting a violation and watching them fail:

- `backend/tests/test_startup_no_schema_creation.py` (3 tests) records calls to
  `Base.metadata.create_all` while booting the real app factory. Recording is
  required rather than raising, because `create_app` wraps the database block
  in `except Exception` and would swallow an assertion from inside `create_all`.
- `backend/tests/test_schema_parity.py` (9 tests) asserts the ORM declares **no**
  tables, that `Base.metadata.tables` is empty so neither `create_all` nor
  `drop_all` can touch schema, that the migrations still declare their 16
  expected tables with one linear head, and that `Base` remains importable.

**Known gap, recorded not fixed:** the `dw_*` aggregates carry
`organization_id`/`workspace_id`
(`backend/migrations/versions/a1b2c3d4e5f6_domain_aggregates.py:36-37`) with
**no `organizations` table in any migration**, so those columns have no
foreign-key target. Multi-tenancy is deferred by D2, so this is inert today;
it is tracked under ADR-0009.

**T6 is done.** A flag enabled against a reachable but never-migrated database
now fails with a named error instead of a driver-level `UndefinedTable`.
`backend/app/db/__init__.py` gains `require_tables`, raising
`CanonicalSchemaMissing` with each missing table and the remedy
(`alembic upgrade head`, or unset the flag).
`backend/app/services/project_repository.py` requires `{projects, sources,
ontologies}` and `backend/app/services/source_repository.py` requires
`{dw_sources, dw_source_versions}` — sets **read from each repository's SQL**,
not guessed; a first draft named five tables `ProjectRepository` never queries.
The check runs once on engine acquisition, not per query, and
`backend/tests/test_canonical_store_schema_guard.py` (5 tests) verifies each
declared table is one a migration actually creates. Proven by neutering
`require_tables`: two tests fail.

**Phantom imports are guarded, and the two offenders are gone.** Two modules used
to import packages that did not exist, and nothing detected it:
`backend/scripts/migrate_json_to_postgres.py` imported `app.db.database` and
`app.db.models.*`, and `backend/app/optimization/learning_loop.py` imported
`app.db.models`. Neither package existed — `backend/migrations/env.py` records
that the same package "never existed" — and both failed with a bare
`ModuleNotFoundError` far from the cause. **Both files were deleted on
2026-10-02** by
[ADR-0014](adr/ADR-0014-removal-of-optimization-backtest-island.md), which
emptied the `KNOWN_UNRESOLVED` allowance that had been tolerating them and
removed the two pinning tests.
`backend/tests/test_no_phantom_imports.py` (**5** collected tests, re-measured
2026-10-02; an earlier revision here said 6) resolves every absolute `app.*`
import against the filesystem. It is **static** — parsing each file's AST rather
than importing it — because importing every module would execute Celery app
construction and database engine creation, making the test order-dependent and
environment-sensitive. The allowance is now empty, so there is no reason for an
entry to exist; a staleness test would fail if a phantom reappeared. Proven by
planting `from app.services.does_not_exist import thing`: the guard fails.

**Per-call prompt provenance now reaches disk.** ADR-0004 requires a SHA-256
record for every model call. Those records were being constructed in
`backend/app/services/oasis_profile_generator.py` and then discarded, so the
audit trail the rule requires did not exist. `OasisProfileGenerator` now
accumulates them under a lock (generation runs on a thread pool) and hands
them over via `drain_prompt_records()`; `write_run_manifest()` in
`backend/app/services/simulation_artifacts.py` writes them to
`run_manifest.json` at both tier-4 artifact sites in
`backend/app/services/simulation_manager.py`. Covered by
`backend/tests/test_simulation_artifacts.py`. This is the **on-disk run
artifact**, alongside the other JSON files in the simulation directory, and
needs no schema change; it is deliberately **not** the canonical run-manifest
table, which still lands with the canonical persistence layer.

**The decision is recorded.**
[ADR-0013](adr/ADR-0013-schema-source-convergence.md) declares migrations
canonical, which *implements*
[ADR-0012](adr/ADR-0012-canonical-transactional-and-object-persistence.md)
rather than re-deciding it — ADR-0012 already required "schema changes are
Alembic-only; web and worker startup never call `create_all`". ADR-0013 records
the measured divergence, the boot path
(`backend/app/__init__.py` → `:167` → `backend/app/db/__init__.py:27`),
and the verified reachability table. That table is the load-bearing part: it
shows the divergence was a **trap, not active corruption**, because
`RunRepository` and `PathRepository` have no production importer at all and
both live repositories are behind flags that default off.

**Gate 4 — PARTIAL, re-scoped 2026-10-02.** Gate 4 previously had no
implementation; before that date it had none, and the honest legend vocabulary
for "approved but unbuilt" is `TARGET`. It is now PARTIAL because metrics
exist and the remainder is open:
`backend/app/utils/metrics.py` provides in-process request metrics, installed by
`_register_metrics` in `backend/app/__init__.py` and exposed in Prometheus text
format at `GET /health/metrics` (`backend/app/api/health.py`). It records
request count, latency as a fixed-bucket histogram, cumulative duration, and
in-flight depth.

**Metric labels are bounded by construction, which is the privacy and
cardinality requirement.** Only `method`, Flask `endpoint`, and `status_class`
are labelled. Never the URL, never an id: `route_label` returns `"unmatched"`
for anything that is not a short endpoint name, so a request to an unrouted
path cannot become one time series per path, and a project or simulation id
cannot reach a label. Storage is bounded by `method x endpoints x 4` regardless
of traffic, and the histogram has fixed bucket boundaries rather than per-request
samples.

The endpoint sits **outside** `/api` and therefore outside bearer auth,
because a scraper cannot hold an `APP_TOKEN`. It exposes only counts, latencies,
and endpoint names — the same class of information the public `/health` route
already exposes about component state. A deployment that needs it hidden should
put it behind the ingress rather than add a token check that would break
scraping.

Tested by `backend/tests/test_metrics_gate4.py` (32 collected tests, re-measured
2026-10-02). **Correction:** an earlier revision of this paragraph also cited
`backend/tests/test_metrics_wiring.py` (6 tests). That module was **deleted**,
and the "removed registration fails 4 of 6" claim died with it — do not
restate it. The surviving coverage proves the privacy property on the
**output**, not the input: the exposition is scraped and checked for path
separators and id-shaped hex, so a future change that passes `request.path`
fails a test rather than leaking.

**Still missing:** distributed tracing, SLO and cost-budget definitions,
alerting rules, Redis-backed rate limiting, and horizontal scaling. Sentry is
PARTIAL. `../release/RUNBOOK.md` and
[`../security/INCIDENT_RESPONSE.md`](../security/INCIDENT_RESPONSE.md) remain
concrete while the procedures they describe are still partly unimplemented.

**Gate 5.** CoT scrubbing is implemented per ADR-0010
(`strip_reasoning_scaffold()` in `backend/app/services/report_agent.py`, covered
by `backend/tests/test_reasoning_scrub.py`). A versioned prompt registry
([`../ai/PROMPT_REGISTRY.md`](../ai/PROMPT_REGISTRY.md)) and a single
OpenAI-compatible adapter exist, and a narrow eval suite
(`backend/tests/evals/`) passes in CI. The behavioural modules `big_five` and `prospect_theory` remain, exported from
`backend/app/services/__init__.py` and unit-tested; `diffusion_model` is
exported at `services/__init__.py:41` and is **wired in production** by
`simulation_config_generator.py`. **Correction (2026-10-02):**
`constraint_engine`, `game_theory`, and `calibration_metrics` no longer exist.
They were deleted, not wired, by
[ADR-0014](adr/ADR-0014-removal-of-optimization-backtest-island.md) (commit
`8739d10`) together with their five tests; a grep for any of the three names
under `backend/` now returns nothing. Their Phase 2 analysis survives in
[`NEXT_STEPS_ROADMAP.md`](NEXT_STEPS_ROADMAP.md) and §B2 of
[`ULTRAPLAN.md`](ULTRAPLAN.md), both of which describe modules that are gone —
those two documents need a correction pass.

**Character distinctness is measured, not assumed.** The distinctness eval
(`backend/tests/evals/test_variant_persona_distinctness.py`) failed on entry:
worst-pair shingle similarity was 0.647 against its own 0.60 bar. The root
cause was that every composition axis was *shorter than the expansion factor*,
so collisions were unavoidable by construction. Composition now addresses four
axes by mixed radix over a single global slot (`_axis_values` in
`backend/app/services/persona_composition.py`), which is injective across the
**whole population** rather than within one archetype — the previous
per-archetype guarantee still produced exact duplicate personas across
archetypes, which a one-archetype-at-a-time eval cannot see. Measured on a real
5,000-variant tier-4 population: 5,000 unique personas, worst legitimate pair
0.634, worst within-archetype pair 0.253. Two invariants are asserted at import
rather than left to a comment: no axis length may share a factor with the
composition stride (an axis whose length divides the stride is constant across
every variant of one archetype), and the joint axis space must cover the
declared population.

The batch diversity gate in `backend/app/services/profile_validators.py` had
two defects. It compared the **raw** persona, so the mandated disclosure and
role framing that every variant is required to carry dominated the score:
legitimate variants measured 0.93-0.95 and the gate rejected its own correct
output. And it was O(n²) at tier-4's 5,000 profiles. It now measures only the
discriminating text, and its pairwise stage runs inside a documented budget
while the exact-duplicate stage stays O(n) across the whole population,
reporting in `details` when the pairwise stage was skipped. It previously
never ran on archetype-expanded variants at all; `generate_archetype_profiles`
now validates the expanded population. The threshold and its limits are pinned
by `backend/tests/test_profile_validation.py`.

**Gate 5 blocker — CLOSED by deletion, 2026-10-02.** This subsection is now
history and is retained because the *reason* still constrains future work. The
θ-optimization island once comprised five unimported artifacts citing a
now-archived roadmap as "Authority", each carrying a DO-NOT-WIRE warning naming
the superseded document and the truth-rail clause it violates:

- `backend/app/optimization/theta_optimizer.py` — fit θ to observed outcomes
- `backend/app/optimization/multi_objective_loss.py` — scored against `P_real_world`
- `backend/app/optimization/learning_loop.py` — closed loop consuming outcomes
- `backend/app/simulation/hybrid_simulator.py` — pipeline from *real observed
  platform state* to a *final predictive distribution*
- `backend/db/migrations/20260819_add_capability_registry.sql` — table keyed
  to `forecast_horizon` and a real population

**Every one of those five paths no longer exists.**
[ADR-0014](adr/ADR-0014-removal-of-optimization-backtest-island.md) (commit
`8739d10`) deleted the island rather than warning about it, because an agent
looking for this code should find the ADR and not a header comment. Verified
2026-10-02: `Get-ChildItem backend -Recurse -Filter '*capabilit*'` and
existence checks on each of the five paths return nothing under `backend/`.
The roadmap,
[`../archive/misc/PREDICTIVE_SIMULATION_ROADMAP-2026-08-19.md`](../archive/misc/PREDICTIVE_SIMULATION_ROADMAP-2026-08-19.md),
was archived on 2026-10-01 because its stated objective is to minimize the
distance between simulated and **observed real-world behaviour** — a
calibration objective against human outcomes, which the truth rail forbids
(`NOT A FORECAST`, `HUMAN RESPONDENTS: 0`, `SOURCES: STARTING CONDITIONS ONLY`).
Its companion
[`../archive/misc/predictive-persona-system-integration-2026-08-03.md`](../archive/misc/predictive-persona-system-integration-2026-08-03.md)
proposed a "target capability" of reporting a **68% probability** of a market
outcome. Both contradict accepted
[ADR-0001](adr/ADR-0001-product-category-and-truth-contract.md) and must not be
implemented. Wiring `app/optimization/` would require a new accepted ADR that
supersedes ADR-0001 — that is a product decision, not a refactor.

### Shipped work not previously reflected in any status table

The following is complete at `b868477`. Earlier trackers still described it as
open.

- **Exec-plan 08** (harvest framework engineering fixes): fixes 2, 3, 4, and 5
  are done. Fix 1 (dual SQLAlchemy bases / Alembic) is partial and belongs to
  gate 3.
- **Exec-plan 09 Tier 1** (decision-only mode): source material is no longer
  required to submit — the `files.value.length > 0` guard was removed from
  `canSubmit` (`frontend/src/views/Home.vue:535`, with the requirement list
  updated at `frontend/src/views/Home.vue:541`; re-measured 2026-10-02 after the
  decision-first rebuild of that view).
- **Exec-plan 09 Tier 2** (URL ingestion): `POST /api/sources/fetch` is live
  (`backend/app/api/sources.py:20-22`), backed by
  `backend/app/services/url_fetcher.py` and the SSRF guard in
  `backend/app/utils/safe_url.py`. Tier 3 (auto-research) is not started.
- **Decision Workspace SDD tasks 1-4** are complete: the domain kernel under
  `backend/app/domain/`, the tenant persistence migration
  `a1b2c3d4e5f6`, and the run/source repositories. See
  `.superpowers/sdd/progress.md` for the per-task record.
- **Fork action** (`NEXT_STEPS_ROADMAP.md` Phase 1.1) is built and wired:
  `forkSimulation()` is called by `frontend/src/components/ForkRunControl.vue:51`
  and `frontend/src/components/ForkRunControl.vue:79`, which is mounted by
  `frontend/src/views/SimulationRunView.vue`. Branch lineage
  (`forked_from`, `forked_at_turn`, `forked_at`) is served by
  `/api/simulation/list` and `/history`. The branch **tree and comparison
  views** are still unbuilt.
- **Release verification gate**: `scripts/release/verify` is the single
  verification entry point required by `../release/RUNBOOK.md:131-135`, invoked
  by `npm run verify` (`package.json:18`). It runs **six** gates:
  the documentation validator
  (`tools/validate_docs.py`), the doc truth-gate self-test
  (`scripts/release/check-docs-gates.sh`), frontend tests, the frontend
  production build, backend tests excluding evals, and a gitleaks scan when the
  binary is present.
- **Both CI truth gates were inert until 2026-10-01 and are now armed.** The
  naked-wordmark check and the prohibited-outcome-language check in
  `.github/workflows/docs.yml` each used a multi-line parenthesised ERE. GNU
  grep cannot compile that (`Unmatched ( or \(`), and because both pipelines
  ended in `|| true` the error was swallowed, the hit list came back empty, and
  the gates reported PASS unconditionally. **The wordmark gate had never caught
  a single violation in the repository's history.** Both patterns are now
  single-line, each gate asserts its own patterns compile (grep exits 2 on a
  regex error, 1 on a clean no-match — testing for a match would fail on a clean
  tree), and `scripts/release/check-docs-gates.sh` runs as gate 2 of
  `npm run verify`, planting a violation to prove each gate fires.
- **The wordmark gate was also logically wrong, not just inert.** It flagged
  *any* occurrence of the wordmark, so a correctly branded line
  ("ASKTHEPEOPLE — Synthetic Decision Explorer") was a violation too — which is
  why it needed an ever-growing allowlist. It now flags the wordmark only where
  an approved descriptor does **not** accompany it, using the same five
  descriptors as `tools/lint_frontend_truth.mjs`
  `APPROVED_PRODUCT_DESCRIPTOR_PATTERN`. Non-prose occurrences (URLs, asset
  filenames, filesystem paths, JSON response literals) are exempt. Scope is the
  user-facing surfaces — `README.md`, `docs/release/`, `docs/privacy/` — because
  an all-of-`docs/` scope produced only internal-prose false positives (ADRs,
  design analyses, document titles, prompt templates). The current tree has
  **zero** violations under that scope.
- **Two documents that contradicted ADR-0001 were archived.** See the truth
  surface note below.
- **OPEN DECISION — the brand descriptor is inconsistent across three
  variants, and no gate catches it.** The accepted
  [ADR-0001](adr/ADR-0001-product-category-and-truth-contract.md) classifies the
  product as a **Synthetic Decision Explorer**
  (`docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md:30`).
  The split was wider than this document recorded. As of 2026-10-02, after the
  shell redesign consolidated five hand-written route headers into
  `frontend/src/components/ViewHeader.vue`, **`frontend/src/**` now uses the
  ADR-0001 family throughout**: the shared header, the masthead lockup
  (`frontend/src/components/DesktopMasthead.vue`), and the entry view
  (`frontend/src/views/Home.vue`) all render
  `Synthetic Decision Explorer`. The five per-view brand blocks that used to
  render `Ask The People / generated Decision Explorer — home` no longer exist
  as markup, so the seven naked-wordmark truth violations they carried are gone.
  `tools/lint_frontend_truth.mjs` `APPROVED_PRODUCT_DESCRIPTOR_PATTERN`
  accepts both families, so nothing gates the difference.
  **What remains is `frontend/index.html`, which still ships
  `GENERATED DECISION EXPLORER`** in `<title>` (line 20), the description meta
  (line 10), and the Open Graph title (line 12); the two wordmark SVGs
  (`frontend/public/mark.svg:2`, `frontend/public/social-card.svg:2`); **and
  `frontend/src/views/NotFoundView.vue:9`, which still renders the bare
  `Ask The People` wordmark in visible body text.** An earlier revision of this
  paragraph named only the first three surfaces and so under-counted the
  residual. That is the residual split, and
  it is still deliberately unresolved: unifying it edits what users see or
  edits an accepted ADR, and both are product-claim changes requiring a PR with
  named reviewers, an impact statement, and a rollback plan per `AGENTS.md`
  §5 rule 13.
- **CORRECTION — the frontend truth linter does not have the blind spot this
  document used to record.** It previously claimed that
  `VISIBLE_ATTRIBUTE_PATTERN` matched attributes only and that visible text
  nodes were therefore unenforced. That was wrong, and re-running the linter on
  2026-10-02 disproves it: it reports **6 violations, 3 of them on visible text
  nodes** (`frontend/src/components/Step4Report.vue:251`,
  `frontend/src/views/NotFoundView.vue:9`, and both wordmark SVGs). The linter
  has three candidate sources — attributes via `VISIBLE_ATTRIBUTE_PATTERN`
  (`tools/lint_frontend_truth.mjs:7-8`), template text between `>` and `<`
  reported as surface `text` (`tools/lint_frontend_truth.mjs:189-197`), and
  `<script>` string literals reported as `script-string`
  (`tools/lint_frontend_truth.mjs:208-217`). Only the attribute pattern is
  attribute-only; visible copy is enforced.
- **The doc validator now checks link anchors (2026-10-01).** It previously
  stripped `#fragment` and never resolved it, so two **fabricated** anchors
  shipped and survived: `…BUILDPLAN.md#13-highest-value-implementation-order`
  (§13 is *Permanent truth statements*) and
  `…BUILDPLAN.md#7-correct-target-architecture` (§7 is *P2 gaps*). Neither
  heading exists anywhere. `tools/validate_docs.py` now resolves a fragment
  against the target file's headings using GitHub's slug rules and fails on a
  mismatch, and it found four more on the first run — two in
  `docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md`
  and two in `docs/architecture/state-machines.md`. All are repointed to real
  headings or de-linked with the fabrication recorded. It also accepts `#LlNNN`
  highlighter anchors and explicit HTML `id=` targets.
- **The backend and frontend prohibited-term lists had drifted, and now
  cannot.** `tools/lint_frontend_truth.mjs` `TERM_PATTERNS` holds 33 patterns (re-measured 2026-10-02; `_term_regexes()` in
  `backend/tests/test_backend_truth_terms.py` returns 33)
  applied to `frontend/src/**`; `backend/app/utils/llm_client.py`
  `_TRUTH_KEYWORDS_PROHIBITED` held 5 strings applied to every LLM response by
  `_audit_response`. Nothing enforced agreement, and the two differed: the
  frontend pattern was `polls?`, which matches "poll" and "polls" but **not**
  "polling" — a term the backend prohibited. A response asserting "polling data
  suggests" was therefore rejected by the backend and accepted by the UI
  linter. `backend/tests/test_truth_term_sync.py` compiles the JS patterns as
  Python regexes and asserts each backend-prohibited term is actually matched
  by one, so this cannot drift again; the frontend pattern is now
  `poll(?:s|ed|ing)?`.
- **A backend-wide term gate now exists, with a reviewed allowlist.** The plan
  called this T16 and warned it would be false-positive prone. It was:
  `backend/scripts/survey_backend_truth_terms.py` found **194** matching
  literals in `backend/app/**`, **104** of them with no negation marker, and
  hand-classification showed none was a truth-contract violation. They fall
  into four groups — the DO-NOT-WIRE'd θ-optimization island (~61), disclosure
  *field names* whose value is "not calibrated" (~14), non-claim vocabulary
  such as the verb "Poll" and the route path `/export/survey` (~14), and the
  prohibition list itself. `backend/tests/test_backend_truth_terms.py` now
  gates the rest: it compiles the frontend `TERM_PATTERNS` as Python regexes,
  skips any match whose **clause** carries a negation, excludes the reviewed
  island, and fails on anything else. **114 of 139 `backend/app` modules are
  gated** and 25 are allowlisted, each with a written reason, and the test
  asserts every allowlist entry still points at a real file — so none is stale.
  (Re-measured 2026-10-02 after ADR-0014 removed nine dead-island allowlist
  rows; an earlier revision said 100 of 135 with 35 allowlisted.) Verified by planting
  `backend/app/__truth_probe__.py` containing "this run predicts what people
  will do" — the gate failed, and passed again once removed.
- **Step 1 progressive guidance** is live: `ProgressiveGuidance` and
  `ContextualHelp` are used in `frontend/src/components/Step1GraphBuild.vue`
  (5 and 2 references) with adaptive title copy.

### Feature-level backlog

Adoption of the progressive-guidance system is partial. Measured by reference
count in each component:

| Component | `ProgressiveGuidance` | `ContextualHelp` | Adaptive copy | Strategy checklist |
|---|---:|---:|---:|---|
| `Step1GraphBuild.vue` | 5 | 2 | 4 | complete |
| `Step2EnvSetup.vue` | 4 | 3 | 3 | [`STEP2_MIGRATION_STRATEGY.md`](../design/STEP2_MIGRATION_STRATEGY.md) lines 290-325 — progressive profile display landed (2026-10-01); Sessions 2-5 (help/adaptive-copy depth) remain |
| `Step3RunWayfinder.vue` | **0** | 3 | 0 | [`STEP3_STEP4_MIGRATION_STRATEGY.md`](../design/STEP3_STEP4_MIGRATION_STRATEGY.md) lines 214-225 — contextual help landed (2026-10-01) for the run boundaries and diagnostics concepts; the truth boundary itself is deliberately NOT capability-wrapped (hiding it would violate the truth contract) |
| `Step4Report.vue` | **0** | 2 | 0 | [`STEP3_STEP4_MIGRATION_STRATEGY.md`](../design/STEP3_STEP4_MIGRATION_STRATEGY.md) lines 427-439 — contextual help landed (2026-10-01) for the report-records concept; the export controls keep the native `<details>` disclosure because `ProgressiveGuidance`'s availability tier would hide the Markdown/TXT exports from first-use users entirely (caught by `frontend/src/__tests__/report-recovery.spec.js`) |
| `Step5Interaction.vue` | **0** | **0** | 2 (`actionLabel`) | not planned |

These checklists are the authoritative work items for the migration;
[`../design/COMPONENT_MIGRATION_CHECKLIST.md`](../design/COMPONENT_MIGRATION_CHECKLIST.md)
is the reusable per-component template and is intentionally blank.

Three Vue files that were referenced nowhere have been **deleted** (2026-10-01,
in their own revertible commit, uncommitted at the time of writing):
`frontend/src/components/Step1GraphBuildRefactored.vue` (426 lines),
`frontend/src/components/EvidenceBadge.vue` (290 lines), and
`frontend/src/components/HistoryDatabase.vue` (1013 lines — removed from
`Home.vue` by the Direction C redesign `d57898f`). Nothing imported any of
them, no route rendered them, and the frontend suite passes without them (290 tests
in 32 files, measured 2026-10-02; an earlier revision here said 200 in 28). `HistoryDatabase.vue` was the only one with a note
warning against reviving it; see
[`NEXT_STEPS_ROADMAP.md`](NEXT_STEPS_ROADMAP.md). **Correction:** an earlier
revision of this paragraph called the comment at
`frontend/src/__tests__/branch-lineage.spec.js:41-42` stale. It has since been
corrected — it now states that `HistoryDatabase.vue` "has since been deleted".
Do not restore the older wording.

### Blocked on operator actions, not on engineering

`../deployment/README.md` § *Deployment blockers* (lines 178-234) records seven
deployment blockers.
Blocker 6 (missing `scripts/release/verify`) is closed. The rest gate a
**deploy**, not the documentation or feature work, and must not be scheduled as
engineering tasks:

- Blockers 1, 3, 4, 7 — credential revocation and rotation, operator-supplied
  secrets, and disabling provider-dashboard autodeploy. No code change closes
  these.
- Blocker 2 — `npm run setup:backend` is repaired in `package.json:7`
  (`uv sync --frozen --group dev`).
- Blocker 5 — the runbook forbids the only runnable topology from OneDrive,
  Dropbox, NFS, or SMB (`../release/RUNBOOK.md:217-222`). This checkout is
  under OneDrive, so a deployer must clone to a local disk first.

The Product Truth Contract
and the Product Truth Claim Block
implementation detail in this document. Where the implementation and the truth
contract disagree, the truth contract wins until superseded by an accepted
ADR.

## How to read the rest of the architecture documentation

- [`data-model.md`](data-model.md) — the aggregates, the canonical store, the
  target persistence model, and the divergence between current and target.
- [`state-machines.md`](state-machines.md) — the four independent state
  machines (preparation, execution, environment, report) and the four-state
  task envelope that wraps them.
- [`adr/`](adr/README.md) — every accepted architecture decision. The ADR set
is growing; take the current count from `tools/validate_docs.py` rather than
from a number quoted here.
- [`../exec-plans/`](../exec-plans/README.md) — the implementation program
  in dependency order.
- [`../release/ACCEPTANCE.md`](../release/ACCEPTANCE.md) — what every
  release must produce.
