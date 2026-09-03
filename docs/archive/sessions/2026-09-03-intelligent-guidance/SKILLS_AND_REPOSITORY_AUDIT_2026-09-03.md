# Skills and repository audit — 2026-09-03

## Scope and method

This audit covered:

- Repository source, tests, configuration, documentation, and current worktree
  metadata.
- All `SKILL.md` files found under `C:\Users\serge\.claude\skills` and
  `C:\Users\serge\.copilot\skills`.
- Generated/dependency trees (`node_modules`, `frontend/dist`, `.git`, and
  Python virtual environments) were excluded from source inspection.
- Binary databases and environment files were checked for tracking status but
  not opened or copied.

The repository has no project-local `.claude/skills` directory.

## Repository-first project profile

Before selecting skills, the repository was characterized from its governing
contracts, manifests, source tree, route registration, tests, and current
worktree:

| Area | Evidence-based profile |
|---|---|
| Frontend | Vue 3 + Vite, JavaScript, Vue Router, Vitest; entry point and styles are under `frontend/src/` |
| Backend | Flask application with blueprints, WebSocket support, Celery/Redis task processing, and Python 3.11+ |
| Persistence | SQLAlchemy/Alembic, SQLite in the current baseline, PostgreSQL/Supabase transition surfaces, filesystem artifacts |
| AI/simulation | OASIS/CAMEL, OpenAI-compatible endpoints, Zep Cloud, behavioral/model services, provenance and truth-contract constraints |
| Security | Bearer authentication, signed WebSocket tickets, SSRF/path defenses, secret scanning, CORS/rate-limit controls |
| Quality gates | `python tools/validate_docs.py`, Vitest, Vite build, and backend pytest; no configured frontend lint script |
| Operational state | Current worktree contains 36 modified/untracked paths; the audit is not based on a clean commit |

This profile was established before mapping skills. Skills were selected only
when their guidance matched one of these surfaces; framework-specific examples
were treated as non-authoritative unless they matched the repository’s actual
stack.

The executable routing contract derived from this profile is in
[REPO_SKILL_PLAYBOOK.md](REPO_SKILL_PLAYBOOK.md).

## Verification results

| Check | Result |
|---|---|
| Documentation validator (`python tools/validate_docs.py`) | PASS — 0 errors, 0 warnings |
| Frontend tests (`npm run test`) | PASS — 27 files, 190 tests |
| Frontend build (`npm run build`) | PASS, with CSS warnings |
| Diff whitespace check (`git diff --check`) | FAIL — blank line at EOF in `AGENTS.md` |
| Backend tests (`cd backend; .\.venv\Scripts\pytest -q`) | PASS — 9,464 passed, 4 skipped, 1 expected failure; 1 Windows cache-permission warning |
| Tracked environment files | Only `.env.example` is tracked; runtime env files are ignored |

## Findings

### High priority

1. **Malformed font imports are accepted but ignored.**
   [design-tokens.css](frontend/src/assets/design-tokens.css) lines 1027–1028
   contain `@import ""@fontsource/..."";`. The imports also occur after other
   stylesheet rules. Vite completes the build but emits `@import must precede`
   warnings, so the intended Archivo Narrow and Source Sans 3 fonts may not
   load. Correct the quoting and move these imports to the top of the file.

2. **The governing documentation contains an internal product-boundary
   contradiction.**
   [docs/README.md](docs/README.md) lines 25–27 describe the product as
   explicitly outside several predictive categories, while its index entry near
   line 150 says those restrictions were deleted to enable forecasting and
   high-fidelity population modeling. [AGENTS.md](AGENTS.md) lines 78–86
   simultaneously treats the restrictions as mandatory. The validator does not
   detect this semantic contradiction; one authoritative wording and status
   should be selected.

3. **The new guidance delivery is claimed complete while its integration is
   explicitly unfinished.**
   [INTELLIGENT_GUIDANCE_DELIVERY.md](INTELLIGENT_GUIDANCE_DELIVERY.md) lines
   3–5 and 171–188 call the system complete and production-ready, but
   [INTELLIGENT_GUIDANCE_COMPLETE.md](docs/design/INTELLIGENT_GUIDANCE_COMPLETE.md)
   lines 154–185 still describe replacing and migrating components as future
   phases. [MainView.vue](frontend/src/views/MainView.vue) lines 187–189
   imports the original `Step1GraphBuild.vue`; the
   `Step1GraphBuildRefactored.vue` file is not used by the application. This
   is a documentation claim about shipped behavior that the code does not
   support.

