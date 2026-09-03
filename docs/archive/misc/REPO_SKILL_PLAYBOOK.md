# ASKTHEPEOPLE repository skill playbook

This is the operational skill map for this repository. It is not a generic
software-engineering checklist. Select skills from the files and behavior being
changed, then apply the repository contract in `AGENTS.md` and the normative
documents under `docs/`.

## Repository facts that control skill selection

- Frontend: Vue 3, Vue Router, Vite, JavaScript, D3, Vitest, and axe CLI.
- Backend: Flask, Flask blueprints, Flask-Sock, Celery, Redis, Python 3.11+.
- Persistence: SQLite/filesystem in the current implementation; SQLAlchemy,
  Alembic, PostgreSQL/Supabase, and MinIO are transition surfaces.
- Simulation: OASIS/CAMEL, process/IPC runtime, profile and behavioral model
  services, OpenAI-compatible providers, Zep Cloud.
- Product boundary: synthetic scenario exploration, not polling, opinion
  measurement, causal inference, or a substitute for real people.
- Required validation: `python tools/validate_docs.py`, `npm run test`,
  `npm run build`, and `cd backend; .\.venv\Scripts\pytest -q` as applicable.

## Routing algorithm

1. Read `docs/architecture/index.md` and the nearest applicable ADR before
   changing architecture, state, storage, prompts, security, or user-facing
   claims.
2. Map changed files to one or more rows below.
3. Activate the primary skill and every listed companion skill when its risk is
   present; do not activate unrelated framework skills.
4. Inspect the complete runtime chain: frontend import/mount -> API route ->
   service/task -> persistence/external provider -> response/export.
5. Add or update a regression test for the failure mode, not just a happy path.
6. Run the row’s required command and record limitations honestly.

## File-precise routing

| Changed files or behavior | Primary skill | Companion skills | What the skill must inspect here |
|---|---|---|---|
| `backend/app/api/**`, `backend/app/schemas/**` | `api-design` | `backend-patterns`, `security-review`, `python-testing` | Blueprint prefix, route registration, auth/parse/authorize/dispatch/present order, typed errors, status codes, malformed JSON, missing resources |
| `backend/app/api/ws.py`, `/api/auth/ws-ticket`, frontend WebSocket code | `security-review` | `python-testing`, `verification-loop` | Ticket signature, expiry, audience/simulation scope, replay, unauthorized handshake, disconnect behavior, client recovery |
| `backend/app/tasks/**`, `backend/app/celery_app.py`, `backend/app/models/task.py` | `backend-patterns` | `python-testing`, `enterprise-agent-ops`, `measure-instrumentation-spec` | No route-owned worker/thread, task idempotency, retry classification, cancellation, Redis state atomicity, leases/heartbeats, worker health and metrics |
| `backend/app/db/**`, `backend/alembic/**`, `*_repository.py` | `database-migrations` | `backend-patterns`, `python-testing`, `security-review` | Immutable Alembic history, expand/contract migration, transaction boundaries, workspace/tenant predicates, SQLite/Postgres parity, rollback and partial-failure behavior |
| `safe_path.py`, `safe_url.py`, uploads, `url_fetcher.py`, source routes | `security-review` | `python-testing`, `ai-regression-testing` | Traversal, symlink/absolute-path escapes, SSRF redirects and private IPs, MIME/magic bytes, size limits, encoding, provenance, cleanup |
| `simulation_artifacts.py`, `simulation_observation_store.py`, Supabase/MinIO code | `security-review` | `database-migrations`, `backend-patterns`, `python-testing` | Canonical artifact ownership, object/path keys, retention, cross-workspace access, filesystem/object-storage transition assumptions |
| `backend/app/simulation/**`, `simulation_runner.py`, `simulation_ipc.py` | `python-patterns` | `python-testing`, `ai-regression-testing`, `enterprise-agent-ops` | Process lifecycle, IPC framing, timeout/termination, deterministic controls, orphan cleanup, concurrent runs, failure state and observability |
| `big_five.py`, `prospect_theory.py`, `diffusion_model.py`, `constraint_engine.py`, `game_theory.py`, `calibration_metrics.py` | `python-patterns` | `python-testing`, `eval-harness`, `ai-regression-testing` | Numeric invariants, seed reproducibility, invalid domains, overflow/size bounds, calibration interpretation, and actual production call sites |
| `backend/app/prompts/**`, provider adapters, `report_agent.py` | `agentic-eval` | `ai-regression-testing`, `security-review`, `documentation-lookup` | Prompt registry/version binding, tool permissions, structured-output refusal, provider timeout/retry, prompt injection, disclosure, no chain-of-thought retention |
| `export_service.py`, `report_evidence.py`, `claim_boundary.py`, report routes | `ai-regression-testing` | `api-design`, `doc-coauthoring`, `security-review` | Export derives from canonical server records, provenance is not fabricated, disclosures survive CSV/PDF/JSON, response schema and error behavior |
| `frontend/src/components/**`, `views/**`, `assets/**` | `frontend-design` | `frontend-patterns`, `verification-loop` | Civic Wayfinding, stable structure, content hierarchy, focus order, WCAG semantics, reduced motion, truth-critical copy, CSS import/build behavior |
| `frontend/src/composables/**`, stores, router, polling | `frontend-patterns` | `ai-regression-testing`, `verification-loop` | Vue reactivity, watcher cleanup, stale request races, route persistence, loading/error/empty states, API response shape |
| Guidance files (`useGuidedContext`, `useAdaptiveUI`, `ProgressiveGuidance`, `ContextualHelp`) | `frontend-design` | `frontend-patterns`, `ai-regression-testing`, `webapp-testing` | Capability × phase matrix, hidden-content reveal path, expansion state, keyboard/screen-reader behavior, mounted integration rather than example-only code |
| `frontend/src/__tests__/**`, `vitest.config.js` | `ai-regression-testing` | `verification-loop` | Regression contracts for changed behavior, null/non-object API responses, sandbox/production parity, test isolation, realistic fixtures |
| Browser workflow or accessibility integration | `webapp-testing` | `frontend-design`, `verification-loop` | First verify a browser runner exists; do not call Vitest component tests E2E coverage |
| `Dockerfile*`, `docker-compose.yml`, `Procfile` | `docker-patterns` | `deployment-patterns`, `verification-loop`, `enterprise-agent-ops` | Web/worker separation, health checks, mounts, env names, startup order, graceful shutdown, pinned images and local/production differences |
| `vercel.json`, `railway.toml`, `render.yaml`, deploy workflows | `deployment-patterns` | `verification-loop`, `security-review` | Build guard, unsupported platform blockers, secret/config separation, artifact output, target environment, rollback evidence |
| `.github/workflows/**`, `docs/release/**`, SLO/telemetry work | `enterprise-agent-ops` | `measure-instrumentation-spec`, `verification-loop`, `documentation-lookup` | Actual metrics/traces/logs, release evidence, failure budgets, incident actions, rollback, and current vs target status |
| `docs/**`, `AGENTS.md`, product copy, terminology | `doc-coauthoring` | `develop-adr`, `documentation-lookup`, `verification-loop` | Authority hierarchy, file/line citations, truth-contract vocabulary, status labels, links, version/review metadata, validator |
| Whole-repository audit, hallucination or contradiction review | `skill-stocktake` | `security-review`, `ai-regression-testing`, `verification-loop`, `doc-coauthoring` | Docs -> imports -> call sites -> routes -> persistence -> tests -> deployment; separate “exists” from “wired” and “released” |

