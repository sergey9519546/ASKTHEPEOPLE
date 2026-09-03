---
title: "Release Notes — Gate 0 (Immediate correctness and security)"
status: "Operational"
version: "1.0.0"
owner: "askthepeople-security-reviewer"
last_reviewed: "2026-07-29"
review_cycle: "Per P0 fix"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
applies_to: "every PR that touches backend/app/api/simulation.py, backend/app/tasks/simulation_tasks.py, backend/app/services/oasis_profile_generator.py, backend/app/utils/llm_client.py"
related_adrs: "ADR-0003, ADR-0004, ADR-0005, ADR-0008, ADR-0009, ADR-0012"
---

# Gate 0 — Release notes (immediate correctness and security)

This is the release evidence for the three P0 release-blocker findings in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](../architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md) §5.
Each P0 is closed by a structural fix and a corresponding test. The full
release evidence bundle per [`ACCEPTANCE.md`](ACCEPTANCE.md) is
**TARGET** and lands with gate 4 + gate 5; this document is the
gate-0 subset.

## P0 #1 — Unvalidated `platform` path component in the posts endpoint

**Audit anchor:** §5 P0.

**Affected file:** `backend/app/api/simulation.py`, route
`get_simulation_posts` (around line 2641 in the baseline).

**Before:**

```python
platform = request.args.get('platform', 'reddit')
db_file = f"{platform}_simulation.db"  # P0: request-controlled filename
db_path = os.path.join(sim_dir, db_file)
```

**After:** a module-level `ALLOWED_PLATFORMS` constant
(`{"reddit": "reddit_simulation.db", "twitter": "twitter_simulation.db"}`).
The route parses `platform` as a strict enum and returns
`{"success": false, "error": "invalid_platform", "allowed": [...]}` with
HTTP 422 on any unknown value. SQLite is opened in read-only mode
(`file:...?mode=ro`) with a bounded busy timeout
(`timeout=5.0`). The four audit-required error types are distinguished:
missing database (200 with empty result), missing table (200 with empty
result), locked database (423), corrupt database (500 with
`database_corrupt`), other query failure (500 with
`database_query_failed`).

**Tests:** `tests/test_path_traversal_routes.py::test_get_simulation_posts_platform_allowlist_rejects_unknown`,
`..._rejects_other_unknown`, `..._omitted_defaults_to_reddit`,
`..._accepts_known`.

**Backlog follow-up:** the P1 client-supplied export data hazard and the
tenant isolation in the export query are gate 3 / gate 5 work; this
commit does not close them.

## P0 #2 — Preparation runs in a local daemon thread

**Audit anchor:** §5 P0/P1.

**Affected files:** `backend/app/api/simulation.py`, route
`prepare_simulation`; new `backend/app/tasks/simulation_tasks.py`
task `prepare_simulation_task`.

**Before:**

```python
def run_prepare():
    # ... inline work ...
thread = threading.Thread(target=run_prepare, daemon=True)
thread.start()
return jsonify({...})
```

The thread is process-local and dies on any web restart, redeploy, or
scale-out. Per ADR-0003 the route must enqueue work and return.

**After:** the inline work moved to a new `prepare_simulation_task`
Celery task in `backend/app/tasks/simulation_tasks.py`. The route
enqueues via `prepare_simulation_task.delay(...)` and returns
**HTTP 202 Accepted** with `Location: /api/jobs/{task_id}`. The
progress callback uses `self.update_state` for cross-process
progress plus a best-effort in-process mirror for the in-process
reads that the existing status endpoint performs. The simulation
state is persisted as FAILED on task failure. The unused
`import threading` and `TaskStatus` import are removed from the
route.

**Tests:** `tests/test_simulation_celery_dispatch.py::test_prepare_simulation_returns_202_and_enqueues_task`
asserts the 202 status, the `Location` header, and the enqueued
kwargs.

**Backlog follow-up:** the full durable workflow (idempotency keys,
leases, fencing tokens, heartbeats, cancellation, retry classification)
is gate 2 in `adr/ADR-0003-durable-run-orchestration.md`. This
commit closes the daemon-thread P0 and makes the route an
enqueue-and-return boundary; gate 2 turns it into a fully durable
workflow.

## P0 #3 — Prompt prefixing is not a security boundary