4. **Progressive guidance can hide its own “show more” control.**
   [ProgressiveGuidance.vue](frontend/src/components/ProgressiveGuidance.vue)
   lines 68–82 renders nothing unless `isRevealed(id)` is true. In the mapping
   phase, [useGuidedContext.js](frontend/src/composables/useGuidedContext.js)
   lines 140–154 does not list `remaining_entities` in the primary, secondary,
   or available emphasis sets, while
   [Step1GraphBuildRefactored.vue](frontend/src/components/Step1GraphBuildRefactored.vue)
   renders that content as `level="secondary"`. A first-use user can receive
   no preview or trigger to reveal remaining entities.

### Medium priority

5. **A root-level Markdown link is over-relative.**
   [AGENTS.md](AGENTS.md) line 34 links to
   `../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` even though `AGENTS.md` is at the
   repository root. The link should resolve from the root to
   `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`.

6. **The repository contains explicitly unfinished backend paths.**
   TODOs remain in
   [hybrid_simulator.py](backend/app/simulation/hybrid_simulator.py) and
   [learning_loop.py](backend/app/optimization/learning_loop.py), and
   [baseline_library.py](backend/app/models/baseline_library.py) still raises
   `NotImplementedError`. These may be intentional roadmap items, but release
   documentation should not describe the affected capabilities as complete
   without gating those paths.

7. **The architecture claim about simulation route ownership is false.**
   [docs/architecture/index.md](docs/architecture/index.md) lines 97 and
   102–105 say all simulation handlers live in `api/routes/`, but
   [branching_routes.py](backend/app/api/branching_routes.py) lines 10–11
   still defines a simulation route and
   [api/__init__.py](backend/app/api/__init__.py) lines 49–56 imports it
   separately. Move the route or document the exception and verify the URL
   map.

8. **Gate 5 was overstated by re-exporting library symbols.**
   The modified [services/__init__.py](backend/app/services/__init__.py)
   exports constraint, game-theory, and calibration functions, but export
   visibility is not production runtime integration. [AGENTS.md](AGENTS.md)
   lines 158–159 should keep these capabilities partial until production call
   sites and release evidence exist.

9. **A security regression test was weakened.**
   [test_secret_scan_policy.py](backend/tests/test_secret_scan_policy.py)
   lines 156–158 no longer asserts that every Vercel manifest contains the
   `block_legacy_railway_deploy.py` fail-closed blocker; it only checks that a
   project name is absent. The test can pass while an unsupported manifest is
   reintroduced.

### Low priority

10. **The current worktree is not a clean audit baseline.**
   There are 36 modified or untracked paths, including frontend guidance work,
   backend service exports, tests, and documentation. Findings involving those
   files should be reviewed against the author’s intended diff before cleanup.

11. **The skill-stocktake skill has incomplete metadata.**
   [skill-stocktake/SKILL.md](C:/Users/serge/.copilot/skills/skill-stocktake/SKILL.md)
   has a description and origin but no `name:` frontmatter field. Its own
   inventory logic expects named skill metadata, so this is a self-audit
   inconsistency.

12. **The repository contract references an unavailable skill name.**
   [AGENTS.md](AGENTS.md) line 66 references an `adhd` skill, but no matching
   skill directory or `SKILL.md` exists in either installed skill tree.

## Skill inventory

| Location | `SKILL.md` files | Notes |
|---|---:|---|
| `C:\Users\serge\.claude\skills` | 401 | Includes nested benchmark and coding skills |
| `C:\Users\serge\.copilot\skills` | 395 | Includes the Copilot-native skill set |
| Project-local `.claude\skills` | 0 | Directory not present |

There are 22 exact relative-path overlaps between the Claude and Copilot
trees, all in shared video/media skills. The two trees are not interchangeable:
the Claude tree contains Claude-specific command assumptions, while the Copilot
tree contains the skills available to this VS Code session.

## Recommended skills for this repository

The selection below is the result of the repository-first profile above, not a
generic list of skills whose names happen to contain “backend”, “security”, or
“frontend”.

### Subsystem-to-skill matrix

