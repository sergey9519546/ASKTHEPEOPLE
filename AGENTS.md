# AGENTS.md

> Operational contract for any AI agent working on this repository — the
> orchestrator runtime and every specialist, in any runner (Kilo, Claude Code,
> Codex, or anything else).
>
> **This file is a navigation map and a set of enforceable prohibitions, not a
> second copy of the status.** Everything that can go stale lives in `docs/`;
> everything that can go wrong lives here. If a claim in this file disagrees
> with a cited file, the cited file wins and this file is the bug.
>
> The commit reference below is a *measurement baseline*, not a claim about
> where `main` is. Check `git log -1 --oneline`; do not assume.

---

## 0. The rule that governs this file

**§9 of this document exists because an earlier agent got it wrong, and I got it
wrong twice.** Every hard number here — a line count, a test count, a file size,
a `git status` listing — was correct when written and wrong within days. Several
were wrong on the day they were written.

So:

1. **This file carries no measured snapshot.** It gives you the *command* that
   produces each number, not the number. Run the command; quote its output.
2. **Any number you copy out of this file must be re-measured before you write
   it into a commit, a document, or a status claim.** §9.1 is the re-measurement
   script.
3. **A `file:line` citation in this file may be off by a few lines.** File
   contents shift under edits. Cite the symbol, confirm with a read, then use the
   number you actually saw. Do not trust a number here without opening the file.

This is not false modesty. The drift this prevents is real and is catalogued in
§9.2 — the same repo that has a validator for documents has three documents
quoting counts that are wrong.

---

## 1. Read these five things before you touch anything

```bash
python tools/validate_docs.py   # doc system integrity. 0 errors, 0 warnings, or the tree is broken.
git status --short              # the tree is dirty and changes under you; see §9
git log -1 --oneline            # the commit every file:line claim is measured against
```

Then read, in this order:

1. [`docs/architecture/index.md`](docs/architecture/index.md) — **the** entry
   point. Its §[Status of record](docs/architecture/index.md#status-of-record)
   is the single authoritative statement of gate status, shipped work, feature
   backlog, and operator-blocked items. **Do not restate gate status in any other
   document, including this one.** Six documents previously asserted it
   independently and drifted into contradicting each other and the code; that is
   the failure this file exists to prevent.
2. [`docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md`](docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md) — the product category and the truth boundary. Accepted.
3. [`docs/README.md`](docs/README.md) — the documentation system, its authority
   hierarchy, and its change-control rule.
4. The ADR for whatever you are about to touch (`docs/architecture/adr/README.md`).
5. [`docs/release/ACCEPTANCE.md`](docs/release/ACCEPTANCE.md) and
   [`docs/release/RUNBOOK.md`](docs/release/RUNBOOK.md) if your change could
   ship.

**Never assert what is or is not implemented without a `file:line` reference.**
"The system persists X" is not a sentence. `backend/app/services/run_repository.py`
— a named file and line you read — is.

> **Known hazard:** `index.md` was the authority *and* was itself stale. Its
> citations into `backend/app/__init__.py` were off by 20–110 lines and two of
> its buildplan anchors were fabricated; all were corrected on 2026-10-01. It is
> far better than it was, but a `file:line` in any document is still cheaper to
> re-read than to trust. This file carries the same risk; see §0.

---

## 2. The truth contract is not negotiable

ASKTHEPEOPLE is a **Synthetic Decision Explorer**. It is not a poll, survey,
public-opinion measure, digital twin, causal model, behavioral forecast, or a
substitute for contact with real people. Human respondents: 0. Output origin:
generated. The run is not a forecast.

These five facts are the Truth Rail and are permanent, non-dismissible, and
carried on every primary surface
([`frontend/src/components/TruthRail.vue`](frontend/src/components/TruthRail.vue),
`aria-label` on the `.truth-rail` element):

```text
ACTIONS + ANSWERS: GENERATED
HUMAN RESPONDENTS: 0
NOT A FORECAST
SOURCES: STARTING CONDITIONS ONLY
HUMAN VALIDATION: OUTSIDE THIS RUN
```

**The exact first line is `ACTIONS + ANSWERS: GENERATED`.** The build plan
(§13) still writes `SYNTHETIC` there in three places — search it before
trusting a build-plan quote. The code and its linter are authoritative:
`tools/lint_frontend_truth.mjs` requires `GENERATED` in its
`REQUIRED_TRUTH_RAIL_FACTS`, and
`frontend/src/__tests__/product-truth-guard.spec.js` asserts it. Do not "fix"
the code to match the build plan.

### Prohibited in user-facing copy

The naked `ASKTHEPEOPLE` wordmark without its `SYNTHETIC DECISION EXPLORER`
descriptor; and these outcome claims: *predict what people will do, predict
public response, know what people think, human-level accuracy, digital twin of
your audience/users/customers/people, bias-free personas, scientifically proven
simulation, representative synthetic sample, ask thousands of people instantly,
validate the decision with/by this product*, and the ~33-term list in
`tools/lint_frontend_truth.mjs`'s `TERM_PATTERNS` (forecast, consensus,
probability, confidence, representative, majority, popularity, prevalence,
sample, survey, poll, respondent, …).

