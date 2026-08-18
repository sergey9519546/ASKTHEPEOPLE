---
title: "Trustworthy Agent Boundary Design"
status: "Approved"
version: "1.0.0"
owner: "Architecture + Security + Methodology + AI Evaluation"
last_reviewed: "2026-08-08"
review_cycle: "Per agent-boundary change"
research_cutoff: "2026-08-08"
baseline_commit: "55aa182"
applies_to: "decision-lens preparation, review, runtime adaptation, execution admission, and live scenario observations"
---

# Trustworthy Agent Boundary Design

## 1. Decision

Adopt a controlled transition from identity-like OASIS profiles to reviewed
functional decision lenses.

Existing profile artifacts remain readable as legacy audit records. They are
never silently rewritten and cannot authorize a new run. Every newly prepared
run must use a versioned decision-lens artifact, an approval record bound to the
artifact hash, a derived runtime adapter, and a passing preflight.

Live intervention is narrowed to typed public scenario observations. Runtime
events cannot change a system message, tool contract, output schema, identity,
goal, or decision-lens definition.

This specification is the first implementation slice in a larger upgrade. It
closes the highest-risk character and instruction-boundary gaps while creating
the stable seam needed for reproducible experiments, canonical world state,
network/feed causality, lifecycle repair, live evaluation, and fail-closed
report validation.

## 2. Authority and state legend

This specification is subordinate to, in order:

1. `docs/product/PRODUCT_TRUTH_CONTRACT.md`;
2. `docs/product/USE_POLICY.md`;
3. `docs/security/` and `docs/privacy/`;
4. `docs/product/METHODOLOGY.md`;
5. `docs/release/ACCEPTANCE.md`;
6. accepted ADRs under `docs/architecture/adr/`;
7. `docs/architecture/index.md` and `docs/architecture/state-machines.md`.

State terms in this document:

- **CURRENT** — implemented and observable in the working repository.
- **PARTIAL** — implemented but materially deficient against a binding rule.
- **TARGET** — the approved end state for this boundary.
- **TRANSITION** — an explicitly temporary bridge that remains truthful about
  its limitations.

## 3. Scope decomposition

### 3.1 In scope for this slice

- a strict decision-lens domain schema;
- versioned generation through the prompt registry;
- deterministic structural and truth validation;
- explicit human review and hash-bound approval;
- a `NEEDS_REVIEW` preparation state;
- fail-closed execution admission before any restart side effect;
- a derived OASIS runtime adapter with a custom semantic prompt;
- typed public scenario observations;
- an idempotent, per-platform event journal and application acknowledgement;
- frontend decision-lens review and execution locking;
- manifest identities for lens, review, prompt, schema, validator, and adapter;
- read-only legacy compatibility.

### 3.2 Explicitly outside this slice

- PostgreSQL and object-storage migration from ADR-0012;
- workspace identity and RBAC from ADR-0009;
- private or targeted information delivery;
- calibrated behavioral or psychometric claims;
- exact model-output replay and durable counterfactual forks;
- a canonical resource/payoff/world consequence engine;
- network and recommender repair;
- external human behavioral validation;
- final-report deterministic validation.

Those are required later slices. They must not be described as CURRENT merely
because this boundary is implemented.

## 4. Current evidence and defects

### 4.1 Identity-like profiles — PARTIAL

`backend/app/services/oasis_profile_generator.py:27-66` stores a name,
username, biography, persona, age, gender, MBTI, country, profession, and
interests. `backend/app/prompts/definitions/profile_generation_v1.yaml:25-47`
requires those fields. `frontend/src/components/Step2EnvSetup.vue:58-95` and
`:540-653` present them as character attributes.

This conflicts with `docs/product/METHODOLOGY.md:307-350`, which requires
functional labels, no biographies or first-person identity narrative, no
psychometrics by default, no demographics without reviewed relevance, and
four to eight materially different lenses.

### 4.2 Missing review admission — PARTIAL

`backend/app/services/simulation_preflight.py:143-237` validates files, export
shapes, capacity, publishers, model configuration, and imports, but not lens
approval. `backend/app/api/routes/execution_routes.py:143-235` can create and
dispatch a run without an approval record. This conflicts with the release
blocker at `docs/release/ACCEPTANCE.md:293`.

### 4.3 Instruction mutation — PARTIAL

`backend/app/api/routes/execution_routes.py:389-442` accepts an untyped event
name and payload. `backend/app/services/simulation_runtime_contract.py:853-870`
appends `persona_modification`, `persona_change`, and `dynamic_instruction`
content directly to agent system messages.

