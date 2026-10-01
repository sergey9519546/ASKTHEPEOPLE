# ASKTHEPEOPLE — Next 30 Tasks

Derived from the `AGENTS.md` audit of 2026-10-01, then **corrected after a
reachability re-check** (see "Corrections to the first draft"). Every task
carries the `file:line` evidence that justifies it and a test that fails without
it.

## Decisions taken (settled; do not re-litigate)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Migrations become canonical.** The 16 tables in `backend/migrations/versions/` are the source of truth. `backend/app/db/schema.py` is reconciled to match. Matches ADR-0012 and exec-plan 08 Fix 1. | T1–T6 |
| D2 | **Multi-tenancy stays deferred.** `DEV_ACTOR_CONTEXT_ENABLED` remains refused in production. Tenant isolation is an accepted pre-release risk, documented not solved. | No task builds an identity model. |
| D3 | **Scope is the full backlog** — correctness, hygiene, and the six gates' remaining work. | 30 tasks across 5 waves. |
| D4 | **The filesystem lifecycle stays the current runtime; the `dw_*` aggregates stay TARGET.** `SimulationManager` must not re-mirror into `dw_runs`. This is pinned by a passing test and must not be reverted. | Constrains T2–T4 and T6. |

## Non-negotiable constraints for every task

- `npm run verify` passes, or the delta is explained with `file:line`.
- `python tools/validate_docs.py` → `Errors: 0, Warnings: 0`.
- `AGENTS.md` §0: **no number copied from a document or from `AGENTS.md` may be
  written anywhere without re-measuring it first.** Run the command, quote output.
- Any task touching a truth surface (copy, disclosure, prompt, model, retention,
  export) carries an impact statement, a rollback plan, and a `version` +
  `last_reviewed` bump on the affected document.
- Gate status is recorded in exactly one place: `docs/architecture/index.md`
  § *Status of record*. No task restates it elsewhere.
- **Re-verify reachability before acting.** A module can be substantial, tested,
  and still unreachable. The first draft of this plan got that wrong twice; see
  below.

## Corrections to the first draft

Two defects found by re-checking import reachability. Both changed the plan.

1. **`RunRepository` and `PathRepository` have no production importer.** They
   are referenced only in docstrings (`services/simulation_manager.py:205`,
   `services/path_repository.py:6`) and in one test docstring. The first draft
   treated the 16-table schema as actively exercised. It is not.
2. **`DecisionLensRepository` is not a SQL repository.** It is filesystem-backed,
   constructed as `DecisionLensRepository(sim_dir, production=...)`
   (`services/decision_lens_repository.py:65`), and imports no engine. The first
   draft implied it wrote to the migration schema. It does not.

**The corrected picture.** Only three repositories issue SQL against the
migration tables, and each is reachable only when
`Config.USE_SUPABASE_PERSISTENCE` is `True`, which **defaults to `False`**
(`config.py:321-322`):

| Repository | Reached from | Gate |
|---|---|---|
| `ProjectRepository` | `models/project.py:205` via `_delegate_to_canonical` | `USE_SUPABASE_PERSISTENCE` |
| `SourceRepository` | `api/routes/source_routes.py:161,232,308` | flag + route flag |
| `RunRepository` | **nothing** | unreachable |
| `PathRepository` | **nothing** | unreachable |
| `DecisionLensRepository` | live, but filesystem-only | always on |

**So the schema divergence is not an active data-corruption risk. It is a
trap**: the moment someone sets `USE_SUPABASE_PERSISTENCE=true` against a database
that only has the ORM's six tables, `SourceRepository` and `ProjectRepository`
issue SQL against tables that were never created. Wave 1 is therefore scoped as
*make the trap non-silent*, not as *migrate production data*.

## Dependency graph

```
T1 ──► T2 ──► T3 ──► T4 ──► T5 ──► T6
T15 ──► T16 ──► T17
T7–T14   (independent, parallelizable)
T18–T24  (independent, parallelizable)
T25 ──► T26 ; T27 ; T28 ; T29 ; T30
```