Synthetic profile counts must never be presented in a way that resembles a
sample size. Role labels supply no behavioral evidence — see the `reasoning`
field of `entity_type_registry.json`.

### Where this is actually enforced — and where it is not

| Surface | Enforcement | Status |
|---|---|---|
| `frontend/src/**` accessible labels (`aria-label`, `title`, `placeholder`, `alt`, `content`) | `tools/lint_frontend_truth.mjs`, imported by `product-truth-guard.spec.js` | **live** — runs on every `npm test` |
| `frontend/src/**` **visible text nodes** | nothing | **unenforced** — the linter's `VISIBLE_ATTRIBUTE_PATTERN` matches attributes only, so body text is invisible to it |
| `docs/**`, root `README.md` | the two grep steps in `.github/workflows/docs.yml`, plus `scripts/release/check-docs-gates.sh` as gate 2 of `npm run verify` | **live** since 2026-10-01 |
| `backend/app/**` | nothing | **unenforced** — you are the linter |
| `frontend/dist/**`, `static/dist/**` | nothing | build output; never edit, never cite as source |

Three structural facts about that CI job, all corrected on 2026-10-01:

- **The two grep gates were silently inert and had never once fired.** Each used
  a multi-line parenthesised ERE. GNU grep cannot compile that
  (`Unmatched ( or \(`), and because both pipelines ended in `|| true` the error
  was swallowed, the hit list came back empty, and the gates reported PASS
  unconditionally. The wordmark gate had never caught a violation in the
  repository's history. Both patterns are now single-line, and each gate asserts
  its own patterns compile — grep exits 2 on a regex error and 1 on a clean
  no-match, so testing "did it match?" would fail on a clean tree.
- **The wordmark gate was also logically wrong.** It flagged *any* occurrence of
  the wordmark, so a correctly branded line was a violation too, which is why it
  needed an ever-growing allowlist. It now flags the wordmark only where an
  approved descriptor does not accompany it, using the same five descriptors as
  `tools/lint_frontend_truth.mjs`. Scope is the user-facing surfaces
  (`README.md`, `docs/release/`, `docs/privacy/`) because an all-of-`docs/`
  scope produced only internal-prose false positives. Current tree: zero
  violations.
- The dead `docs/product/**` `SCAN_PATHS` and allowlist entries are gone; the
  truth contract is cited as ADR-0001, where that directory went. **The job is
  still path-filtered**, but the filter now also covers `frontend/src/**`,
  `backend/app/**`, `AGENTS.md` and `README.md`, so a frontend or backend change
  no longer bypasses it entirely.

---

## 3. Repository map

Counts are approximate and were measured at `b868477`; re-measure with §9.1
before quoting any of them.

| Path | What it is |
|---|---|
| `backend/app/api/routes/` | The live simulation HTTP surface — the decomposed per-resource modules, registered by `api/routes/__init__.py` |
| `backend/app/api/simulation.py` | **Helpers only. Zero routes.** Exists because every `routes/` module imports its helpers |
| `backend/app/api/report.py` | The largest remaining handler cluster and still monolithic — a real Gate 1 remainder |
| `backend/app/api/graph.py` | Legacy graph handlers |
| `backend/app/domain/` | Pure frozen state machines and value types. No Flask, no Celery, no I/O |
| `backend/app/application/` | Use-case services. Currently one module |
| `backend/app/services/` | Everything else: model layer, repositories, runtime, Zep, reporting |
| `backend/app/tasks/` | Celery tasks; the beat schedule is in `celery_app.py` |
| `backend/app/models/task.py` | Redis task state, leases, fencing tokens, idempotency |
| `backend/app/config.py` | All env reads and the fail-closed credential rules; `Config.validate()` |
| `backend/app/__init__.py` | App factory, the global auth hook, CORS, security headers, error scrubbing |
| `backend/app/utils/` | `safe_path.py`, `safe_url.py`, `llm_client.py`, `input_policy.py` — the security primitives |
| `backend/app/celery_app.py` | Celery instance and the beat schedule |
| `backend/tests/` | 123 test modules. **No custom pytest markers** — nothing is excluded from a default run |
| `backend/migrations/versions/` | 3 revisions, linear, head `b2c3d4e5f6a7` |
| `frontend/src/` | Vue 3 + Vite 7 + vue-router 4, **no Pinia** (module-level `reactive()` singletons), D3 |
| `frontend/src/assets/design-tokens.css` | Brutal-Editorial token set. Contains a large deprecated-alias block kept for backward compatibility — see §5 rule 18 |
| `frontend/src/components/` | Includes three dead files; see §9.2 |
| `docs/` | The normative authority: 12 accepted ADRs, a validated validator, ~93 markdown files |
| `tools/validate_docs.py` | The doc validator. **This is the real linter for this repo** |
| `tools/lint_frontend_truth.mjs` | The frontend truth-contract linter |
| `scripts/release/verify` | The single release verification entry point |