### 4.4 OASIS semantic leakage — PARTIAL

The pinned OASIS generators include persona, MBTI, gender, age, and country in
the Reddit agent profile at
`backend/.venv/Lib/site-packages/oasis/social_agent/agents_generator.py:577-604`.
The Twitter generator includes `user_char` and description at `:624-646`.
`SocialAgent` supports a caller-supplied `user_info_template` at
`backend/.venv/Lib/site-packages/oasis/social_agent/agent.py:58-83`, but the
current generators do not use it.

### 4.5 Lossy event transport — PARTIAL

`backend/app/services/simulation_observation_store.py:14-29` uses a shared
process-local queue as fallback. Parallel platform consumers can therefore
observe different event sets. The current implementation records events before
knowing whether the intended platform action succeeded and treats unsupported
events as applied at
`backend/app/services/simulation_runtime_contract.py:790-873`.

## 5. Approaches considered

### 5.1 Hard cutover

Delete or migrate all legacy profile artifacts and require the new schema
immediately.

- Benefit: smallest conceptual surface after migration.
- Rejected because: current user-owned simulations and audit records would be
  invalidated or semantically rewritten.

### 5.2 Thin approval wrapper

Keep the current persona schema and add an approval checkbox before start.

- Benefit: lowest implementation cost.
- Rejected because: approval would bless the wrong representation and leave
  identity leakage, psychometric anchoring, and instruction mutation intact.

### 5.3 Controlled transition — selected

Preserve legacy data as read-only evidence, generate new functional lenses,
derive a constrained runtime adapter, and require hash-bound approval.

- Benefit: closes the execution boundary without destroying history.
- Cost: two readable artifact versions exist during the transition.
- Control: only the new version is executable.

## 6. Domain model

### 6.1 `DecisionLensArtifactV1`

Immutable artifacts are stored at
`decision_lens_artifacts/{artifact_id}.json`. The atomic current pointer is
`decision_lenses.current.json` and contains only `artifact_id`, `revision`,
`artifact_sha256`, and `updated_at`. A pointer update never changes an artifact.

```text
schema_version = "decision-lens/v1"
artifact_id
simulation_id
revision
created_at
prompt_record
input_refs[]
lenses[4..8]
truth_fields
artifact_sha256
```

`artifact_sha256` is computed over the canonical JSON representation with the
hash field omitted. Array ordering and object-key ordering are deterministic.

### 6.2 `DecisionLensV1`

```text
lens_id
title
purpose
context
goals[]
constraints[]
access_conditions[]
incentives[]
switching_costs[]
information_conditions[]
decision_criteria[]
excluded_inferences[]
uncertainty_notes[]
input_refs[]
sensitive_attributes[]
status
```

Rules:

- `title` is a functional label, not a realistic person name.
- First-person identity narratives are rejected.
- `name`, `username`, `bio`, `persona`, `age`, `gender`, `mbti`, avatar fields,
  and population-weight fields are forbidden extra properties.
- Every lens has at least one goal, constraint, information condition,
  decision criterion, excluded inference, uncertainty note, and input reference.
- An input reference is an existing approved source segment, starting
  condition, declared assumption, critical uncertainty, or disclosed graph
  record. The validator resolves every reference; generation cannot invent IDs.
- A generated lens with no source-segment basis uses an approved assumption or
  uncertainty reference and remains `GENERATED_GENERATED`; it never receives a
  fabricated source location.
- Sensitive attributes are empty by default. Adding one requires a separate
  relevance statement, retention/export restriction, and per-attribute review
  disposition before the lens can be approved.
- Material distinction is measured over goals, constraints, access,
  information, and decision criteria. Cosmetic wording does not count.
- Failure to produce four materially distinct lenses produces an explicit
  incomplete result; the system does not pad the set with clones.

### 6.3 Truth fields

Each artifact carries immutable values from the Product Truth Contract:

```json
{
  "output_origin": "synthetic",
  "human_respondent_count": 0,
  "is_forecast": false,
  "is_public_opinion_measure": false,
  "is_causal_evidence": false,
  "source_role": "starting_conditions_only",
  "human_validation_scope": "external_to_synthetic_run"
}
```

## 7. Review model

### 7.1 Review artifact

