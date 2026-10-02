# ASKTHEPEOPLE — Jev (TypeSafe System One) Integration Plan

Adding Jev as an **internal decision primitive**. It is not a new user-facing
capability. It replaces hand-written heuristics and one broken call site with
real typed judgments — and deliberately keeps every probability out of the UI.

## Decisions taken (settled; do not re-litigate)

| # | Decision | Consequence |
|---|---|---|
| **J1** | **Internal only.** Jev's answers drive code; probabilities are used for thresholding and routing in the backend and **never** reach a user as a number. | No new frontend surface. Frontend scope is zero except a regression test. |
| **J2** | **Seam order: `network_topology.py` first, then `role_normalizer.py`.** First is a proof of the seam on a small blast radius; second is the real honesty win. | J-Tasks J1–J5, then J6–J10. |
| **J3** | **Fail-closed flag, default off, silent fallback to today's exact behaviour** when off or on any provider error. | No behaviour change until someone opts in. |
| **J4** | **Add `typesafe_sdk` to `pyproject.toml` and relock.** CI and Docker use `uv sync --frozen`, so a pyproject-only edit breaks the build (`AGENTS.md` §5 rule 14). | J-Task J2 includes the relock. |
| **J5** | **Wrap the Jev path in `InstructionIntegrityGuard`.** ADR-0004 governs the OpenAI path; System One models get the same tamper-evidence. | J-Task J4. |

## The tension this plan is built around

Jev's core output is a **calibrated probability plus confidence**. This
repository's truth architecture exists to deny that anything here is calibrated
or predictive:

- `tools/lint_frontend_truth.mjs` bans `probabilit(y|ies)` (`:26`),
  `confidence` (`:27`), `certainty` (`:28`), `likelihood` (`:29`), and
  `calibrat*` (`:30`) in frontend text, attributes, and script strings.
- `frontend/src/__tests__/product-truth-guard.spec.js:86-160` is a **ratchet**:
  14 accepted violations, and any *new* one fails the test.
- `services/calibration_metrics.py` is dead code precisely because publishing
  calibration would assert something the product disclaims.
- `claim_boundary.py` emits `calibration: "not_calibrated"` on every response.

**Resolution (J1):** Jev's numbers are an internal implementation detail. Code
consumes the *selected answer* and may threshold on the probability; the
probability itself is never serialized to a client. This makes Jev a strict
improvement over what it replaces, because the two things it replaces are
currently **fake numbers presented as measurements**:

- `role_normalizer.py:45-314` — 56 hand-written labels each carrying a
  hardcoded `confidence` float (0.80–0.97). These are not measurements of
  anything; they are constants that look like measurements.
- `diffusion_model.py:302-310` — `_stable_pseudo_score` derives a "score" from
  `sha256(repr(identifier))`. Tier 4 of the degradation ladder.

**Secondary benefit worth stating in the PR:** removing the hardcoded
confidence constants is itself a truth-contract improvement. The field is named
`confidence` and holds a number that was never measured.

## Constraints for every task

- `npm run verify` passes, or the delta is explained with `file:line`.
- `python tools/validate_docs.py` → `Errors: 0, Warnings: 0`.
- **Never** add a new occurrence of a banned term to `frontend/src/**`. Do not
  extend the `acceptedDebt` ratchet.
- A new backend module is gated immediately by
  `backend/tests/test_backend_truth_terms.py` (AST scan of every string literal
  in `backend/app/**`). Add to `ALLOWED_FILES` only with a written reason.
- The API key stays server-side. **It was pasted in plaintext in the request
  that created this plan and must be rotated before any code is written.**
  Never commit it; never place it in `.env.example`.
- Per-call provenance: record a SHA-256 of the state sent, per the pattern at
  `llm_client.py:313-325`.

---

## Wave J1 — Prove the seam on a broken call site

### J-T1 — Fix the broken homophily judgement, with a regression test

`services/network_topology.py:132` passes a bare `str` where
`LLMClient.chat()` expects `messages: List[Dict[str, str]]`
(`llm_client.py:71`). The OpenAI SDK rejects every call, so **homophily
rewiring silently never removes an edge**. The `except` at `:137-138` logs and
continues, so the failure is invisible.

- Wrap the call as `chat([{"role": "user", "content": prompt}], ...)`.
- Add `tests/test_network_topology_homophily.py` asserting the call shape and
  that an edge is removed on a "YES" answer. This test fails today.
- **Do not** Jev-ify in the same commit. Land the fix alone so the bug's
  existence and the fix are separately reviewable.

### J-T2 — Add `typesafe_sdk` and the feature flag