---

## Wave 1 — Make the schema trap non-silent (D1, D4)

**Reorder note:** the `SimulationManager` canonical-mirror withdrawal is already
done and pinned by a test; nothing in this wave may regress it. See D4.

### T1 — Record the schema-canonicalization decision
Write ADR-0013 (or amend ADR-0012) declaring migrations canonical, and record
three things the first draft missed:
- the primary-key conflict: `384c98f88d53_initial_schema.py:25` declares
  `sa.Column('id', sa.Integer(), autoincrement=True)` while
  `app/db/schema.py:11,18,28,38,47,57` declare `Column(Uuid, primary_key=True,
  default=uuid.uuid4)`. Same table names, incompatible key types.
- the reachability table above — which repositories are live, which are not.
- that Alembic is invoked by **no** Dockerfile, compose service, or CI job;
  `create_app` calls `init_db` → `Base.metadata.create_all` at boot
  (`app/db/__init__.py:25-27`, called from `app/__init__.py:167`).
- **Acceptance:** ADR accepted, `adr/README.md` updated, validator passes.
- **Owner:** `askthepeople-persistence-engineer`.

### T2 — Add the 4 ORM-only tables as migrations
`organizations`, `agent_profiles`, `attempts`, `observations` exist in the ORM
(`app/db/schema.py:9,36,45,55`) and in no migration. After this task the
migration set is a strict superset of the ORM set.
- **Blocked by:** T1.

### T3 — Converge primary keys to `Uuid`
The `384c98f88d53` revision (the only one with `down_revision = None`,
`:15-16`) is the base and is Integer-keyed. Rewrite it, or add a new head
revision that converts `projects`/`simulations`.
- **Blast radius is small:** `USE_SUPABASE_PERSISTENCE` defaults off, so no
  deployment is currently on the canonical store. Confirm before assuming.
- **Test:** `upgrade head` → `downgrade -1` → `upgrade head` twice, idempotent.
- **Blocked by:** T2.

### T4 — Make Alembic the only schema-creation path
Remove `init_db`/`create_all` from the boot path; make `alembic upgrade head` an
explicit, tested deploy step.
- **Risk:** this can leave a deploy with no schema if the step is skipped. Ship
  it as an explicit step with a test; do **not** make it fail-closed in the same
  commit.
- **Blocked by:** T3.

### T5 — Add the schema-parity test
The test whose absence let this divergence survive. Fails when a table exists in
one definition and not the other, with an explicit allowlist for
`organizations`/`agent_profiles`/`attempts`/`observations` until T2 lands.
- **Test:** add a table to `schema.py` only → the new test must fail.

### T6 — Fail loudly when the flag is on but the schema is absent
Today, `USE_SUPABASE_PERSISTENCE=true` against a `create_all` database fails
late, at first query, with a raw `UndefinedTable` error.
`SourceRepository._engine` already raises `canonical_store_not_configured`
(`services/source_repository.py:42`) — that is the right shape; extend it to
verify the expected tables exist, not just that a URL is configured.
- **Test:** flag on + missing table → clear error naming the missing table and
  the migration step.
- **Blocked by:** T4.

---

## Wave 2 — Dead code and shipped hazards (independent; parallelize)

### T7 — Delete the unmounted FastAPI router
`api/capability.py` (244 lines) builds an `APIRouter` inside a Flask app;
nothing imports it. Collaborators: `services/capability_registry.py`,
`schemas/capability.py`.
- **Note:** `capability_registry.py:17` also imports `app.schemas.capability`, so
  the island is not strictly one-directional — check before deleting.

### T8 — Delete the three dead Vue components
`Step1GraphBuildRefactored.vue` (426), `EvidenceBadge.vue` (290),
`HistoryDatabase.vue` (1,013). **Separate revertible commit** — large enough
that bundling them with a feature change makes review harder for no benefit.