| Repository surface | Skills to use | Why this is a distinct use | Repository anchors / cautions |
|---|---|---|---|
| Flask blueprint and route decomposition | `api-design`, `backend-patterns`, `python-patterns` | Check URL/resource semantics, route responsibility, validation, repository/service boundaries, and Python implementation quality separately | `backend/app/api/`, `backend/app/application/`, `backend/app/domain/`; do not apply Node/Next middleware examples literally |
| WebSocket ticket issuance and runtime channel | `security-review`, `python-testing`, `verification-loop` | Review ticket scope/expiry/authentication, then test handshake and failure modes, then verify browser-to-server behavior | `backend/app/api/ws.py`, `backend/app/api/auth.py`, frontend WebSocket composables; preserve signed-ticket contract |
| Celery tasks, Redis state, worker lifecycle | `backend-patterns`, `python-testing`, `verification-loop` | Audit queue boundaries, idempotency, retries, cancellation, and worker observability rather than treating background work as ordinary request code | `backend/app/tasks/`, `backend/app/models/task.py`, `docker-compose.yml`, `Dockerfile.worker`; current docs call durable workflow support partial |
| SQLAlchemy/Alembic/PostgreSQL transition | `database-migrations`, `backend-patterns`, `python-testing` | Review migration safety, repository scoping, transaction behavior, and SQLite/Postgres parity as separate concerns | `backend/alembic/`, `backend/app/db/`, `backend/app/services/*_repository.py`; do not substitute Prisma/Drizzle advice |
| Supabase/MinIO/filesystem artifacts | `database-migrations`, `security-review`, `backend-patterns` | Check storage cutover assumptions, path traversal, object naming, retention, and failure recovery | `backend/app/services/supabase_client.py`, `simulation_artifacts.py`, `safe_path.py`; object storage is documented as target/transition, not completed |
| Source ingestion and URL fetching | `security-review`, `python-testing`, `ai-regression-testing` | SSRF, file type/size, encoding, provenance, and malicious-input regression coverage are the core risks | `backend/app/utils/safe_url.py`, `url_fetcher.py`, source routes, security tests |
| Authentication, authorization, tenant/workspace isolation | `security-review`, `api-design`, `python-testing` | Verify identity and authorization independently from response shape and test cross-tenant denial paths | `backend/app/config.py`, `backend/app/__init__.py`, `access_control.py`, repositories; generic Supabase RLS snippets are not proof of current enforcement |
| Secret policy and deployment manifest guardrails | `security-scan`, `security-review`, `verification-loop` | Scan agent/config surfaces, inspect application secret handling, and run the repository’s actual policy tests | `backend/tests/test_secret_scan_policy.py`, `.gitleaks.toml`, `backend/scripts/guard_vercel_build.py`; `security-scan` mainly targets Claude config and is supplementary |
| OASIS/CAMEL simulation runtime | `python-patterns`, `python-testing`, `ai-regression-testing` | Validate process boundaries, deterministic controls, model adapter errors, and sandbox/production parity | `backend/app/simulation/`, `simulation_runner.py`, `hybrid_simulator.py`; TODOs and `NotImplementedError` must remain visible in release status |
| Behavioral and analytical model services | `python-patterns`, `python-testing`, `ai-regression-testing` | Test mathematical invariants, deterministic seeds, edge cases, and regression fixtures; do not infer production wiring from exports | `big_five.py`, `prospect_theory.py`, `diffusion_model.py`, `constraint_engine.py`, `game_theory.py`, `calibration_metrics.py` |
| LLM providers, prompt registry, model releases | `ai-regression-testing`, `documentation-lookup`, `security-review` | Check provider API freshness, prompt/version binding, structured-output failure handling, and prompt-injection boundaries | `backend/app/prompts/`, `prompt_registry_service.py`, provider adapters, `docs/ai/`; use current provider docs rather than memory |
| Evidence, provenance, truth disclosures, exports | `ai-regression-testing`, `api-design`, `documentation-lookup` | Verify canonical-record derivation, disclosure presence, export schemas, and user-facing claims | `export_service.py`, `report_evidence.py`, `claim_boundary.py`, `docs/architecture/adr/ADR-0001*`; truth contract outranks convenience |
| Vue workflow components and composables | `frontend-design`, `frontend-patterns`, `verification-loop` | Review information architecture and accessibility separately from reactive state/data-flow correctness and build verification | `frontend/src/components/`, `views/`, `composables/`; `frontend-patterns` is React-centric and must be translated to Vue |
| Progressive guidance and adaptive UI | `frontend-design`, `frontend-patterns`, `ai-regression-testing`, `e2e-testing` | Test capability/phase state transitions, hidden/revealed content, keyboard behavior, and actual integration into the mounted workflow | `useGuidedContext.js`, `useAdaptiveUI.js`, `ProgressiveGuidance.vue`, `MainView.vue`; current refactored Step 1 is not integrated |
| Vitest unit/component coverage | `python-testing` is not applicable; use `ai-regression-testing`, `verification-loop` | Prevent choosing a backend skill merely because “testing” appears; focus on contract and regression tests in the configured Vitest runner | `frontend/package.json`, `frontend/src/__tests__/`; no Playwright script currently exists |
| Browser-level workflow/accessibility | `e2e-testing`, `frontend-design`, `verification-loop` | Use only when adding browser tests; validate real navigation, API integration, focus order, and responsive/reduced-motion behavior | `frontend/package.json` has no Playwright dependency/script; do not claim E2E coverage from Vitest alone |
| Docker, Railway, Render, Vercel deployment | `docker-patterns`, `deployment-patterns`, `verification-loop` | Compare service topology, worker commands, environment contracts, and build guards across deploy targets | `Dockerfile*`, `docker-compose.yml`, `Procfile`, `railway.toml`, `render.yaml`, `vercel.json`; deployment manifests are intentionally constrained |
| Release acceptance and operational readiness | `verification-loop`, `documentation-lookup`, `ai-regression-testing` | Assemble evidence, verify current tool/API behavior, and ensure known-risk regressions have tests | `docs/release/`, `.github/workflows/`, `DEPLOY_CHECKLIST.md`; no configured lint script should be invented |
| Documentation governance and contradiction audit | `documentation-lookup`, `verification-loop`, `skill-stocktake` | Verify external technical claims, run the normative validator, and audit skill metadata/content quality | `docs/README.md`, `tools/validate_docs.py`, `AGENTS.md`; semantic contradictions can pass the validator |
| Repository-wide hallucination/consistency review | `skill-stocktake`, `ai-regression-testing`, `verification-loop`, `security-review` | Cross-check declared behavior against imports, call sites, routes, tests, and security policies; each skill covers a different failure class | Use exact file/line evidence; do not treat passing tests or exported symbols as proof of feature integration |