Immutable review records are stored at
`decision_lens_reviews/{review_id}.json`. The atomic current pointer is
`decision_lens_review.current.json` and contains only `review_id`,
`lens_artifact_id`, `lens_artifact_sha256`, `review_sha256`, and `updated_at`.
A pointer update never changes a review record.

```text
schema_version = "decision-lens-review/v1"
review_id
simulation_id
lens_artifact_id
lens_artifact_sha256
reviewed_at
reviewer_assertion
authentication_strength
dispositions[]
overall_status
review_sha256
```

`reviewer_assertion` is a non-empty human-supplied name or accountable role.
It is not a verified user identity. `authentication_strength` is derived by the
server, never accepted from the request. Its allowed TRANSITION values are
`application_bearer_self_attested_reviewer` and
`development_no_auth_self_attested_reviewer`. The latter cannot authorize a
production-mode run. The UI labels the limitation and must not claim verified
authorship. A future workspace actor ID supersedes both values after ADR-0009
lands.

Each lens disposition is `approved` or `rejected` and includes a bounded review
note. Every sensitive attribute has its own `approved` or `rejected`
disposition and justification.

The overall status is `approved` only when all lenses and all sensitive
attributes are approved. A changed lens artifact hash makes the review stale
without mutating the historical review record.

### 7.2 Review API

```text
GET   /api/simulation/{simulation_id}/decision-lenses
PATCH /api/simulation/{simulation_id}/decision-lenses/{lens_id}
PUT   /api/simulation/{simulation_id}/decision-lens-review
```

`PATCH` creates a new whole-artifact revision and hash. It never mutates an
approved artifact in place. The previous artifact and review remain readable.
The new revision returns to `pending` review.

`PUT` is idempotent for the same artifact hash and canonical review body. A
different body creates a new review record and supersedes the prior current
review without deleting it.

Errors use stable codes:

- `404 simulation_not_found`;
- `409 decision_lens_review_required`;
- `409 decision_lens_review_stale`;
- `409 decision_lens_incomplete`;
- `422 decision_lens_invalid`;
- `422 sensitive_attribute_approval_required`.

## 8. Preparation and execution state

Add `NEEDS_REVIEW` to the current simulation preparation status as a
TRANSITION state:

```text
CREATED -> PREPARING -> NEEDS_REVIEW -> READY -> RUNNING
                         |      ^
                         v      |
                       FAILED   +-- new artifact revision
```

Preparation generates and validates the lens artifact, persists the prompt
record, and stops at `NEEDS_REVIEW`. It does not mark the simulation `READY`.

Approval triggers runtime-adapter derivation and preflight. Only a passing
preflight moves the simulation to `READY`.

The start admission check runs immediately after simulation lookup and before:

- force-stop;
- log cleanup;
- task creation;
- Celery dispatch;
- simulation state mutation.

`SimulationRunner.start_simulation` repeats the same check so a worker or
internal caller cannot bypass the HTTP boundary.

Legacy simulations without a valid `decision_lenses.current.json` pointer and
referenced immutable artifact return
`409 decision_lens_review_required` with remediation `regenerate_decision_lenses`.
They remain available through read APIs and are labeled
`legacy_profile_artifact_non_executable`.

## 9. Runtime adapter and immutable instructions

### 9.1 Local factory

Add an application-owned OASIS factory rather than editing `.venv` code. The
factory constructs `SocialAgent` with a custom `user_info_template` containing
only approved functional lens fields and permanent truth constraints.

The semantic prompt includes:

- the functional title;
- purpose and context;
- goals and constraints;
- access and information conditions;
- incentives and switching costs;
- decision criteria and excluded inferences;
- uncertainty notes;
- the synthetic/non-forecast/source-role disclosure.

It excludes age, gender, MBTI, realistic names, biographies, role-derived
personality, source instructions, and hidden reasoning requests.

Platform signup may require a public account name and description. The derived
values are deterministic and disclosed:

```text
name = "Decision Lens {ordinal}: {functional title}"
username = "decision_lens_{ordinal:02d}"
description = "Synthetic decision lens for scenario exploration; not a person."
```

These transport values never alter the semantic prompt. The runtime adapter is
written to `decision_lens_runtime.v1.json` and is derived only after approval.
Its hash, adapter version, and source lens hash are stored in the run manifest.

### 9.2 Instruction integrity

At agent construction, compute a canonical hash of every system message. The
runtime verifies the hash before and after each round and before shutdown.

A mismatch:

- records a structured `instruction_integrity_violation` without prompt text;
- stops the affected platform;
- fails the run attempt;
- prevents final-report generation.