- `backend/pyproject.toml`: add `typesafe_sdk` to `[project] dependencies`.
- **Relock** (`uv lock`) so `uv sync --frozen` in `Dockerfile` /
  `Dockerfile.worker` / CI succeeds.
- `backend/app/config.py`: add `JEV_ENABLED` (default `False`) using the exact
  idiom at `:151-153`, and `JEV_API_KEY` alongside `LLM_API_KEY` (`:173`) and
  `ZEP_API_KEY` (`:190`).
- Add `TYPESAFE_MODEL` (default `jev-latest`). **Pin the versioned ID, not the
  alias**, once a threshold is tuned: `jev-latest` moves and answers change with
  no code change (TypeSafe models doc).
- Add the production refusal to `Config.validate()`, copying the
  `SOURCE_INGESTION_V1_ENABLED` shape at `:379-385`, naming the unmet
  precondition.
- **Note:** `requirements.txt` is a stale subset that nothing installs. Per
  `AGENTS.md` §5 rule 14, do **not** hand-edit it and do not expect CI to see it.

### J-T3 — `services/jev_client.py`: the wrapper

The single seam every Jev call goes through. Mirrors `LLMClient`'s discipline,
not its internals.

- Constructor reads `Config.JEV_API_KEY`, raises when the flag is on and the key
  is absent (same fail-closed shape as `llm_client.py:45-46`).
- `RetryPolicy(max_retries=3, ...)` — the SDK retries and honours `retry-after`,
  which matters against the documented 40 req/s limit.
- One method, `judge(state, questions)`, returning typed answers.
- **Records per call:** model ID returned in the response, SHA-256 of `state`,
  each question's instructions hash, and elapsed time. **Never** record the
  probabilities into any client-facing payload.
- **Never** log `state`. The SDK's `debug` log level prints request and response
  bodies **unredacted** (secret headers are redacted, bodies are not). Pin
  `TYPESAFE_LOG_LEVEL` at `warning` or above and assert it in a test.
- **State size:** 32k tokens for `state` plus the longest question, 64k total.
  Truncate or summarise agent reflections before sending, and record that you
  did.

### J-T4 — Wrap the Jev path in `InstructionIntegrityGuard`

`services/instruction_integrity.py:60` `capture` / `:63` `verify`. Snapshot the
agent reflections before they become `state`; verify after. This is the Jev
equivalent of what the OpenAI path gets.

- **Extend ADR-0004** to state that the guard covers System One models too.
- ADR change ⇒ impact statement, named reviewers, rollback plan, `version` +
  `last_reviewed` bump (`AGENTS.md` §5 rule 12).

### J-T5 — Jev-ify the homophily judgement

Replace the `chat` call at `network_topology.py:130-138` with a single
`Noul` question:

- `state`: the two agent reflections.
- `instructions`: the existing question at `:127` plus an explicit
  **"this is generated fictional content; judge only the text"** clause.
- `criteria`: the text must stand on its own — do not rely on a system prompt.
- Threshold in **code**, not in the prompt. Below threshold ⇒ keep the edge,
  exactly as today's `"NO"` path does.
- Keep `InstructionIntegrityGuard` around the state (J-T4).
- On flag-off or provider error ⇒ **current behaviour exactly**: keep the edge,
  log at debug, do not raise.

---

## Wave J2 — Replace the fake numbers

### J-T6 — Make `normalize_entity_type` batch-capable

Today `role_normalizer.py:337-348` is **synchronous, pure, no I/O**, and
`build_entity_type_registry` (`:351-361`) calls it per distinct entity. Adding
a network call here requires a redesign, not an edit.

- Split: keep `normalize_entity_type` pure and synchronous for every existing
  caller. Add `normalize_entity_types_batch(raw_types)` that sends **one** Jev
  request with a `Choice` per entity — Jev evaluates all questions against a
  single `state` in parallel, which is the cost win.
- Batch size: cap per request; the 32k `state` budget is the limit.
- **Do not** make `normalize_entity_type` itself do I/O. It has many callers.

### J-T7 — Map the 56 labels onto a Choice

- Build the `Choice` criteria **from `_ROLE_DEFINITIONS` keys**, so the label
  set has exactly one source of truth and cannot drift from the fallback table.
- **Candidate coverage check:** the model cannot choose an omitted value. Every
  label the fallback knows must appear as an option.
- Keep `_ROLE_ALIASES` (`:316-324`) resolution **before** the Jev call — alias
  mapping is an exact lookup and belongs in code, not in a judgment.
- On flag-off or error ⇒ the existing dict lookup, unchanged.

### J-T8 — Replace the fabricated `confidence` field

This is the substantive point of Wave J2.