To find the biggest files rather than trusting a list:

```bash
Get-ChildItem backend/app -Recurse -Filter *.py |
  Sort-Object { (Get-Content $_.FullName).Count } -Descending |
  Select-Object -First 10 Name, @{n='Lines';e={(Get-Content $_.FullName).Count}}
```

The heaviest files are in `services/` (the report agent and the simulation
runner dominate), then `models/task.py` and `api/report.py`. Do not quote a
list from memory — the previous version of this file did, and got two entries
wrong.

---

## 4. The agent team

The orchestrator plans, sequences, delegates, verifies, and re-routes on domain
conflict. It owns no domain. Eight specialists carry the domains; the `Owner`
column of the gate table in `index.md` uses these exact identifiers.

| Agent | Owns | Read first |
|---|---|---|
| `askthepeople-docs-steward` | `docs/` integrity, the validator, ADRs, truth-contract enforcement, archive reconciliation, CI doc gates | `docs/README.md`, `INTEGRATION_GUIDE.md`, `docs/exec-plans/00-repository-census-and-governance.md` |
| `askthepeople-architect` | `backend/app/api/` decomposition, `application/`, `domain/`, the route responsibility contract, the typed boundary, the data model | `docs/architecture/*`, ADRs 0003 / 0006 / 0011 / 0012 |
| `askthepeople-persistence-engineer` | PostgreSQL schema, object storage, outbox events, attempts/manifests, immutable artifacts, tenant isolation at the query layer | ADRs 0002 / 0012, `docs/architecture/data-model.md`, `docs/privacy/*` |
| `askthepeople-orchestration-engineer` | Job system, workers, leases, fencing, heartbeats, retries, cancellation, the durable run state machine | ADR 0003, `docs/architecture/state-machines.md`, `docs/release/RUNBOOK.md` |
| `askthepeople-security-reviewer` | Path escape, prompt prefixing, tenant isolation, source ingestion, threat model, incident response. **Has kill-switch authority on P0 regressions** — it can halt a merge unilaterally | `docs/security/*`, ADRs 0005 / 0009, `docs/architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` §5 P0 and §6 P1 |
| `askthepeople-ai-eval-steward` | Prompt registry, evals, model releases, failure modes, provider adapters, no chain-of-thought retention | `docs/ai/*`, ADRs 0004 / 0007 / 0010 |
| `askthepeople-frontend-steward` | `frontend/src/`, Civic Wayfinding, route grammar, WCAG 2.2 accessibility, the content system, design assets | `docs/design/*`, ADR 0006 |
| `askthepeople-release-operator` | Release acceptance, runbook, observability, deploy and rollback, SLOs, cost budgets | `docs/release/*` |

**These identifiers are ownership labels, not files.** No agent definition files
exist for them anywhere in the repository, and `.kilo/command/` and `.kilo/agent/`
do not exist. The labels are load-bearing only because `index.md` cites them as
gate owners. If you create agent definitions, put them in `.kilo/agent/`; do not
treat a missing definition as permission to skip a domain.

### The legacy `.agents/` workspace

`.agents/` exists on disk (gitignored at `.gitignore:55`), holding ~31 role
directories from a prior session — `orchestrator`, `sentinel`, four `auditor_m*`,
eight `reviewer_*_m*`, `victory_auditor`, several `worker_milestone_*` and
`_fix` variants, and three `teamwork_preview_explorer_arch_*` — each with
`BRIEFING.md` / `progress.md` / `handoff.md`. Read the directory listing before
mapping; the set has grown since any list was written down.

Mapping when a legacy session is resumed: auditors, `victory_auditor`, and
`sentinel` → `askthepeople-security-reviewer`; `reviewer_*` → `architect` or
`security-reviewer` by topic; `worker_milestone_*` → `architect` +
`orchestration-engineer`; `orchestrator` → the runtime. The notes are useful
context; `docs/` and the code are the authority.

`.kilo/anchored_memory.md` is a previous session's resume note (dated
2026-08-16). It is **history** — it records a backend suite in the 9,4xx range
and a frontend suite in the 1xx-file range. Both are stale. Treat every number
in it as history.

---

## 5. Hard rules

1. **Cite the actual code.** Every behavioral claim needs `file:line`. The
   validator checks documents; the audit checks claims. A symbol name plus the
   file is acceptable when you did not pin a line — a wrong line is worse than
   no line.