## Skill combinations by concrete task

### Adding a Flask endpoint

Use `api-design + backend-patterns + security-review + python-testing`.

- Start at the owning blueprint and confirm registration in
  `backend/app/api/__init__.py`.
- Do not add handlers back to `backend/app/api/simulation.py`; use the
  per-resource route modules.
- Check auth, workspace ownership, schema validation, status codes, and
  error-envelope compatibility.
- Test missing auth, malformed input, invalid IDs, cross-workspace access,
  downstream failure, and success.

### Changing simulation execution

Use `python-patterns + backend-patterns + python-testing +
ai-regression-testing + enterprise-agent-ops`.

- Keep long-running work out of routes.
- Trace Celery task -> runner -> IPC/process -> observation/artifact store.
- Test duplicate submission, cancellation, timeout, worker restart, partial
  artifacts, and stale task state.
- Do not claim durable workflow support while leases, fencing, heartbeats, and
  retry semantics remain target/partial.

### Changing AI behavior or reports

Use `agentic-eval + ai-regression-testing + security-review +
documentation-lookup`.

- Bind prompt/model/provider versions.
- Keep source material data separate from instructions.
- Test invalid structured output, provider timeout, refusal, injection-like
  source text, disclosure presence, and provenance.
- Never optimize wording in a way that weakens the product truth boundary.

### Changing the Vue workflow

Use `frontend-design + frontend-patterns + ai-regression-testing`.

- Identify the mounted view from `MainView.vue` or the router before editing an
  “example” component.
- Test first-use, learning, practiced, expert, loading, empty, error, and
  recovery states.
- Verify keyboard focus, labels, dialogs, reduced motion, responsive layout,
  and API failure presentation.
- A new component is not delivered until the live import path uses it.

### Changing storage or migrations

Use `database-migrations + security-review + backend-patterns +
python-testing`.

- Treat current SQLite/filesystem behavior and PostgreSQL/object-storage design
  as separate states.
- Check tenant/workspace filters at query level, not only at route level.
- Verify migration upgrade, downgrade/forward repair strategy, backfill
  safety, and artifact consistency.

### Preparing a release

Use `verification-loop + deployment-patterns + docker-patterns +
enterprise-agent-ops + doc-coauthoring`.

- Run only commands that exist in this repo.
- Verify build guards, web/worker topology, environment contracts, health
  checks, release evidence, and rollback.
- Report `CURRENT`, `PARTIAL`, `TARGET`, and `TRANSITION` accurately.

## Explicit exclusions

- Do not use React/Next.js, Django, Laravel, Prisma, or Drizzle skills as
  implementation instructions in this Vue/Flask/SQLAlchemy repository.
- Do not use `prompt-optimizer` for direct implementation or skill inventory;
  product and security contracts outrank prompt polish.
- Do not use `security-scan` as a substitute for application threat modeling;
  it is mainly for Claude configuration.
- Do not use deployment skills for a feature-only change.
- Do not claim E2E, production integration, or release readiness from a passing
  unit test, exported symbol, local build, or documentation validator alone.