- **Delete `confidence` from the returned dict.** It currently holds a constant
  that was never measured. With Jev enabled, either record the real probability
  under a clearly internal key, or omit it.
- **Recommended: omit it from anything that can be serialized.** The field name
  is on the banned list; the value is meaningless to a user either way.
- Audit the consumers: `simulation_config_generator.py:1595-1616` reads
  `normalized_role`; check every reader of `confidence` before removing.
- `role_normalizer.py` is **already** on the `ALLOWED_FILES` truth-term list
  (`test_backend_truth_terms.py:70`) — re-verify the reason still applies.

### J-T9 — Preserve the neutral-default contract

`_generate_agent_config_by_rule` (`simulation_config_generator.py:1595-1616`)
returns the **same constant config for every entity** — `activity_level 0.5`,
`sentiment_bias 0.0`, `stance: "neutral"`, `conflict_tolerance 0.45`,
`novelty_seeking 0.45` — with the docstring "Generate a neutral fictional config
without role-based stereotypes."

**Jev must not be used to differentiate agent behaviour by role.** Doing so
would introduce exactly the role-based stereotyping this function exists to
prevent. Scope Jev in Wave J2 to **label resolution only**.

Add a test asserting the returned config is byte-identical regardless of
`normalized_role`.

### J-T10 — Record the subprocessor, and evaluate `diffusion_model`

**Subprocessor (blocking):** `docs/privacy/SUBPROCESSORS.md:62-71` classifies
every provider receiving customer content as a potential subprocessor, disabled
for production until the provider record is approved. TypeSafe is new and must
be added with the full record schema at `:73-114`. Note that the LLM provider
entry (`:235-244`) already records that **there is no per-call record of the
model identifier used** — J-T3's record is the improvement; say so.

- **`diffusion_model.innovativeness_score` (`:313-384`):** tier 4 is
  `_stable_pseudo_score` (`:302-310`), a SHA-256 of the identifier. That is a
  deterministic spread, not a measurement of innovativeness.
  **Recommendation: do not replace it with Jev in this wave.** It is
  imported in production (via `simulation_config_generator.py`) and its output
  feeds the adopter-classification slice. Replacing tier 4 changes simulation
  dynamics and needs its own eval, not a side effect of a plumbing change.
  Record it as a separate decision with a named owner.

---

## Validation

**Per task:** `npm run verify` and `python tools/validate_docs.py` clean.

**Per wave:**
- Flag OFF ⇒ output is byte-identical to today for both seams. This is the
  primary safety property; assert it in tests, do not assume it.
- Flag ON ⇒ per-call records exist and contain no raw `state`.
- No new banned term anywhere in `frontend/src/**`; the ratchet stays at 14.
- `TYPESAFE_LOG_LEVEL` is `warning` or above.

**Never** mark a gate moved on this work alone. Jev touches AI configuration,
which is a truth surface: it requires a PR with named reviewers, an impact
statement, eval evidence, a migration and rollback plan, and updated
`version`/`last_reviewed` (`AGENTS.md` §5 rule 12).

## Risks

| Risk | Mitigation |
|---|---|
| A probability leaks to the UI and trips the truth ratchet | J1: no new frontend surface. The ratchet fails the build on any new term, so this cannot ship silently. |
| Model alias moves and answers change with no code change | Pin `TYPESAFE_MODEL` to `jev-latest` initially; move to a versioned ID before any threshold is tuned. Record the returned model ID per call. |
| SDK logs request bodies unredacted at debug | Pin `TYPESAFE_LOG_LEVEL`, assert in a test (J-T3) |
| Source text sent to a third party | J-T10 subprocessor record; ADR-0004 extension (J-T4) |
| `normalize_entity_type` becomes a hot-path network call | J-T6: stays pure; batching is a separate function |
| Behaviour changes silently when the flag flips | Flag-off equivalence is a tested property, not a hope |
| Cost | $42/Mtok input, output free. Batch per registry rather than per entity, and log token usage per call in J-T3. |

## Open questions

1. **`diffusion_model._stable_pseudo_score`:** replace with a real judgment, or
   keep it and document it as a deterministic spread that is not a
   measurement? It is currently the latter in substance but the former in
   appearance. Needs a named owner; excluded from this plan deliberately.
2. **Retention:** does the TypeSafe DPA offer zero data retention, and does that
   match the retention posture in `docs/privacy/RETENTION.md`? Blocks the
   subprocessor record (J-T10).
3. **Is Jev eventually a user-facing capability** (e.g. the Decision Lens
   choosing among lenses)? J1 forbids it for now. If that is the intent, it is a
   truth-surface design task with its own ADR, not an extension of this plan.