2. **Do not add code to `backend/app/api/simulation.py`.** New handlers go in
   the per-resource modules under `backend/app/api/routes/`, which is what
   `api/routes/__init__.py` registers. That file is a helper module with zero
   routes; it exists because every `routes/` module imports its helpers. It
   previously also carried undecorated copies of the handlers `routes/` serves —
   unreachable, hand-synced, and called directly by tests, so a safety assertion
   could pass against code that never answered a request. **Do not reintroduce
   that pattern, and do not "helpfully" re-export handlers from it.**

3. **Every module in `api/routes/` must be imported by `routes/__init__.py`.**
   `entity_routes` was written but never imported, so
   `GET /api/simulation/entities/...` answered 404 from that commit until the
   import was added. That comment is in the file for a reason.

4. **No threads, no `subprocess`, from a route.** Long-running work goes through
   Celery (`app/tasks/simulation_tasks.py`, ADR 0003). Routes enqueue and return
   `202 Accepted` with a `Location` header. Cleanup and stale-run reconciliation
   run in beat, not in a daemon thread.

5. **No client-supplied data in canonical server-side records.** Exports are
   derived from canonical attempt records on the server. The audit's P1 finding
   on fabricated provenance is binding.

6. **Use the CURRENT / PARTIAL / TARGET / TRANSITION legend** in any
   architecture or implementation document. The definitions are in
   `index.md` § *State legend*. Do not invent a fifth state.

7. **There are six release gates and no seventh.** The integration audit defines
   them. An earlier roadmap listed a seventh and was archived at
   `docs/archive/misc/IMPLEMENTATION_ROADMAP-2026-08-18.md`. Do not revive it.

8. **Run `python tools/validate_docs.py` before claiming a doc change is
   complete.** Zero errors *and* zero warnings. Warnings are emitted for unused
   footnotes; they still fail the bar. CI blocks the PR otherwise.

9. **Know which schema definition you are editing.** There are **two divergent
    sources of database truth**, and no test compares them:

    | Path | Defines |
    |---|---|
    | `backend/migrations/versions/` (3 revisions, head `b2c3d4e5f6a7`) | 16 tables — the `dw_*` run/source/path aggregates, plus `graphs`, `ontologies`, `reports`, `projects`, `simulations`, `sources` |
    | `backend/app/db/schema.py` | 6 tables — `organizations`, `projects`, `simulations`, `agent_profiles`, `attempts`, `observations` |

    Only `projects` and `simulations` appear in both. **Alembic is not invoked by
    any Dockerfile, compose service, or CI job** — `grep -rn alembic Dockerfile*
    docker-compose.yml .github/workflows/` returns nothing. Instead `create_app`
    calls `init_db` → `Base.metadata.create_all` at boot, which materializes
    only the ORM's six tables.

    Consequences you must plan around: a schema change in one file does not
    reach the other; a deployment that relies on `create_all` never gets the
    `dw_*` aggregates; and `alembic upgrade head` against a `create_all` database
    collides on the two shared tables. This is Gate 3 work under
    `askthepeople-persistence-engineer` and belongs to exec-plan 08 fix 1 (dual
    SQLAlchemy bases / Alembic), not to a feature change. **Do not "fix" it by
    running `create_all` against production** — decide which definition is
    canonical, record the decision, then converge.

10. **Never edit build output or generated packaging.** `frontend/dist/`,
   `static/dist/` (an older second build, committed at the root), `*.db`,
   `CHECKSUMS.sha256`, `MANIFEST.md`, `TREE.txt`. Those three are a frozen
   2026-07-29 snapshot of a documentation package that no longer matches the
   tree; treat them as audit artifacts, not as a manifest of what exists.

11. **Do not fix the docs to hide an implementation gap.** Mark CURRENT vs
    TARGET explicitly. A screenshot, prototype, fixture, or generated route is
    not proof of a complete backend workflow (`INTEGRATION_GUIDE.md` §7).

12. **Every pull request identifies**: what is implemented, what the docs
    require, the exact gap closed, migration and compatibility impact,
    tests/evals run, rollback method, and remaining known gaps.

13. **Material changes to product claims, methodology, AI prompts, model
    configuration, source processing, retention, or release gates require** a
    PR, named reviewers, security/privacy review where relevant, an impact
    statement, test or eval evidence, a migration and rollback plan, and an
    updated version and review date. Silent changes to prompt aliases, model
    aliases, prohibited-language rules, truth disclosures, or retention are
    **forbidden** (`docs/README.md` change-control rule).

14. **`backend/requirements.txt` is a stale subset, and nothing uses it.** It
    declares a fraction of what `backend/pyproject.toml` does and is missing
    `flask-limiter`, `flask-sock`, `celery`, `redis`, `sqlalchemy`, `alembic`,
    `psycopg`, `supabase`, `gotrue`, `minio`, `torch`, `sentence-transformers`,
    `transformers`, `mcp`, `fpdf2`, `pandas`, `networkx`, `gunicorn`, and
    `sentry-sdk`. **CI and the Docker builds use `uv.lock` via
    `uv sync --frozen`**, which fails on a lock that does not match. Adding a
    dependency means editing `pyproject.toml` and relocking — never
    hand-editing `requirements.txt` and expecting CI to see it. Treat
    `requirements.txt` as documentation of the *original* dependency set.

