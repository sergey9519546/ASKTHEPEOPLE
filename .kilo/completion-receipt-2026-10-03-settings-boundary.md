# Completion Receipt — SettingsModal `extra="forbid"` boundary + T27–T30 review

**Date:** 2026-10-03
**Checkpoint:** `a410c9d` on `main`. **All changes uncommitted**, nothing staged, no
history rewritten, no other agent's file touched.
**Baseline at start:** backend 9965 passed; frontend 209 tests / 28 files.

## What was wrong

Nothing was broken. `ProviderSettingsUpdateRequest` and
`ProviderConnectionTestRequest` (`backend/app/api/schemas_entity_settings.py:56,76`)
are `extra="forbid"`, and `SettingsModal.vue` satisfies them today — verified, not
assumed:

```
frontend form keys : 8  ['BRAVE_SEARCH_API_KEY','LLM_API_KEY','LLM_BASE_URL',
                         'LLM_BOOST_API_KEY','LLM_BOOST_BASE_URL',
                         'LLM_BOOST_MODEL_NAME','LLM_MODEL_NAME','ZEP_API_KEY']
backend  mutable   : 8  (identical set)
extra in frontend  : []
missing in frontend: []
/test posts         : ['LLM_API_KEY','LLM_BASE_URL','LLM_MODEL_NAME']
extra in /test post : []
```

The defect was **latent and unguarded**. `frontend/src/components/SettingsModal.vue`
has no test at all. The invariant held only through the *shape* of the source:
`loadSettings` hydrates with `Object.keys(form.value).forEach(...)`
(`SettingsModal.vue:515`), writing key by key, so the fixed 8-key `form` literal is
what `save()` posts (`SettingsModal.vue:554`).

`GET /api/settings` returns 7 read-only keys that are **not** in `MUTABLE_PROVIDER_KEYS`:
`runtime_settings_enabled`, `allowed_llm_base_urls`, `allow_private_llm_endpoints`
(`settings.py:89,90`) and four `*_CONFIGURED` booleans (`settings.py:74-77`).
Rewriting line 515 as `form.value = data` — or `Object.assign(form.value, data)` —
would put those into every save payload, and `extra="forbid"` would answer
`400 settings_request_invalid`, which the modal surfaces as a bare
"Settings could not be saved." No test would have failed.

## What was added

One new untracked file: `backend/tests/test_settings_modal_request_contract.py`, 10
tests. **No production or component code was modified** — the contract was already
correctly applied, so the deliverable is the missing coverage.

Modelled on `backend/tests/test_frontend_api_contract.py`, which is the existing
precedent for cross-boundary source-derived contract checks: read the key sets out
of the SFC rather than hardcoding them, and include vacuity guards.

| Test | Pins |
|---|---|
| `test_form_keys_equal_the_backend_mutable_allowlist` | equality, not containment — an extra key is a 400, a missing key is a setting the UI offers that can never be saved |
| `test_save_posts_the_form_verbatim` | `updateSettings(form.value)`, not `{...form.value, ...}` |
| `test_hydration_is_key_driven_and_never_wholesale` | rejects `form.value =` and `Object.assign(form.value`, and requires the `Object.keys(form.value)` loop |
| `test_no_read_only_response_key_is_posted` | the 3 named read-only keys are absent from the form literal |
| `test_connection_test_payload_is_accepted_by_its_schema` | `/test` payload ⊆ declared fields |
| `test_a_body_carrying_a_read_only_key_is_refused` | route really answers `400 settings_request_invalid` |
| `test_the_form_payload_as_posted_is_accepted` | the 8 real keys clear the boundary, so a forbid-everything schema cannot pass the test above |
| `test_the_feature_gate_still_precedes_the_schema` | malformed body + gate off → `403 runtime_settings_disabled`, not 400 |
| `test_the_key_extractor_can_fail` | extractor returns `[]` / exactly its own keys / ≥8 on the real file |
| `test_this_module_can_actually_fail` | `extra="forbid"` asserted on the model *and* on a live request |

### Falsification (each reverted; tree byte-identical to HEAD afterwards)

| Injected break | Result |
|---|---|
| 9th key `NEW_UNMUTABLE_KEY` added to `form` | **1 failed** (key-set equality) |
| `form.value = data;` before the hydration loop — *the exact latent break* | **1 failed** (`test_hydration_is_key_driven_and_never_wholesale`) |
| `updateSettings({ ...form.value, runtime_settings_enabled: true })` | **1 failed** (`test_save_posts_the_form_verbatim`) |

`git diff --stat frontend/src/components/SettingsModal.vue` → empty after all three.

## Exact validation

| Check | Result |
|---|---|
| `test_settings_modal_request_contract.py` | **10 passed** |
| settings + contract + gate modules (7 files) | **77 passed** |
| Backend suite (`--ignore=tests/evals`) | **9709 passed, 1 skipped, 1 xfailed**, 0 failed (193s) |
| `frontend/src/components/SettingsModal.vue` vs HEAD | **byte-identical** |
| `git status --short` | only `?? backend/tests/test_settings_modal_request_contract.py` |