**Audit anchor:** §5 P0.

**Affected files:** `backend/app/utils/llm_client.py` (new
`chat_with_role_contract` method); `backend/app/services/oasis_profile_generator.py`
(`_generate_profile_with_llm` refactored to use the contract).

**Before:** the profile generator called the OpenAI
`chat.completions.create` with hand-rolled messages, manual JSON
parsing, manual retries, and a textual "do not invent" instruction
in the system role. A textual instruction is not a security
boundary on its own.

**After:** new `LLMClient.chat_with_role_contract` enforces:

- **Separate roles.** The fixed prefix lives in the `system` role;
  the user-controlled content lives in the `user` role; optional
  context lives in additional `user` messages BEFORE the user
  content so the user content remains the last role seen by the
  model and the context cannot displace it.
- **Zero tools.** The OpenAI `tools` parameter is NEVER passed.
  Tests assert `tools`, `functions`, and `tool_choice` are not in
  the call kwargs.
- **Structured output.** JSON mode is requested. A JSON decode
  failure raises `ValueError` and is never silently coerced to a
  valid-looking empty object.
- **Deterministic truth + terminology validators.** The response
  is checked for prohibited terms ("respondent", "public opinion",
  "polling", "poll result", "digital twin") and the hits are
  recorded in `truth_audit`. The audit does not block at this
  layer; gate 5 (evals) lands the block-on-violation behavior.
- **Per-call record.** The result includes `model`,
  `system_prompt_sha256`, `user_prompt_sha256`, `output_sha256`,
  `tools_bound=False`, `structured_output=True`, and the
  `truth_audit` dict so the caller can attach them to the run
  manifest.

`_generate_profile_with_llm` is refactored to use
`chat_with_role_contract`. The manual JSON-parse, manual retry, and
JSON-repair fallbacks are kept for resilience; the structural
contract (roles, zero tools, structured output, per-call record) is
now first-class.

**Tests:** `tests/test_llm_client_role_contract.py` — 8 tests
covering happy path returns data + record, zero tools bound
(asserted on the call kwargs), separate system + user roles, context
prompts come BEFORE the user content, JSON decode failure raises
(no silent empty-object coercion), empty system or user prompts
are rejected, prohibited terms are recorded in the truth audit,
markdown ```json fences are stripped.

**Backlog follow-up:** the full prompt registry, model release
ledger, per-prompt evaluation suite, and adversarial prompt-injection
red team are gate 1 + gate 5 in
`adr/ADR-0004-provider-adapters-and-prompt-registry.md` and
[`docs/ai/EVALS.md`](../ai/EVALS.md). This commit closes the P0
finding by making the role split and zero-tools rule structural
rather than convention; the larger registry / eval work remains
tracked in the ADRs.

## P1 — Live scenario injection now works

**Audit anchor:** §5 P1 "Live scenario changes unsupported".

**Affected files:** the route `inject_simulation_event` in
`backend/app/api/simulation.py`; new helpers
`push_in_memory_event` / `pop_in_memory_events` /
`record_injected_event` in
`backend/app/services/simulation_observation_store.py`; new
function `apply_injected_events` in
`backend/app/services/simulation_runtime_contract.py`; new
`RedisEventConsumer` class and the per-round `consume_events`
hook in `backend/scripts/run_parallel_simulation.py`;
`REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in
`backend/app/config.py`; new `injected_events` SQLite table
populated by `sync_observation_store`; new
`injected_events.jsonl` log per simulation directory.

**Before:** `POST /api/simulation/<id>/inject` returned
**HTTP 501** with `code: "live_scenario_injection_unsupported"`
and the runtime could not ingest breaking news, persona
modifications, or dynamic instructions while a run was in
progress. The audit flagged this as a P1 capability gap.

**After:** the route publishes the event payload to the Redis
Pub/Sub channel `simulation:<id>:events` and falls back to a
process-local in-memory queue when Redis is unavailable. The
runner creates a `RedisEventConsumer` per run, drains the
channel + the in-memory queue each round, and applies the events
through `apply_injected_events`, which logs each event to
`injected_events.jsonl`, records it in the new `injected_events`
SQLite table, and applies content-bearing events as posts
(through `_apply_specs`) and persona-modification events as
system-message appends. `event_type` is one of `breaking_news`,
`inject_post`, `post`, `news`, `topic_spike`, `inject_event`
(content-bearing) or `persona_modification`,
`persona_change`, `dynamic_instruction` (persona-modifying);
unknown event types are recorded as no-ops and counted.