15. **Do not enable a feature flag to make a test pass.** The flags are
    fail-closed by design, and `Config.validate()` refuses several outright when
    `DEBUG=False`: `SOURCE_INGESTION_V1_ENABLED` (default off — every mutating
    source route returns 503 while off, and 501 when on, which is the honest
    signal that the boundary is unfinished), `DEV_ACTOR_CONTEXT_ENABLED` (exists
    only because the ADR-0009 OIDC/membership resolver is not built; it
    fabricates a tenant scope), `ENABLE_TRAIT_INFERENCE` (off),
    `ALLOW_RUNTIME_SETTINGS` (off), `ALLOW_PRIVATE_LLM_ENDPOINTS` (off),
    `DECISION_LENS_V1_ENABLED` (on), `USE_SUPABASE_PERSISTENCE` (off —
    persistence is opt-in).

16. **Never add a FastAPI router to this app.** `backend/app/api/capability.py`
    is one: an `APIRouter(prefix="/api/capability")` that is never included and
    never imported, inside a Flask app. It is dead code. Its two collaborators
    (`services/capability_registry.py`, `schemas/capability.py`) exist only to
    serve it — though note that `capability_registry.py` itself imports
    `app.schemas.capability`, so "only imported by it" is one-directional, not a
    clean island. Do not mount it. Delete it in a separate, revertible commit.

17. **Do not run the spent one-shot scripts.** Root `patch.py` is regex surgery
    that already rewrote `backend/app/api/graph.py` to enqueue Celery tasks; it
    is not idempotent and re-running it would corrupt the file. There is a
    second copy under `backend/`. Same class: `verify_check.py`,
    `setup-local.sh` (obsolete pyenv flow, superseded by `uv`), and
    `run-evaluation-pipeline.sh` (references a `views/Process.vue` that was
    renamed to `views/MainView.vue`).

18. **Do not add new aliases to the deprecated token block.** `design-tokens.css`
    keeps ~70 legacy aliases in a clearly marked block so old components keep
    rendering. Adding to it grows a debt you will have to unwind; consuming one
    is the actual fix.