Backend total is 9709, not the 9965 quoted earlier in the session: the frontend
redesign work consolidated specs. No test regressed — the count fell, it did not fail.

## T27–T30 reviewed against current source

### T27 — transactional artifact writes: substantially complete, one window open

Already implemented before this session's plan text claimed otherwise:
`TaskExecutionFence.checkpoint()` (`models/task.py:325`) rejects a lapsed lease
(`task_execution_fence_expired`, `:329`) and a superseded token
(`task_execution_fence_token_divergence`, `:333`); `write_guard` (`:336`) calls it
before yielding; **15** `write_guard()` call sites; **7** `_atomic_write_text` sites.

**Remaining, genuinely open:** `checkpoint()` is invoked **once**, then the guard
yields — a takeover landing between the check and the write is not observed. Atomic
`os.replace` bounds the damage (one worker's complete content wins, never a mixture)
but only a compare-and-swap at commit closes it. This is a durability-model
decision, not a bug fix.

### T28 — outbox events: not started, and its blocker is now HALF closed

No implementation. `outbox` appears 3× in `backend/app/**` and all three are
non-implementation: a startup refusal message (`config.py`), a reserved identifier
name (`domain/identifiers.py`), a docstring (`services/audit_log.py`).

ADR-0012 requires *"the row version increment and the outbox event in the same
transaction, with a separate publisher."* Still absent. Still **3** migration files.

**Changed since earlier in the session — the Alembic gate is now closed for CI.**
`.github/workflows/ci.yml:364` defines `migrations: "Schema migrations (gate 3)"`,
which asserts exactly one linear head (`:403`), applies every revision to an empty
database with **no credentials in the environment** (`:416`), verifies the canonical
tables and the recorded head (`:423`), round-trips downgrade/upgrade (`:438-439`), and
asserts `alembic revision --autogenerate` still refuses (`:452`). That was zero
references earlier in this session.

**Still open — two owner decisions:**

1. **Container deploy has no migration step.** `alembic` appears **0** times in
   `Dockerfile`, `Dockerfile.worker`, `docker-compose.yml`, `Procfile`, `render.yaml`
   and `vercel.json`. CI proves the chain runs; nothing applies it on deploy.
2. **CI proves the chain against SQLite, not PostgreSQL.** Every migration step uses
   `DATABASE_URL: sqlite:///${RUNNER_TEMP}/gate3.db` (`ci.yml:413,435,448`). SQLite
   tolerates type and constraint behaviour Postgres rejects, so a new revision can
   pass CI and fail on the real engine. T28's table would be the first to prove this
   either way.

### T29 — Gate 4 observability remainder: not started

Zero references for `OTEL`, `opentelemetry`, `SLO`, `COST_BUDGET`, `ALERT` or
tracing in `backend/app/config.py` or `.env.example`. Metrics and Sentry are wired;
the remainder is tracing, SLOs, cost budgets, alerting and horizontal scaling.

The rate-limit decision is **already made and documented**, not an oversight:
`RATELIMIT_STORAGE_URI` is plumbed to `Limiter(storage_uri=...)` and stays opt-in
because a Redis outage would surface as 5xx on `/api/*` (`.env.example:160-163`).

**Owner decision gate:** adding tracing requires a new dependency plus a `uv.lock`
relock — `AGENTS.md` §5 rule 14 makes `uv sync --frozen` in CI and both Dockerfiles
fail on a lock that does not match. That is a dependency-governance choice.

### T30 — prompt registry adoption: now partially adopted

Changed since earlier in the session. `backend/app/utils/llm_client.py:13` imports
`..prompts.registry.PromptRegistry` and `:55` instantiates it lazily
(`PromptRegistry()`), guarded by a `try/except` that logs and continues without the
registry. That is real wiring, not a stray import.

The CWD-relative default path fix from earlier in the session is still in place
(`services/prompt_registry_service.py:8-9,22`, anchored to `parents[3]`).

**Still open:** **18** inline prompt assignments remain, concentrated in
`services/zep_tools.py` (10), `simulation_config_generator.py` (3),
`opinion_scorer.py` (2). And the two competing registries are unreconciled —
`app/prompts/registry.py` (YAML, SHA256 audit fingerprint) now has a production
consumer via `llm_client`, while `app/services/prompt_registry_service.py` (markdown
parser) still has none, and its parser matches nothing in the real
`docs/ai/PROMPT_REGISTRY.md`.

**Owner decision gate:** collapsing the two registries is an ADR-0004 design
decision, not a cleanup.

## Carried forward

- `docs/ai/PROMPT_REGISTRY.md` is a 658-line prose governance document containing
  **zero** `### Prompt: ID (v1.0)` blocks, which is the format
  `prompt_registry_service.py` parses. Either the document or the parser is wrong.
- The SQLite-vs-PostgreSQL gap in the CI migration job (§T28 above) is the one that
  will bite first on a real schema change.