### Skills that look relevant but would mislead if applied wholesale

- `backend-patterns` and `frontend-patterns` contain substantial
  Node/Express/Next.js and React examples. They are useful for concepts only;
  applying their sample code directly would introduce framework drift.
- `api-design` uses `/api/v1` and envelope conventions that do not automatically
  match the existing `/api/*` contract. It should review the current contract,
  not silently redesign it.
- `security-scan` is valuable for Claude configuration, but it does not
  replace Flask application threat modeling or the repository’s secret-policy
  tests.
- `e2e-testing` describes Playwright, while this repository currently exposes
  Vitest only. It becomes applicable after a deliberate browser-test setup.
- `documentation-lookup` references Context7 tool names that are not present in
  every harness. Its principle—verify current library behavior—is useful, but
  the available documentation tool must be substituted.
- Skills for Next.js, React, Prisma, Django, Laravel, mobile, media production,
  sales, and unrelated scientific benchmarks should not be activated merely
  because a file contains “AI”, “model”, “app”, or “pipeline”.

### Additional narrow-use skills

These are useful for specific review phases, but should not be treated as the
repository’s general implementation playbook:

| Skill | Narrow reason to use | Boundary |
|---|---|---|
| `eval-harness` | Design repeatable evaluations for simulation outputs, truth disclosures, provenance, and model-release gates | Do not turn evaluation scores into claims of real-world prediction or representative populations |
| `agentic-eval` | Evaluate tool-using/provider behavior and failure trajectories in the AI layer | Keep prompts, traces, and retained artifacts within the repository’s privacy/no-chain-of-thought rules |
| `prompt-optimizer` | **Do not use for this inventory or direct implementation task** | Its own instructions exclude direct execution and skill inventories; optimization must not weaken the truth contract |
| `enterprise-agent-ops` | Operational controls for agent runs, budgets, incidents, and auditability | Gate 4 is not complete merely because operational guidance exists; verify actual telemetry and runbooks |
| `measure-instrumentation-spec` | Specify missing metrics/traces for Celery workers, simulations, report generation, and release SLOs | Treat as target design until instrumentation is present in code and deployment |
| `develop-adr` | Record decisions when resolving the product-boundary contradiction, storage cutover, or route ownership | Do not use an ADR to relabel an unimplemented target as current |
| `doc-coauthoring` | Reconcile normative docs, implementation-status tables, and release evidence with explicit citations | Run `tools/validate_docs.py`; prose quality does not override the truth contract |
| `webapp-testing` | Browser/API flow testing for the Vue workflow when Vitest unit tests cannot cover integration | The current repo has no configured browser runner; add one deliberately before claiming E2E coverage |
| `deploy-to-vercel` / deployment-specific skills | Validate the Vercel build guard and deployment topology when release work is requested | Not relevant to ordinary feature implementation; do not infer deployment success from a local build |