19. **One `vercel.json` exists and is the single static-frontend manifest.**
    The duplicate `frontend/vercel.json` was deleted on 2026-10-01 (root
    builds `frontend/dist` via `npm --prefix frontend run build`, matching the
    Dockerfile's build location). Do not create a second.

---

## 6. Commands

### Verify (the one gate)

```bash
npm run verify          # -> bash scripts/release/verify
```

Five gates, in order: doc validator → frontend tests → frontend production build
→ backend tests with evals excluded → gitleaks (skipped with a warning when the
binary is absent; CI still enforces it). Exits non-zero on any failure.
**Requires bash** — under PowerShell use Git Bash, or run the steps below
directly.

`docs/release/RUNBOOK.md` makes this the mandatory single clean-environment
entry point. It was missing until commit `661f330`. If you extend it, keep the
runbook's checklist mapped to it and keep `package.json` pointing at it.

### Tests

```bash
npm run backend:test          # Windows only: hardcodes .\.venv\Scripts\pytest
npm run backend:test:ci       # portable: uv run --frozen pytest -q --ignore=tests/evals
npm test                      # frontend: vitest run
cd backend && .\.venv\Scripts\pytest                    # full suite, evals included
cd backend && .\.venv\Scripts\pytest tests/evals        # evals need tests/evals/results.json
```

`backend/pyproject.toml`'s `[tool.pytest.ini_options]` sets
`asyncio_mode = "auto"`, `--import-mode=importlib`, clears `PYTHONPATH`, and sets
`FLASK_DEBUG=true`. There are **no custom pytest markers** — nothing is excluded
from the default run, so a full local run is roughly what CI's backend job runs.
Known skips are Windows symlink/admin tests and the eval tests that need
`results.json`.

To get the real numbers instead of a remembered one:

```bash
npm run verify          # authoritative; prints the full gate summary
```

### Lint

- **Backend: none configured.** ruff is deliberately absent from
  `backend/pyproject.toml` — adding it requires relocking, and `uv sync
  --frozen` in `Dockerfile` / `Dockerfile.worker` fails on a lock that does not
  match. The tree is not ruff-clean against ruff's defaults and there is no
  `[tool.ruff]` config, so `uvx ruff check <files you touched>` is advisory only.
  Lint the files you touched, not the tree.
- **Frontend: none.** No ESLint, no `lint` script. The only static analysis is
  the truth linter, reached through Vitest.
- **Docs: `python tools/validate_docs.py`.** This is the real linter.

### Dev

```bash
npm run setup:all     # npm ci (root + frontend) && uv sync --frozen --group dev
npm run dev           # backend on :5001, frontend on :3000, concurrently
```

`--group dev`, not `--extra dev` — dev dependencies are a uv dependency group,
not an extra; `--extra dev` was a real bug, fixed in `47bff7b`. The backend
refuses to import in production without a validated `SECRET_KEY` (minimum
length and insecure-marker rules are in `credential_validation_error()` near the
top of `config.py`; the fail-closed raise is further down, in the `SECRET_KEY`
block) and `Config.validate()` refuses `CORS_ORIGINS='*'` when `DEBUG=False`.

---

## 7. Security invariants worth knowing before you move anything

- **HTTP auth**: one global `before_request` hook in `create_app`
  (`require_auth`). `/health` is exempt; only `/api/*` is protected;
  `Authorization: Bearer` is compared with `hmac.compare_digest`. A falsy
  `APP_TOKEN` opens the API — that is local-dev behaviour, and
  `REQUIRE_APP_AUTH` defaults to on outside DEBUG. `create_app` refuses to boot
  if auth is required and the token is weak or missing.
- **WebSocket auth**: browsers cannot set headers, so the client POSTs
  `/api/auth/ws-ticket` (rate-limited per minute) and connects with `?ticket=`.
  Tickets are HMAC-SHA256, short-TTL, scope-allowlisted to
  `{"simulation", "report"}`, and single-use via a lock-guarded nonce set.
  Origin is checked by exact allowlist. **Never put the access key in a URL.**
- **Path escape**: `app/utils/safe_path.py`. **SSRF**: `app/utils/safe_url.py`
  on source ingestion. Do not hand-roll either.
- **Prompt prefixing is not a security boundary** (ADR 0004). Source text is
  data, never instruction. `LLMClient.chat_with_role_contract` with separate
  roles, zero tools, structured output, deterministic truth + terminology
  validators, and a per-call SHA-256 record is the boundary. There is a test
  guard for this; do not weaken it to unblock a feature.
- **No chain-of-thought retention** (ADR 0010).
  `strip_reasoning_scaffold()` in `services/report_agent.py`, covered by
  `tests/test_reasoning_scrub.py`.
- **Graph writes to synthetic memory are unconditionally rejected** at the
  request seam — `_resolve_graph_memory_request` in `api/simulation.py` always
  raises `synthetic_graph_writes_unsupported`. `ZepGraphMemoryUpdater` is
  documented experimental.
- **5xx responses are traceback-scrubbed** by an `after_request` hook
  (`strip_traceback_in_production`); Sentry events are PII-scrubbed by
  `before_send`. These are two different hooks in two different parts of
  `create_app` — do not cite them as one range.

---

## 8. Deployment reality: there is no supported PaaS deploy

Every deploy path fails closed on purpose, pending canonical shared persistence
(ADR 0012).

- `Procfile` — all three process types run
  `backend/scripts/block_legacy_railway_deploy.py`, which exits non-zero
  unconditionally.
- `railway.toml` — carries an explicit `RELEASE NO-GO` comment, and
  `preDeployCommand` also runs the blocker.
- `render.yaml` — `services: []`.
- `vercel.json` — static frontend only, and there are two conflicting ones (§5
  rule 19).
- The only runnable topology is single-host transition Compose, and it requires
  `BUILD_REVISION` and a mode-0600 `.env.transition`. **The runbook forbids
  running it from OneDrive, Dropbox, NFS, or SMB** — SQLite locking and atomic
  file updates are not deployment evidence on a sync mount, and this checkout is
  under OneDrive. A deployer must clone to a local disk first.
- Operator-only blockers, no code change closes them: revoke and rotate the
  exposed provider credentials; supply `SECRET_KEY`, `APP_TOKEN`, `LLM_API_KEY`,
  `ZEP_API_KEY`, and an explicit `CORS_ORIGINS` allowlist; disable autodeploy on
  every connected provider dashboard.

Full list with `file:line`: `docs/deployment/README.md` § *Deployment blockers*.
Two of its entries were stale at `b868477` — it still reported `setup:backend`
as broken and `npm run verify` as omitting the doc validator, both of which had
already been fixed. **Both entries were corrected on 2026-10-01** and are now
struck through as RESOLVED (blockers 2 and 6). Blockers 1, 3, 4, 5, and 7
remain open and no code change closes them.

**Do not deploy from a worktree.** Duplicate checkouts appear under `.kilo/` and
`.freebuff/`, and they match any naive glob. Check `git worktree list` and both
directories before you do anything that walks the tree. These come and go
between sessions — the set present when this file was written is not the set
present now. Two orphaned worktrees (`lively-bite`, then `burly-memory`, both
detached at `b868477` and clean) were removed on 2026-10-01; if new ones appear
during a session, something is creating them.

---

## 9. Drift: the known-wrong things

### 9.1 Re-measure before you quote

```bash
python tools/validate_docs.py                 # doc counts — trust this output
npm run verify                                # full gate summary
git status --short; git log -1 --oneline; git worktree list
Get-ChildItem docs/exec-plans -Filter *.md | Measure-Object    # plan count
Get-ChildItem frontend/src/components -Filter *.vue | Measure-Object
```

### 9.2 Known drift you will trip over

Real, current, and not yet fixed. Do not "discover" them as if they were new; do
not assume a document that says otherwise is right.

- **Two divergent schema definitions, and no test compares them.**
  `backend/migrations/versions/` defines 16 tables; `backend/app/db/schema.py`
  defines 6. Only `projects` and `simulations` overlap. Alembic is not invoked by
  any Dockerfile, compose service, or CI job — `create_app` runs
  `Base.metadata.create_all` at boot instead, materializing only the ORM's six
  tables. This is the largest unrecorded correctness risk in the repository, it
  is invisible to `npm run verify`, and it is what exec-plan 08 fix 1 is for.
  Read §5 rule 9 before touching either file.
- ~~**`index.md` has ~12 stale citations into `backend/app/__init__.py`.**~~
  **Corrected on 2026-10-01.** At `b868477` the file was citing a version
  roughly 50-200 lines out of date: `create_app` at `:25` (real `:72`),
  `require_auth` at `:125-141` (real `:223-252`), `compare_digest` at `:140`
  (real `:248`), the CORS branch at `:74-82` (real `:126-146`), security
  headers at `:246-293` (real `:266-313`), traceback stripping at `:295-326`
  (real `:315-346`), the static handler at `:317-325` (real `:425-433`), and
  `register_cleanup` at `:106-109` (real `:203-205`). Two error-handler
  citations (`362-366`, `351-360`) pointed at the blueprint-registration block
  rather than at `handle_unsafe_path` (`:384-386`) and `handle_rate_limit`
  (`:376-378`). All re-measured against the 438-line file.
- ~~**Both dead buildplan anchors.**~~ **Corrected on 2026-10-01** by
  repointing, as this file always instructed. Both anchors were not merely
  stale but **fabricated**: `#13-highest-value-implementation-order` and
  `#7-correct-target-architecture` appear nowhere in the build plan, and the
  phrase "auth → parse → authorize → dispatch → present" appeared nowhere in
  the repository except `index.md` itself. The build plan also does not define
  the six gates at all — its §7 is *P2 gaps* and its §13 is *Permanent truth
  statements*. `index.md` now states that its gate table is the only definition
  of the gate themes and points to ADR-0011 for rollout order.
- **The build plan contradicts the code on the Truth Rail's first line.**
  It writes `ACTIONS + ANSWERS: SYNTHETIC` in three places; the enforced string
  is `GENERATED`. §2 gives the resolution.
- ~~**`docs/product/**` is gone but the CI job still references it.**~~ **The
  root `README.md`'s seven dead links into that directory were repaired on
  2026-10-01 (the truth contract now points at ADR-0001, and the
  appropriate-use and validation-handoff links point at their archived
  originals), and `.github/workflows/docs.yml`'s dead `SCAN_PATHS`/allowlist
  entries were removed the same day — that removal was what made both grep gates
  inert in the first place. All `docs/product/` references in the live workflow
  are now explanatory comments, not live paths.
- ~~**`docs/release/GATE_0_RELEASE_NOTES.md` still quotes the gate-0 snapshot**
  (`225 passed`, `Markdown files: 49`).~~ **Corrected on 2026-10-01.** It now
  labels that block a historical gate-0 snapshot, tells the reader to run the
  validator rather than quote its counts, and records the current measurement.
  `docs/README.md` and the root `README.md` were corrected the same way — none of
  them hardcode a document count any more.
- ~~**Three tracked Vue files are dead weight**~~ **RESOLVED 2026-10-01**
  (commit `74784b7`). `Step1GraphBuildRefactored.vue` (426 lines),
  `EvidenceBadge.vue` (290), and `HistoryDatabase.vue` (1013) were deleted in
  their own revertible commit. Nothing imported any of them, no route rendered
  them, and the frontend suite passes without them (200 tests in 28 files). One
  stale comment in `frontend/src/__tests__/branch-lineage.spec.js` still
  described `HistoryDatabase.vue` as an existing alternative; corrected.
- ~~**Exec plans 08 and 09 are not in the `docs/exec-plans/README.md` order
  table** and have no dependency narrative.~~ **Corrected on 2026-10-01.** All
  ten numbered plans are now in that table with a per-plan status, and root
  `README.md` no longer says "8 plans". Plans 08 and 09 still lack a dependency
  narrative — that half remains open.
- **2,652 lines across 6 files of the backtest/optimization island have no
  production importer** (re-measured 2026-10-01; an earlier figure of "~2,900"
  was wrong): `app/simulation/hybrid_simulator.py` (563),
  `app/optimization/learning_loop.py` (474), `multi_objective_loss.py` (406),
  `theta_optimizer.py` (456), `app/data/outcome_fetcher.py` (430),
  `app/models/baseline_library.py` (323) — driven only by
  `app/evals/first_backtest.py`, which is itself unimported.
  `hybrid_simulator.py` still carries 5 `TODO`s, and `baseline_library.py`
  raises `NotImplementedError` by design (abstract base). **All five artifacts
  plus `backend/db/migrations/20260819_add_capability_registry.sql` carried an
  "Authority: PREDICTIVE_SIMULATION_ROADMAP.md" line citing a document that was
  archived as superseded on 2026-10-01.** That roadmap's objective is to fit
  simulated output to observed real-world behaviour, which ADR-0001 forbids.
  Each now carries a DO-NOT-WIRE warning. Do not wire them without a new
  accepted ADR superseding ADR-0001.
- **`constraint_engine`, `game_theory`, and `calibration_metrics` have no
  production importer** and are blocked on inputs the product does not have.
  Analysis in `docs/architecture/NEXT_STEPS_ROADMAP.md`, Phase 2.
  `calibration_metrics` is the sharpest case: publishing a Brier score would
  assert a calibration the product explicitly disclaims, so wiring it is a
  truth-contract violation, not a task. **Note `diffusion_model` *is* wired** —
  `simulation_config_generator.py` imports it in production. Do not list it as
  dead; an earlier draft of this file did, and it would have justified deleting
  a live module.
- **`supabase/` is an abandoned CLI-default scaffold**: a generated `config.toml`
  with no migrations, no referencing code, and a stray `.start.log`.
- **~41 stray `.pytest_*` directories** sit untracked-but-ignored under
  `backend/` (and more at the repo root). `.gitignore` has a broad `.pytest*/`
  rule. Local debris. Do not add a blanket exception, and do not cite their
  contents as evidence.
- **Two committed frontend builds** (`frontend/dist/`, `static/dist/`).
- **`.claude/settings.local.json` is machine-local, gitignored, and holds a very
  broad `Bash(... -c ":*)` allow rule.** It is not shared policy and must never
  be treated as a permission grant from the repo.
- **The docs validator is scoped to `docs/` only** and exempts `docs/archive/`.
  Root `README.md`, `INTEGRATION_GUIDE.md`, `PROVENANCE.md`, and every file
  outside `docs/` are unvalidated for structure. Broken links and placeholder
  tokens there are yours to catch — the validator will not.

### 9.3 The working tree

`git status` is dirty and **it changes between sessions** — during the audit
that produced this revision, `main` advanced from `b868477` to a new commit
that consumed part of the uncommitted consolidation, two detached worktrees
appeared and then vanished, and the modified-file list grew and shrank. Treat
these as facts about the tree, not as a stable list:

- A documentation consolidation is **partly committed and partly not**. `main`
  has advanced past the baseline named in this file's header. Verify with
  `git log -1 --oneline`; do not assume either state.
- Still uncommitted when last checked: `scripts/release/verify` was made
  portable (it previously failed on Windows with 2 of 5 gates broken — gate 1
  assumed `python` was on the Git Bash PATH, and gate 4 invoked the
  extensionless `.venv/Scripts/pytest`, whose CRLF shebang MSYS cannot
  execute); `index.md` gained its § *Status of record`; root `README.md` and
  `docs/README.md` had stale counts corrected; `IMPLEMENTATION_ROADMAP.md` was
  archived because it listed a phantom seventh gate.

Run `git diff` and read it before committing. Do not revert a dirty file you did
not dirty without understanding why it is dirty.

---

## 10. Definition of done

A change is done when:

1. `npm run verify` passes, or the delta in its result is explained with
   `file:line`.
2. `python tools/validate_docs.py` reports `Errors: 0`, `Warnings: 0`,
   `RESULT: PASS` if any document changed.
3. Every new or moved behavior has a test that would fail without it.
4. If it moves a gate, the **Status of record** table in
   `docs/architecture/index.md` is updated — and only that table. Re-measure its
   line counts before re-quoting them.
5. If it touches a truth surface (copy, disclosure, prompt, model, retention,
   export), it carries an impact statement and a rollback plan, and the affected
   document's `version` and `last_reviewed` are updated.
6. Any number you wrote into a document was produced by running the command, not
   by copying it from here or from another document. §0.
7. The commit message states what changed and what gate or doc section it moves,
   in the repo's existing imperative style.
8. Nothing in §9.2's known-drift list was silently relied upon.

### Provenance

This repository is an adaptation of
[MiroFish](https://github.com/666ghj/MiroFish) by 666ghj, not an independently
created codebase. Shared root commit `38e3d05b1d33d13fcbadc83ec0c4bf84c878e828`;
see [`PROVENANCE.md`](PROVENANCE.md) and `THIRD_PARTY_NOTICES.md` (AGPL-3.0).
Upstream prediction / high-fidelity / digital-twin marketing claims were
explicitly **not** inherited. Do not make origin claims that `PROVENANCE.md`
does not support.