### T9 — Delete the spent one-shot scripts
Root `patch.py` (already applied; re-running corrupts `api/graph.py`),
`backend/patch.py`, `verify_check.py`, `run-evaluation-pipeline.sh` (references a
renamed `views/Process.vue`), `setup-local.sh` (obsolete pyenv flow).

### T10 — Resolve the backtest/optimization island
~2,900 lines with no production importer: `simulation/hybrid_simulator.py`,
`optimization/*`, `data/outcome_fetcher.py`, `models/baseline_library.py`,
reachable only from `evals/first_backtest.py` (itself unimported).
- **This is a decision, not a cleanup** — record either way in the Status of
  record. `baseline_library.py:33` raises `NotImplementedError` by design.
- **Note the pattern:** this is the same *shape* as T1's reachability finding
  (substantial, tested, unreachable). Apply the same check before assuming the
  `dw_*` repositories are live.

### T11 — Resolve the two conflicting `vercel.json`
Root builds `frontend/dist`; `frontend/vercel.json` builds `dist`. Pick one.
Do not create a third.

### T12 — Remove the abandoned `supabase/` scaffold
CLI-default `config.toml`, no migrations, no referencing code, stray `.start.log`.
- **Caution:** `USE_SUPABASE_PERSISTENCE` is a real flag and `supabase_client.py`
  is live code. This task removes only the empty scaffold directory.

### T13 — Resolve the two committed frontend builds
`frontend/dist/` and `static/dist/` are both committed. Keep one, gitignore the
other, record the decision.

### T14 — Purge the 41 `.pytest_*` directories
Untracked-but-ignored under `backend/` (`.gitignore:45`). Local debris. Do not
add a blanket exception; do not cite their contents as evidence.

---

## Wave 3 — Truth-contract enforcement gaps (the CI job is weaker than it looks)

### T15 — Fix the dead `docs.yml` paths
`SCAN_PATHS` and the wordmark allowlist still name `docs/product/**`, which does
not exist (folded into ADR-0001 at `3f27ca7`).
- **Evidence:** `.github/workflows/docs.yml:94-97`, `:129`.
- **Effect:** the wordmark and prohibited-language gates are partly inert.

### T16 — Extend prohibited-language enforcement to `backend/app/**`
No enforcement exists on the backend. The disclosure constants in
`services/claim_boundary.py` and error strings in `api/` are user-facing.
- **Approach:** reuse `tools/lint_frontend_truth.mjs`'s `TERM_PATTERNS` against
  Python string literals; add as a pytest module.
- **Caution:** many hits will be legitimate negations ("not a forecast"). Use a
  narrow explicit allowlist and review every hit.

### T17 — Cover the path-filter gap
`docs.yml` runs only when `docs/**`, the validator, or the workflow change. **A
frontend or backend change is not covered by the doc gate at all.** Either
un-filter `docs.yml` or mirror the checks into `ci.yml`, which runs on every push
and PR.
- **Blocked by:** T15, T16.

---

## Wave 4 — Documentation drift (independent; parallelize)

### T18 — Add exec-plans 08/09 to the order table
Neither is in `docs/exec-plans/README.md`'s order table; neither has a dependency
narrative.

### T19 — Fix root `README.md` plan count
Still says "8 plans" against a directory holding ten numbered plans (00–09).

### T20 — Purge quoted counts repo-wide
Replace hardcoded document/test/file counts with either a measurement command or
an explicitly dated historical label. `GATE_0_RELEASE_NOTES.md` already models
the correct treatment.

### T21 — Fix the buildplan's Truth Rail string
`ACTIONS + ANSWERS: SYNTHETIC` appears in three places; the enforced string is
`GENERATED` (`tools/lint_frontend_truth.mjs:11`, asserted by
`product-truth-guard.spec.js`).
- **Caution:** truth-surface change — needs an impact statement.

### T22 — Make the validator check anchors
`validate_docs.py` strips `#fragment` and never validates it. Two fabricated
anchors shipped and survived; this class of bug will recur.
- **Scope:** resolve `#fragment` to a heading slug within the target file.
- **Test:** a deliberately broken anchor must fail the validator.