The most important omissions from a generic skill list are therefore
observability/evaluation/documentation skills: this project’s largest risks are
not only syntax bugs, but unsupported product claims, partial target
architecture, unmeasured workers, provenance drift, and AI-evaluation blind
spots.

## Repo-specific activation rules

Use this section as the routing contract for future tasks in this repository.
Choose skills from the changed files and requested behavior, not from broad
keywords in the prompt.

### Backend routing

| If the task touches | Activate | Required repo-specific checks |
|---|---|---|
| `backend/app/api/**`, route decorators, request/response schemas | `api-design` + `backend-patterns` + `security-review` | Check blueprint registration in `backend/app/api/__init__.py`; preserve `/api/*`; run targeted backend tests |
| `backend/app/api/ws.py`, auth ticket endpoints, WebSocket clients | `security-review` + `python-testing` | Verify ticket expiry, signature, scope, replay behavior, and browser handshake tests |
| `backend/app/tasks/**`, `backend/app/models/task.py`, worker/Docker files | `backend-patterns` + `python-testing` + `enterprise-agent-ops` | Verify queue boundary, retry/cancel state, Redis behavior, worker health, and no route-spawned threads |
| `backend/app/db/**`, `backend/alembic/**`, `*_repository.py` | `database-migrations` + `backend-patterns` + `python-testing` | Check migration immutability, tenant/workspace predicates, SQLite/Postgres behavior, and rollback evidence |
| `safe_path.py`, `safe_url.py`, uploads, source ingestion, filesystem/object storage | `security-review` + `python-testing` + `ai-regression-testing` | Test traversal, SSRF, redirects, size/type limits, provenance, cleanup, and failure paths |
| `backend/app/services/{big_five,prospect_theory,diffusion_model,constraint_engine,game_theory,calibration_metrics}.py` | `python-patterns` + `python-testing` + `eval-harness` | Test mathematical invariants and edge cases; do not call re-exports production integration |
| `backend/app/prompts/**`, provider adapters, `report_agent.py`, eval fixtures | `ai-regression-testing` + `agentic-eval` + `security-review` + `documentation-lookup` | Verify prompt/model version binding, structured output failures, injection boundaries, disclosure, and no chain-of-thought retention |
| exports, reports, evidence, `claim_boundary.py` | `ai-regression-testing` + `api-design` + `doc-coauthoring` | Derive from canonical server records; assert schema/provenance/disclosure fields and truth-contract wording |

### Frontend routing

| If the task touches | Activate | Required repo-specific checks |
|---|---|---|
| `frontend/src/components/**`, `views/**`, `assets/**` | `frontend-design` + `frontend-patterns` | Use Vue 3 Composition API patterns; preserve Civic Wayfinding, WCAG, truth copy, and existing design tokens |
| `frontend/src/composables/**`, stores, router, polling | `frontend-patterns` + `ai-regression-testing` | Test reactive state transitions, cleanup, stale requests, error states, and route/API parity |
| adaptive guidance files (`useGuidedContext`, `useAdaptiveUI`, `ProgressiveGuidance`, `ContextualHelp`) | `frontend-design` + `frontend-patterns` + `ai-regression-testing` + `webapp-testing` | Test first-use/learning/practiced/expert × workflow phases; ensure hidden content has a reachable reveal path |
| `frontend/src/__tests__/**` or Vitest config | `ai-regression-testing` + `verification-loop` | Run `npm run test`; do not claim browser/E2E coverage from Vitest component tests |
| browser workflow, focus order, responsive behavior | `webapp-testing` + `frontend-design` + `verification-loop` | First verify whether a browser runner exists; current package scripts expose Vitest, not Playwright |

### Documentation, operations, and release routing