**Tests:** `tests/test_scenario_injection.py` — 4 tests covering
the HTTP 200 round-trip, the in-memory fallback path, the
observation-store table record, and the runtime contract
apply path. `tests/test_runtime_regressions.py::test_live_injection_returns_pubsub_contract`
was updated to assert the new contract.

**Backlog follow-up:** the route currently trusts the caller's
`event_type` and content. Per the audit's P1
"client-supplied export data" finding, the canonical
server-side record is the source of truth; downstream consumers
must not promote client-supplied content to canonical status
without a re-derivation pass. The current contract is **CURRENT
for ingestion**; canonicalization (audit trail, dedup, evidence
binding, server-side re-derivation) is gate 3 / gate 5.

## Test count

- Fast suite: **225 passed, 1 skipped** after gate 0.
- New tests added in gate 0: 17
  - `tests/test_path_traversal_routes.py`: 4 (platform allowlist)
  - `tests/test_simulation_celery_dispatch.py`: 1 (202 + enqueue)
  - `tests/test_llm_client_role_contract.py`: 8 (role contract)
  - `tests/test_scenario_injection.py`: 4 (live injection round-trip, in-memory fallback, observation-store table, runtime contract apply)
  - `tests/test_runtime_regressions.py`: 1 updated to assert the new `200` contract in place of the old `501`

## Validator

```text
python tools/validate_docs.py
Markdown files: 49
ADR files: 12
Lines: 14647
Words: 72493
Warnings: 0
Errors: 0
RESULT: PASS
```

## CI

`.github/workflows/docs.yml` runs the validator, the naked wordmark
check, and the prohibited-language linter on every push and PR that
touches `docs/`, `tools/validate_docs.py`, `.github/workflows/docs.yml`,
`INTEGRATION_GUIDE.md`, or `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`. The
workflow fails closed.

## What's still open per the audit

Closed in this gate:

- **P0 #1 path-escape in `/api/simulation/<id>/posts`** — see
  P0 #1 above.
- **P0 #2 daemon-thread in `/api/simulation/prepare`** — see
  P0 #2 above.
- **P0 #3 prompt-prefixing is not a security boundary** — see
  P0 #3 above.
- **P1 live scenario injection unsupported** — see P1 above.
  The route now ingests breaking news, persona modifications,
  and dynamic instructions through Redis Pub/Sub (with an
  in-memory fallback). Canonicalization remains gate 3 + 5.

Still open:

- **P1 client-supplied export data** — require canonical
  `response_ids` in the export route. Gate 5 / exec plan
  [`docs/exec-plans/05-brief-handoff-exports-and-provenance.md`](../exec-plans/05-brief-handoff-exports-and-provenance.md).
- **P1 no object-level authorization** — multi-tenant isolation.
  Gate 3 in `adr/ADR-0009-multi-tenant-isolation.md`.
- **P1 non-atomic file persistence** — write → verify → hash →
  mark-ready, with the canonical row in PostgreSQL gating access to
  the artifact in object storage. Gate 3 in
  `adr/ADR-0012-canonical-transactional-and-object-persistence.md`.
- **P1 contradictory lifecycle semantics** — the four independent
  state machines (preparation, execution, environment, report) with
  one domain command per transition. Gate 1 + gate 2.
- **P1 in-memory rate limiter** — Redis-backed rate limit.
  Gate 4.
- **P1 unbounded collection loading** — cursor-based pagination
  server-side. Gate 4.
- **Repository census** — the divergence report from
  `c33a6a9127fa0705cfff426053f54815f58b4755` to the current
  baseline, per
  [`docs/exec-plans/00-repository-census-and-governance.md`](../exec-plans/00-repository-census-and-governance.md).

## Bridge to the broader program

The 6-gate program is tracked in
[`docs/architecture/index.md`](../architecture/index.md)
§"Gaps to the target architecture". Each gate is owned by a
Mavis specialist agent and tracked by the corresponding execution
plan. Gate 0 (this document) is structurally closed. The remaining
gates 1–5 land per the dependency order in
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](../architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md) §13.