### T23 — Re-verify exec-plan 08's acceptance checkboxes
Several are stale. "Health check is a SELECT 1 liveness only" is **false**:
`api/health.py:72-117` already runs deadline-bounded database, Redis, and Celery
probes concurrently and reports `degraded`/`error`. Re-verify each unchecked box
rather than rebuilding it.

### T24 — Fold this plan's outcomes into `AGENTS.md`
Update §9.2 as each task lands; strike resolved items with the date and evidence,
following the convention already in that file. Add the reachability lesson: a
substantial, tested module may still be unreachable.

---

## Wave 5 — Gate work that does not require an identity model (D2)

Each carries a "tenant scoping not yet enforced (D2)" note. All independent of
each other and of Waves 1–4.

### T25 — Decompose `api/report.py`
23 handlers in 1,437 lines — the largest remaining monolithic cluster and a real
Gate 1 remainder.
- **Test:** each moved handler returns 404 before registration and 200 after,
  proving it is actually routed.

### T26 — Complete schema enforcement across legacy handlers
Typed schemas and `application/` + `domain/` foundations exist; legacy handlers
still accept untyped payloads. Finish the route responsibility contract.

### T27 — Transactional (fenced) artifact writes
Report/graph delivery uses a durable execution fence in
`models/task.py`, but artifact writes are not transactional under it.

### T28 — Outbox events
Required by ADR-0012 for canonical persistence. No implementation exists.

### T29 — Observability (Gate 4 — the only NOT STARTED gate)
No metrics or tracing; Sentry is PARTIAL. Needs metrics instrumentation, SLOs,
cost budgets, alerting, and a decision on the process-local `SimulationRunner`
that forces `--workers 1`.
- **Rate limiting:** `RATELIMIT_STORAGE_URI` defaults to in-process `memory://`
  and is deliberately not derived from `REDIS_URL`, so limits are per-process and
  do not survive a restart. Moving it to Redis is part of this task — see
  Open Question 3.

### T30 — Prompt registry adoption
Most prompts are still inlined rather than versioned in the registry
(ADR 0004, `docs/ai/PROMPT_REGISTRY.md`).

---

## Validation

Per task: `npm run verify` (doc validator → frontend tests → build → backend
tests → gitleaks) and `python tools/validate_docs.py` clean.

Per wave: re-run T5's parity test, then re-read
`docs/architecture/index.md` § *Status of record* and update **only that table**
for any gate that moved.

**Do not** mark a gate closed on the strength of a passing test suite alone —
Gate 2's "durable" and Gate 3's "canonical" claims are both qualified by
deployment behavior that no test exercises.

**Before starting any task that acts on a module:** confirm it is actually
reachable (`rg` its importers, or read its docstring's own claim). T1, T10, and
the first draft of this plan all failed that check.

## Risks

| Risk | Mitigation |
|---|---|
| T3/T4 could leave a deploy with no schema | Never combine with fail-closed in one commit; migration step is explicit and tested before T6 lands |
| T4 removes `create_all` while a deployment is mid-flight | Blast radius is bounded by D4: the flag defaults off, so no deployment is on the canonical store. Confirm before starting. |
| T16 produces false positives on legitimate negations | Narrow allowlist; review every hit |
| T10 may delete research value | Decision, not cleanup; record either way |
| The tree changes between sessions | `git log -1 --oneline` and `git status --short` before every task; never trust a line number from memory |
| 30 tasks become 30 half-done PRs | Waves 1 and 2 must land before Wave 5 |

## Open questions

1. **Is the backtest/optimization island (T10) research asset or dead weight?**
   Needs a human call; the code cannot answer it.
2. **T29 rate limiting:** move `RATELIMIT_STORAGE_URI` to Redis now, or accept
   per-process limits until horizontal scaling lands?
3. **`RunRepository` / `PathRepository` (unreachable, ~525 lines):** wire them,
   delete them, or keep them as the ADR-0012 reference implementation with an
   explicit "not on any runtime path" README? Currently they are none of those —
   they are simply unmentioned.