| If the task touches | Activate | Required repo-specific checks |
|---|---|---|
| `docs/**`, `AGENTS.md`, `CLAUDE.md`, product claims, terminology | `doc-coauthoring` + `develop-adr` (for material decisions) | Read `docs/README.md` and `docs/architecture/index.md`; cite real `file:line`; run `python tools/validate_docs.py` |
| `.github/workflows/**`, release docs, deployment evidence, SLOs | `verification-loop` + `enterprise-agent-ops` + `measure-instrumentation-spec` | Verify actual CI commands, telemetry, rollback evidence, and current/partial/target status |
| `Dockerfile*`, `docker-compose.yml`, `Procfile`, `railway.toml`, `render.yaml`, `vercel.json` | `docker-patterns` + `deployment-patterns` + `verification-loop` | Compare web/worker topology and env contracts; run the build guard; do not equate local build with deployment success |
| repository-wide audit or contradiction review | `skill-stocktake` + `security-review` + `ai-regression-testing` + `verification-loop` | Compare docs → imports → call sites → routes → tests; report only claims backed by evidence |

### Mandatory command mapping

| Change area | Minimum command |
|---|---|
| Documentation | `python tools/validate_docs.py` |
| Frontend behavior | `npm run test` |
| Frontend build or CSS/import changes | `npm run build` |
| Backend behavior | `cd backend; .\.venv\Scripts\pytest -q` |
| Any completed change | `git diff --check` plus the relevant command above |

### Activation anti-patterns

- Do not activate React/Next.js, Django, Laravel, Prisma, or Drizzle guidance
  for this repository’s Vue/Flask/SQLAlchemy implementation.
- Do not activate `prompt-optimizer` to rewrite product or safety prompts;
  truth-contract and disclosure requirements take precedence.
- Do not activate `security-scan` as the application threat model; it is
  supplementary and primarily scans Claude configuration.
- Do not activate deployment skills for a feature-only change.
- Do not mark a feature `complete` because a file exists, a symbol is exported,
  a unit test passes, or a local build succeeds. Trace the mounted/imported
  runtime path and its release evidence.

### Use by default

1. **`python-patterns`** — backend implementation and review. Adapt examples to
   Flask, SQLAlchemy, Celery, and the repository’s Python 3.11+ baseline.
2. **`python-testing`** — backend unit and integration tests.
3. **`api-design`** — route contracts, status codes, error envelopes, and
   pagination. Reconcile its generic `/api/v1` examples with the repository’s
   existing `/api/*` contract before changing URLs.
4. **`security-review`** — authentication, authorization, uploads, secrets,
   SSRF, path handling, and tenant isolation. Its TypeScript examples are
   illustrative, not drop-in Flask code.
5. **`database-migrations`** — Alembic/PostgreSQL schema and migration work.
   Ignore unrelated Prisma, Drizzle, and Django examples.
6. **`ai-regression-testing`** — regression coverage for simulation, sandbox,
   provenance, and backend/frontend parity. Its Next.js examples must be
   translated to Flask and Vue.
7. **`verification-loop`** — final validation, but use the repository commands
   in [AGENTS.md](AGENTS.md): docs validator, Vitest, frontend build, and
   backend pytest. Do not assume a lint script or coverage threshold exists.
8. **`frontend-design`** — Vue UI work and the existing Civic Wayfinding design
   system. Preserve the product’s documented accessibility and content rules.
9. **`e2e-testing`** — only when adding browser coverage. The repository
   currently has Vitest coverage but no Playwright test script.

### Use conditionally

- **`deployment-patterns` / `vercel-cli`** — only for deployment configuration
  or release debugging.
- **`documentation-lookup`** — useful for current Vue, Vite, Flask, Celery,
  SQLAlchemy, and dependency APIs; its Context7 tool names are not available
  in every harness, so use the configured documentation tools instead.
- **`frontend-patterns`** — useful concepts only; it is React/Next.js-centric
  and should not be treated as Vue guidance.
- **`security-scan`** — targets Claude configuration under `.claude/`; it is
  not a substitute for this repository’s application security tests.

### Avoid for ordinary repository work

The many domain-specific benchmark, media-production, mobile, sales, and
framework-specific skills are not relevant unless a task explicitly enters
that domain. Applying them by keyword alone would increase hallucinated
assumptions and framework drift.

## Recommended follow-up order

1. Fix the malformed CSS imports and remove the `AGENTS.md` EOF whitespace.
2. Resolve the product-boundary wording conflict and rerun the documentation
   validator.
3. Correct the root-relative documentation link and verify links in CI.
4. Mark unfinished backend capabilities as `PARTIAL`/`TARGET` in release-facing
   documentation, or implement and test them.
5. Restore the manifest-blocker assertion in the security regression test.
6. Add the missing `name: skill-stocktake` metadata and either remove or
   replace the unavailable `adhd` reference.
7. Re-run the full backend suite to capture its final pass/fail result.