No API or runtime helper exposes a system-message mutation operation.

## 10. Typed public scenario observations

### 10.1 Deliberate restriction

This slice supports public observations only. Private facts, targeted messages,
persona changes, hidden instructions, tool changes, and schema changes are
rejected. They require a later information-boundary specification and secret
leakage evaluation.

### 10.2 Request schema

```text
event_id                 optional client UUID; server UUID when absent
event_type               "public_scenario_observation"
content                  1..4000 Unicode characters
platforms                non-empty subset of ["twitter", "reddit"]
effective_round          optional non-negative integer; next round by default
duration_rounds          integer 1..24; default 1
origin                   "USER_STATED" or "ASSUMPTION_DECLARED"
input_refs[]             existing approved input references; optional for USER_STATED
```

Unknown properties are forbidden. Content is stored as data and wrapped in an
explicit untrusted-observation delimiter. It cannot introduce tools or replace
system/developer instructions.

The API returns `202` after the event is durably recorded, not after it is
applied. A status endpoint exposes per-platform state:

```text
GET /api/simulation/{simulation_id}/events/{event_id}
```

### 10.3 Event journal — TRANSITION

Use a per-simulation SQLite journal named `runtime_event_journal.sqlite` with:

```text
events(event_id PRIMARY KEY, canonical_payload, payload_sha256, created_at)
event_deliveries(event_id, platform, status, effective_round,
                 duration_rounds, first_applied_round, last_applied_round,
                 applied_agent_count, error_code,
                 PRIMARY KEY(event_id, platform))
```

Allowed delivery states are `pending`, `applied`, `rejected`, and `failed`.
Insert is transactional. Reusing an event ID with the same payload is
idempotent; reusing it with a different hash returns `409 event_id_conflict`.

The child runtime polls the journal at round boundaries. Redis PubSub may wake a
poll early, but it is never the source of truth. Each platform claims its own
delivery row transactionally. For a round, an eligible agent is an agent selected
by the recorded activation schedule and therefore receiving an action prompt in
that round. A platform marks a delivery applied only after the observation block
was supplied to every eligible agent prompt for that round. If no agent is
eligible, the delivery remains pending until the next round inside its delivery
window. Unsupported, expired, or malformed events are rejected with a code;
they are never counted as applied.

SQLite is explicitly TRANSITION local storage. It does not satisfy ADR-0012 for
production. The interface must permit replacing the repository with PostgreSQL
without changing route or runtime semantics.

## 11. Preflight and manifest

Preflight fails unless all of the following hold:

- exactly one current `decision-lens/v1` artifact exists;
- it contains four to eight materially distinct valid lenses;
- every input reference resolves;
- prohibited identity fields are absent;
- sensitive-attribute rules pass;
- the current review approves the exact artifact hash;
- the runtime adapter derives from that exact artifact and review;
- semantic system-prompt fixtures contain no compatibility demographics;
- every accepted runtime-control path appears in a versioned static consumption
  registry naming its production consumer and mutation test;
- an unknown control or a non-neutral value for a deprecated/inert control is
  rejected; neutral deprecated fields are removed from the derived runtime
  adapter and recorded as `deprecated_neutral_omitted` in preflight;
- prompt, schema, validator, adapter, artifact, and review versions/hashes are
  available for the manifest.

The run manifest records:

```text
decision_lens_artifact_id + sha256
decision_lens_review_id + sha256 + authentication_strength
prompt_id + version + input/output hashes
schema_id + version
validator_id + version
runtime_adapter_id + version + sha256
instruction_hashes by synthetic agent ID
event_journal_schema_version
```

The manifest continues to disclose uncontrolled seed and single-replicate
status until the reproducible-experiment slice lands.

## 12. Frontend behavior

`Step2EnvSetup.vue` becomes a decision-lens review docket while preserving the
current civic-wayfinding design work.

Each lens presents:

- functional title and purpose;
- goals, constraints, access, and information conditions;
- incentives and switching costs;
- decision criteria, excluded inferences, and uncertainties;
- input references with origin labels;
- sensitive-attribute review, only when present;
- approve/reject disposition and review note.

The interface removes name, username, biography, age, gender, MBTI, avatar, and
sample-like counts from the executable path. Legacy views remain read-only and
carry `LEGACY PROFILE / CANNOT AUTHORIZE A RUN`.

The Run action remains disabled until the server reports an approved current
artifact and passing preflight. The client does not infer readiness from local
checkboxes. Editing or regeneration immediately shows `REVIEW STALE` and locks
the action again.

## 13. Error handling and observability

- Validation errors are bounded RFC 7807 responses without raw model output or
  source content.
- Rejected lens generation persists structured validator codes and prompt/output
  hashes, not hidden reasoning.
- Approval writes are atomic in the TRANSITION filesystem store.
- Event-journal errors fail the request or delivery explicitly; no in-memory
  fallback can claim durability.
- Agent-construction, prompt-construction, and instruction-integrity errors have
  a zero-tolerance budget and fail the affected platform and run. General action
  error-budget policy remains part of the later lifecycle/reliability slice and
  is not claimed complete here.
- Logs contain IDs, hashes, versions, state transitions, and bounded codes; they
  exclude lens prose, event content, source text, and hidden reasoning.

## 14. Acceptance tests

Implementation follows red-green-refactor. Required tests include:

### 14.1 Domain and provenance

- valid four-lens fixture passes;
- three lenses return explicit incomplete status;
- cosmetic clones fail material-distinction validation;
- every prohibited identity property fails with a stable code;
- nonexistent input references fail;
- no-source lenses require an approved assumption or uncertainty reference;
- sensitive attributes fail without per-attribute approval;
- canonical serialization and hash are deterministic.

### 14.2 Review and lifecycle

- unreviewed and legacy simulations cannot start;
- a rejected lens cannot produce overall approval;
- an artifact edit invalidates an earlier review;
- the review API is idempotent for identical input;
- start admission happens before force-stop, cleanup, task creation, dispatch,
  or state mutation;
- the runner repeats admission for non-HTTP callers;
- approval plus passing preflight is the only path from `NEEDS_REVIEW` to
  `READY`.

### 14.3 Runtime adapter

- runtime adapters derive byte-identically from identical approved input;
- system prompts contain every required functional field;
- system prompts contain no age, gender, MBTI, realistic biography, or role
  stereotype;
- changing an approved goal changes the semantic prompt;
- changing a nonsemantic transport username does not;
- system-message hashes remain constant across normal rounds and adversarial
  event input;
- any hash mismatch fails the platform and run.

### 14.4 Events

- instruction-like and unknown event types return `422`;
- unknown fields and oversized content return `422`;
- insert occurs before `202`;
- same event ID and payload is idempotent;
- same event ID with another payload returns `409`;
- parallel platforms claim independent delivery rows;
- Redis absence does not lose a journaled event;
- an event is marked applied only after all eligible prompts received it;
- unsupported events are rejected, never counted as applied;
- observation delimiters cannot alter system-message hashes.

### 14.5 Frontend and regression

- executable preparation shows functional lenses, not identity attributes;
- legacy artifacts show a read-only non-executable label;
- Run remains locked for pending, rejected, stale, failed, or legacy states;
- Run unlocks only from server-confirmed approval and preflight;
- regeneration relocks Run;
- existing truth-rail, accessibility, keyboard, and reduced-motion tests pass.

## 15. Rollout and rollback

1. Land schemas, validators, artifact repository, and tests behind
   `DECISION_LENS_V1_ENABLED` with default off.
2. Land generation and review APIs; keep execution gate in report-only mode in
   development fixtures.
3. Land the local OASIS factory, instruction hashing, and event journal.
4. Land the frontend review docket.
5. Enable the gate by default for newly prepared simulations.
6. Mark all legacy artifacts read-only and non-executable.
7. Remove the old injection event types and in-memory fallback after migration
   tests pass.
8. Remove the feature flag after one release with no compatibility rollback.

Rollback disables new preparation and execution but preserves all artifacts and
review history. It never re-enables unreviewed execution or system-message
mutation.

## 16. Completion boundary

This slice is complete only when:

- documentation validation passes with zero warnings and errors;
- all new tests have demonstrated the intended red-green cycle;
- focused backend and frontend suites pass;
- touched-file lint passes;
- the start route, runner, and preflight all fail closed on review state;
- system-message mutation operations no longer exist on the production path;
- the decision-lens UI is browser-checked at desktop and mobile widths;
- the code and architecture documentation use CURRENT/PARTIAL/TARGET/TRANSITION
  truthfully;
- no user-owned unrelated worktree change is overwritten or included in the
  implementation commits.

Passing this slice does not establish human behavioral validity, calibration,
representativeness, reproducibility, or release readiness for the full product.
