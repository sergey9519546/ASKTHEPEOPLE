# Task 6 revised brief — First-class paths, typed dependencies, and the brief gate

Read this first. It replaces the short Task 6 entry in the supporting execution
plan as the implementation contract for this work.

## Status and authority

**Task status: PROPOSED / REVISION REQUIRED.**

The six-line Task 6 entry in
`docs/superpowers/plans/2026-08-08-decision-workspace-foundation.md` is not an
implementation-ready authorization to add tables or public routes. The design
specification remains **PROPOSED / REVISION REQUIRED**. This brief preserves
that status. It does not promote the path experience, persistence model, or
comparison design to approved production behavior.

Authority for this task, in descending order:

1. `docs/product/PRODUCT_TRUTH_CONTRACT.md`;
2. `docs/product/USE_POLICY.md`;
3. `docs/security/`;
4. `docs/privacy/`;
5. `docs/product/METHODOLOGY.md`;
6. `docs/release/ACCEPTANCE.md`;
7. `docs/architecture/adr/ADR-0003-durable-run-orchestration.md`,
   `ADR-0009-multi-tenant-isolation.md`, and
   `ADR-0012-canonical-transactional-and-object-persistence.md`;
8. `docs/architecture/state-machines.md`,
   `docs/architecture/data-model.md`, and the AI implementation guides;
9. the design and content system, including the proposed experience spec;
10. `docs/exec-plans/04-durable-orchestration-and-path-engine.md`;
11. `AGENTS.md`;
12. this brief and the supporting decision-workspace master plan;
13. code comments and generated documentation.

Use the repository state legend exactly:

- **CURRENT** — implemented and verified in the repository;
- **PARTIAL** — implemented but materially deficient;
- **TARGET** — approved production design not yet reached;
- **TRANSITION** — reversible work moving CURRENT/PARTIAL toward TARGET.

No checkpoint below may be relabeled CURRENT merely because its unit tests
pass. The completion gates at the end of this brief control that claim.

## Audit conclusion

The CURRENT path capability is PARTIAL and cannot safely be extended through
the migration and route list in the supporting plan:

- The landed `PossiblePath` contains only a string ID, string run ID, display
  label, branch reason, origin, steps, and truth bundle
  (`backend/app/domain/decision_workspace.py:98-136`). It does not model the
  reviewed branch bases, scenario frame, decision lenses, considerations,
  conflicts, missing information, disconfirming conditions, validation
  questions, coverage, review, semantic lineage, or artifact identity required
  by `docs/product/METHODOLOGY.md:354-447`.
- Its ID validator is a general ASCII identifier regex
  (`backend/app/domain/decision_workspace.py:9`), while the normative data
  model requires UUIDv7 physical identifiers and treats `P-03`-style codes as
  scoped display identifiers, not primary keys
  (`docs/architecture/data-model.md:37-52`).
- The landed provenance relations and allowlist
  (`backend/app/domain/decision_workspace.py:35-44` and `:161-230`) do not use
  the normative `epistemic-ledger/v2` vocabulary locked by authority commit
  `ce132a5`. The authority conflict is resolved; the TRANSITION domain code is
  not yet updated or approved, so no persisted edge may be created from that
  older allowlist.
- The ORM metadata has only organization, project, simulation, profile,
  attempt, and observation models (`backend/app/db/schema.py:8-62`). It has no
  path, canonical run, path review, epistemic assertion, epistemic edge,
  command receipt, lease, or outbox table.
- The only checked-in migration declares itself the root revision
  `384c98f88d53` (`backend/migrations/versions/384c98f88d53_initial_schema.py:14-18`)
  and creates an integer-key schema that already disagrees with the UUID ORM
  metadata (`backend/migrations/versions/384c98f88d53_initial_schema.py:21-40`).
  The proposed filename and revision ID in the supporting plan are therefore
  unsafe.
- The Task 3 workspace identity is a filesystem TRANSITION manifest. It issues
  `workspace_<uuid4>` and contains no organization identity
  (`backend/app/application/decision_workspace_service.py:124-142` and
  `:173-181`). Its availability is inferred by scanning legacy simulations and
  reports (`backend/app/application/decision_workspace_service.py:206-242`).
  It cannot authorize canonical tenant-owned path rows.
- The durable run kernel, repository, stage attempts, lease/fencing contract,
  and run routes described by Task 5 are absent on the audited head. A path
  writer consequently has no canonical run, active stage attempt, fencing
  token, transactional idempotency receipt, or immutable completion boundary.
- The legacy report agent creates a markdown report and embeds path language in
  prompts (`backend/app/services/report_agent.py:658-686` and `:1859-2061`),
  but its `Report` record has no structured path objects or typed lineage
  (`backend/app/services/report_agent.py:483-510`). Parsing those prose reports
  after the fact would fabricate structure and provenance.
- The existing `/api/simulation/compare` endpoint compares two legacy
  simulation IDs through `ValidationEngine`
  (`backend/app/api/routes/read_routes.py:525-562`). It is not the later
  semantic path comparison contract and must not be relabeled as such.

## Non-negotiable outcome

Task 6 eventually produces one canonical, run-owned path artifact system with:

- four to eight materially distinct possible paths for every complete path
  set;
- a richer pure domain independent of Flask, SQLAlchemy, Celery, provider
  payloads, and filesystem paths;
- UUIDv7 physical IDs, stable server-issued public IDs, and separately scoped
  server-owned semantic lineage IDs;
- first-class path steps, considerations, conflicts, missing-information
  items, disconfirming conditions, and validation questions;
- reviewed assumption and uncertainty-state branch bases;
- closed, typed provenance/dependency relationships whose endpoint roles are
  resolved from canonical records at write time;
- immutable path-set revisions, immutable review artifacts, canonical hashes,
  and an exact-hash gate before brief generation;
- PostgreSQL-authoritative, organization/workspace/run-scoped persistence;
- worker writes protected by the canonical stage lease, fencing token,
  idempotency receipt, optimistic concurrency, and outbox transaction;
- run-based list/detail/review APIs behind a default-off feature flag;
- truthful partial/unavailable/failed states and read-only legacy behavior;
- semantic identity evidence sufficient to begin Task 7 later, but no
  comparison implementation in this task.

Task 6 does **not** implement frontend surfaces, spatial rendering, two-run
comparison, changed-condition injection, external human evidence, decision-
owner conclusions, recommendations, probability, confidence, ranking, or
path scoring.

## Hard prerequisite gate — persistence is blocked

Checkpoint 1 (pure domain) may proceed after the authority reconciliation
below. **No path migration, ORM table, repository write, public write route, or
worker cutover may begin until every item in this section has passing evidence.**

### Tenant and actor identity

- A server-owned organization and workspace exist in PostgreSQL.
- The authenticated actor resolves to an organization/workspace membership and
  canonical role. A bearer token with global access is insufficient.
- Every aggregate and query carries both `organization_id` and `workspace_id`
  as required by ADR-0009. Neither value is accepted from a request, provider
  response, source file, task payload, or model output.
- Application authorization and PostgreSQL RLS both fail closed. Cross-scope
  IDs are indistinguishable from not found.
- Worker credentials and object keys are tenant scoped.

The filesystem workspace manifest from Task 3 remains a read-only TRANSITION
locator until this gate lands. It must not be copied into canonical rows as if
it proved organization ownership.

### Canonical schema and migration lineage

- The ORM metadata and checked-in migrations describe the same baseline.
- PostgreSQL, not SQLite, is the migration acceptance target.
- Organization, workspace, membership, decision version, reviewed input,
  epistemic ledger, run configuration, run, run-stage attempt, command receipt,
  lease, outbox, audit, and artifact-reference tables already exist.
- The application database role is subject to RLS; the migration role is
  separate.
- The then-current Alembic graph has exactly one head and no unapproved drift.

Task 6 must not silently repair the current unrelated metadata/migration drift
inside its path migration.

### Durable run and stage ownership

- Task 5 has landed a canonical run with the exact normative run states,
  immutable run configuration, append-only events, and optimistic version.
- A real `GENERATING_PATHS` stage attempt exists and is recoverable from
  canonical IDs.
- The stage lease has a monotonic fencing token and heartbeat. A stale worker
  cannot register an accepted artifact.
- Durable command receipts and outbox publication are committed in the same
  transaction as a canonical write.
- Retry creates a new stage attempt; rerun creates a new run. No force restart
  deletes or reuses prior path identity.
- A stopped, retryable-failed, terminal-failed, or partial run cannot produce a
  final brief or become completed by client inference.

### Reviewed inputs and release identity

- Decision version, starting conditions, assumptions, uncertainty states,
  decision lenses, rules, and exclusions are canonical and immutable for the
  run configuration.
- Every referenced source version is READY under the secure source-ingestion
  and review state machines. Filesystem presence is not readiness.
- Prompt, model, schema, validator, methodology, path-generator, and simulation
  adapter release IDs are exact and immutable.
- Private object storage is available for the raw structured provider artifact
  and rejected/quarantined output. Relational path rows may reference only an
  accepted object hash.

If any prerequisite is absent, the implementation report records Task 6 as
**PROPOSED / REVISION REQUIRED** or **TRANSITION — DOMAIN ONLY** and stops
before persistence.

## Authority reconciliation status

Authority commit `ce132a5` resolved the normative provenance, path-review, and
comparison-cardinality ambiguities. It updated the Product Truth Contract,
data model, state machines, release acceptance/runbook, privacy map, proposed
experience spec, and structural docs validator. That commit changes the
TARGET contract; it does not update TRANSITION domain code, record the named
Architecture/Methodology/Product-Truth/Docs approvals, or satisfy any
persistence/release prerequisite.

### Provenance contract resolved normatively

The write contract is exactly `epistemic-ledger/v2`. Its closed roles,
relations, and 18 ordered `(from_role, relation, to_role)` triples live in the
higher-authority Product Truth Contract and are structurally locked by
`tools/validate_docs.py`. In particular:

- a path `BRANCHES_ON` an assumption or uncertainty state;
- a path `SEQUENCES` path steps;
- a path `SURFACES` considerations, conflicts, and missing information;
- a path is `DISCONFIRMED_BY` a disconfirming condition;
- a consideration `PRODUCES_QUESTION` a validation question;
- a brief statement `SUMMARIZES` a possible path or consideration;
- `SOURCE_SEGMENT -> POSSIBLE_PATH` and
  `SOURCE_SEGMENT -> CONSIDERATION` remain forbidden under every version; and
- retired TRANSITION relations are not aliases and are invalid for new writes.

Structural ownership remains a foreign-key/domain-containment fact unless an
exact v2 triple also exists. Every persisted edge stores the contract version,
and endpoint roles/origins are resolved from canonical assertions at write
time.

Before Checkpoint 1 changes the enum, named owners must record approval of
`ce132a5`. Then the pure-domain allowlist and exhaustive Cartesian-complement
test must consume v2 exactly. No `epistemic_edges` row, migration enum, or
compatibility alias may land before that approval and updated domain evidence.
If a repository-wide search finds an external consumer of the retired
non-persisted vocabulary, add a versioned read adapter; never accept both
forms on new writes.

### Four-to-eight path requirement

The normative methodology requires four to eight distinct paths
(`docs/product/METHODOLOGY.md:372-391`). This brief enforces that exact range:

- four and eight can become reviewable after all other validators pass;
- zero to three are `INCOMPLETE`, remain inspectable as partial artifacts, and
  cannot be approved or used for a final brief;
- nine or more are invalid provider output and fail the bounded generation
  attempt;
- the system never pads an incomplete set with paraphrases;
- path order, display code, color, geometry, and line length never encode
  likelihood, confidence, support, or quality.

### Exact-two comparison later

Authority commit `ce132a5` revised the proposed design spec to support
**exactly two** completed related runs. The prior viewport-dependent third
attempt is resolved and no longer exists in the specification. The docs
validator rejects a reintroduced third-input exception.

Task 6 creates no comparison route or comparison service. Before Task 7 starts,
named approval of the revised spec must be recorded, and Task 6 must have
evidence that semantic IDs exist, are server-owned, and survive the supported
lineage operations. Any count other than two must return `422` in Task 7,
regardless of viewport.

### Post-path review and run-state reconciliation

The methodology requires human review and locking of approved paths before
brief generation (`docs/product/METHODOLOGY.md:405-415`), while the normative
run machine has no separate post-path `NEEDS_REVIEW` transition. Do not invent
a 21st run state.

Use an independent path-artifact review state machine while the canonical run
remains `VALIDATING_OUTPUT`:

```text
GENERATED
-> INCOMPLETE | NEEDS_REVIEW
NEEDS_REVIEW
-> APPROVED | REJECTED | SUPERSEDED
APPROVED
-> SUPERSEDED only by creation of a new immutable revision
```

`VALIDATING_OUTPUT -> GENERATING_BRIEF` is permitted only when the exact
current path-set hash has an immutable approved review and all critical
validators pass. Waiting for review holds no worker lease. Rejection or a
revision creates a new path-set revision and new validation work while the run
remains `VALIDATING_OUTPUT`; it does not move the run backward or mutate a
completed artifact.

Authority commit `ce132a5` records and structurally locks this interpretation
in the architecture documentation. Named architecture/methodology approval and
the complete implementation evidence remain required before the brief gate is
enabled. If those owners reject the interpretation, persistence stops and a
state-machine ADR amendment is required.

## Identity contract

Physical, public, semantic, and display identities are different fields with
different jobs.

### Physical identity

- Every relational row ID is an application-issued RFC 9562 UUIDv7 stored in a
  PostgreSQL `uuid` column.
- Join-only tables may use a composite key only when they are never externally
  addressable, consistent with the normative data model.
- UUIDv4, truncated UUIDs, integers, provider IDs, model-proposed IDs, and
  client IDs are rejected for canonical rows.
- Python 3.11-3.13 has no standard `uuid.uuid7`; create one small audited RFC
  9562 helper or add one pinned, reviewed dependency. Do not silently call
  `uuid.uuid4()` behind a `uuid7` name.
- Tests inspect the UUID version and RFC variant bits. A deterministic clock
  and randomness seam is available for tests; production randomness is
  cryptographic.

Physical IDs are repository-internal and never serialized by the public API.

### Public identity

Every externally addressable aggregate has a server-issued public ID:

```text
path_set_<32 lowercase UUIDv7 hex>
path_<32 lowercase UUIDv7 hex>
path_step_<32 lowercase UUIDv7 hex>
consideration_<32 lowercase UUIDv7 hex>
conflict_<32 lowercase UUIDv7 hex>
missing_info_<32 lowercase UUIDv7 hex>
disconfirming_<32 lowercase UUIDv7 hex>
validation_question_<32 lowercase UUIDv7 hex>
path_review_<32 lowercase UUIDv7 hex>
```

The UUIDv7 encoded in a public ID is separately generated from the physical
row ID. Public IDs are stable across immutable revisions of the same logical
object. Requests may reference a public ID, but cannot choose one during
creation. Repository lookup always adds authorized organization, workspace,
run, and current-artifact scope.

### Semantic lineage identity

Every path, consideration, conflict, missing-information item, disconfirming
condition, and validation question also carries a non-null server-owned
semantic lineage ID:

```text
path_sem_<32 lowercase UUIDv7 hex>
consideration_sem_<32 lowercase UUIDv7 hex>
conflict_sem_<32 lowercase UUIDv7 hex>
missing_info_sem_<32 lowercase UUIDv7 hex>
disconfirming_sem_<32 lowercase UUIDv7 hex>
validation_question_sem_<32 lowercase UUIDv7 hex>
```

Semantic IDs represent continuity, not similarity scores:

- the first canonical object receives a new semantic ID;
- an edit or immutable revision of that same object retains it;
- a rerun may retain it only through a server-resolved, unambiguous predecessor
  mapping grounded in canonical branch-basis and decision-lineage IDs;
- a model/provider may propose content but never a public or semantic ID;
- a client may reference an existing object for a review command but never
  assign, replace, or merge a semantic ID;
- ambiguous matches receive a new semantic ID and record no match rather than
  guessing;
- semantic IDs do not imply equality, support, factual lineage, or likelihood;
- fuzzy/embedding similarity is diagnostic only and cannot assign identity.

Task 6 implements a `SemanticIdentityResolver` protocol and exact predecessor
rules. Task 7 may add a separately reviewed alignment workflow after these
rules have production evidence; it must not backfill guessed identities.

### Display identity

`P-01` through `P-08` are path-set-scoped display codes. They are not primary,
public, or semantic IDs. A complete set uses contiguous codes matching its
canonical tuple order. Reordering a display does not change semantic identity
and must not imply likelihood.

## Pure domain model

All models are Pydantic v2 frozen, strict, and `extra="forbid"`. Tuples are
used for immutable ordered collections. Provider candidate models contain no
ID fields; persisted models contain only server-issued identities.

### Required types

Create `backend/app/domain/identifiers.py`:

- `new_uuid7()` and strict `UUIDv7` validation;
- prefix-specific public/semantic ID value objects;
- canonical JSON and SHA-256 helpers with explicit schema version;
- no Flask, SQLAlchemy, filesystem, clock singleton, or provider import.

Create `backend/app/domain/possible_path.py` with at least:

- `PathArtifactStatus` — `INCOMPLETE | NEEDS_REVIEW | APPROVED | REJECTED |
  SUPERSEDED | FAILED`;
- `PathReviewDisposition` — `APPROVED | REJECTED | IRRELEVANT`;
- `BranchBasisRef` — canonical assertion reference restricted to reviewed
  `ASSUMPTION` or `UNCERTAINTY_STATE` roles;
- `StartingConditionRef`, `DecisionLensRef`, and `ScenarioRuleRef`;
- `PathStep` — ordered synthetic action plus bounded user-visible rationale;
- `Consideration` — statement and approved methodology category;
- `PathConflict`;
- `MissingInformation`;
- `DisconfirmingCondition`;
- `ValidationQuestion` — non-leading question and intended external-check type;
- `PossiblePath`;
- `PathSetArtifact`;
- `PathReviewItem`, `PathSetReview`, and `PathBriefGate`;
- provider-facing candidate types with no physical/public/semantic IDs;
- approved persisted types carrying the complete immutable `TruthBundle`.

Refactor `backend/app/domain/decision_workspace.py` so truth and the approved
versioned epistemic contract are shared without maintaining a second
`PossiblePath` or `PathStep` definition. Update
`backend/app/domain/__init__.py` to export only the canonical types.

### `PossiblePath` minimum content

Each path contains:

- physical identity for repository use;
- stable public and semantic identity;
- run and path-set identity;
- display code and title;
- reviewed branch-basis refs;
- reviewed starting-condition, decision-lens, and scenario-rule refs;
- branch trigger and bounded rationale;
- scenario frame with named uncertainty states;
- one or more contiguous ordered path steps;
- one or more considerations;
- zero or more explicit conflicts, but the cross-path validator must state
  whether no conflict was found;
- one or more missing-information items;
- one or more disconfirming conditions;
- one or more validation questions;
- content and distinctness hashes;
- origin and the exact immutable truth bundle.

There is no probability, likelihood, confidence, prevalence, public support,
sample size, rank, score, winner, recommendation, hidden reasoning, or
unbounded rationale field. Unknown fields fail validation.

### Artifact invariants

- A reviewable or approved set has exactly four to eight paths.
- Public IDs, semantic IDs, display codes, and content hashes are unique within
  their required scope.
- Display codes are exactly `P-01..P-N` in tuple order.
- Step sequences are exactly `1..N` in tuple order.
- Every branch has at least one assumption or uncertainty-state basis.
- All branches are materially distinct; a paraphrase-only set fails.
- Coverage records every required reviewed input as covered, intentionally
  excluded with a user-visible reason, or incomplete.
- Every path has a validation question and disconfirming condition.
- `bounded_rationale` is a concise explanation of reviewed inputs, not hidden
  chain-of-thought.
- `TruthBundle` values cannot be overridden by constructors, provider payloads,
  repository mapping, migration, or API serialization.
- Canonical serialization is deterministic and includes schema and validator
  versions. Hash fields are omitted from their own hash input.

## Canonical persistence model — only after the hard gate

Do not use the preselected revision ID
`b3f6d8a2c901_decision_workspace_paths.py` from the supporting plan.

### Actual-head migration procedure

Immediately before creating the migration:

1. run `alembic heads`; require exactly one head;
2. run `alembic current` against a disposable production-like PostgreSQL
   database upgraded through Task 5;
3. run `alembic check`; require no unowned metadata drift;
4. record the sole head and schema digest in the Task 6 report;
5. generate a new revision whose `down_revision` is that exact head;
6. inspect the generated operations by hand and remove unrelated drift;
7. run upgrade, downgrade to the recorded parent, and re-upgrade;
8. repeat against a restored production-like backup fixture.

At audit time, `alembic heads` returned `384c98f88d53`, but that value must not
be frozen into Task 6: the tenant and durable-run prerequisite migrations must
be ancestors first. Multiple heads, an unexpected parent, or unrelated
autogenerate changes stop the checkpoint.

### Tables

Extend the canonical metadata and add a migration for these normalized
records. Exact names may change only through architecture review; their
semantics may not be collapsed into JSON report blobs.

#### `path_sets`

Immutable whole-artifact revisions:

```text
id uuidv7 primary key
organization_id uuid not null
workspace_id uuid not null
public_id text not null
run_id uuid not null
run_stage_attempt_id uuid not null
revision integer not null
supersedes_path_set_id uuid null
status enum not null
path_count integer not null
artifact_schema_version text not null
artifact_sha256 char(64) not null
raw_artifact_ref_id uuid not null
coverage_validator_version text not null
coverage_status enum not null
distinctness_validator_version text not null
distinctness_status enum not null
truth fields with immutable check constraints
created_by uuid not null
created_at timestamptz not null
```

The database rejects an approved/reviewable set outside four to eight paths.
`raw_artifact_ref_id` points to an accepted private-object artifact. A partial
or rejected provider object remains quarantined and cannot be substituted.

#### `run_path_heads`

The only mutable path pointer:

```text
organization_id
workspace_id
run_id primary key
current_path_set_id
version bigint
updated_by
updated_at
```

It changes only through optimistic compare-and-swap in the same transaction as
the new immutable set, review invalidation event, audit event, and outbox row.

#### First-class object tables

Add normalized `possible_paths`, `path_steps`, `considerations`,
`path_conflicts`, `missing_information`, `disconfirming_conditions`, and
`validation_questions` tables. Every tenant-owned row carries both tenant
keys, a UUIDv7 physical ID, stable public/semantic ID where externally or
semantically addressable, parent foreign keys, origin, content hash, creation
metadata, and immutable artifact revision.

`possible_paths` additionally stores display code, title, branch trigger,
bounded rationale, scenario-frame version, distinctness hash, and canonical
ordinal. `path_steps` stores contiguous sequence. No table contains a
probability, likelihood, confidence, prevalence, support, score, rank,
recommendation, or hidden-reasoning column.

#### `path_set_reviews` and `path_review_dispositions`

Reviews are immutable and hash bound:

```text
path_set_reviews:
  id uuidv7 primary key
  organization_id
  workspace_id
  public_id
  run_id
  path_set_id
  path_set_sha256
  review_sha256
  overall_status
  reviewer_actor_id
  reviewer_membership_role
  created_at

path_review_dispositions:
  review_id
  possible_path_id
  disposition
  bounded_note
```

Reviewer identity and membership role come from the authorization context,
not the request. An edit, regeneration, or new set creates another immutable
path set, advances the head by compare-and-swap, and makes an earlier review
stale without changing it.

#### Canonical ledger and command infrastructure

Do not create a path-only imitation of the Epistemic Ledger, command receipt,
lease, outbox, or audit log. Use the prerequisite canonical tables.

New path objects receive assertions with their fixed role. Dependency edges
reference assertion IDs and the approved relation contract version. Structural
parent foreign keys do not automatically become epistemic support.

All foreign keys that cross tenant-owned tables include or verify organization
and workspace scope. RLS policies exist on every table. The application role
cannot bypass them. Snapshot/object/edge/review rows are append-only; retention
and legal-hold workflows own deletion.

## Repository write boundary

Create `backend/app/persistence/path_repository.py` only after the persistence
gate. Routes and provider adapters never call it directly.

Required protocol:

```python
class PathRepository(Protocol):
    def commit_generated_path_set(
        self,
        command: CommitGeneratedPathSet,
        *,
        scope: AuthorizedWorkspaceScope,
        stage_attempt_id: UUIDv7,
        lease_owner: str,
        fencing_token: int,
        idempotency_key: str,
        expected_run_version: int,
    ) -> StoredCommandReceipt: ...

    def append_review(
        self,
        command: ReviewPathSet,
        *,
        scope: AuthorizedWorkspaceScope,
        actor: AuthorizedActor,
        idempotency_key: str,
        expected_path_head_version: int,
    ) -> StoredCommandReceipt: ...
```

`CommitGeneratedPathSet` contains validated provider candidate content and
canonical reference IDs only. It contains no organization/workspace, physical
ID, public ID, semantic ID, endpoint role, run state, artifact hash, validator
result, lease, fence, review status, truth override, or final status supplied
by the provider.

### One-transaction write order

Inside one PostgreSQL transaction the repository must:

1. bind organization/workspace RLS context from `scope`;
2. load the canonical run and verify scope, expected version, immutable config,
   and allowed path-stage/run state;
3. load the stage attempt and current lease; verify owner, unexpired lease, and
   exact current fencing token;
4. claim the durable idempotency key and compare canonical request hash;
5. load every referenced assertion by ID and scope;
6. derive endpoint roles and origins from those stored assertions — never from
   the command;
7. reject missing, cross-scope, unreviewed, wrong-run-config, stale, or
   role-incompatible references;
8. assign UUIDv7 physical IDs, public IDs, and semantic IDs through the
   server-owned identity resolver;
9. validate the complete pure-domain artifact, four-to-eight rule, coverage,
   distinctness, truth language, safety, and the approved relation matrix;
10. verify the accepted object-storage artifact hash and release IDs;
11. insert the immutable path set, first-class objects, assertions, and allowed
    edges;
12. compare-and-swap the run path head;
13. append run/audit events, command receipt, and outbox record;
14. commit, then return the stored receipt.

No canonical path row, edge, pointer, event, review, or outbox record may be
visible if any step fails. A same-key/same-hash replay returns the original
stored receipt. A same-key/different-hash replay returns
`idempotency_key_conflict`. A stale fence records or retains only a quarantined
artifact and returns `path_stage_lease_lost`; it writes no canonical path fact.

### Edge safety

- The repository accepts endpoint IDs, not endpoint role claims.
- The repository resolves role/origin from canonical assertions and evaluates
  the exact versioned triple.
- Direct source-segment-to-path and source-segment-to-consideration edges fail
  with stable truth-boundary codes.
- A source may inform a reviewed starting condition; an approved branch may
  then depend on reviewed assumptions/uncertainty states. The API must not
  collapse that chain into source support for an outcome.
- `RELATED_BY_KEYWORD` is diagnostic only and can never satisfy a path
  dependency, review, coverage, or brief-lineage gate.
- Database-level tests attempt direct forbidden inserts under the application
  role and must fail even if application validation is bypassed.

## Application services and stage integration

Create `backend/app/application/path_service.py` with explicit injected
protocols for authorization, run reads, repository, semantic identity,
validators, object artifacts, and outbox dispatch. It contains no Flask,
global manager, filesystem scan, or Celery call.

Required operations:

```text
commit_stage_output(...)
get_path_set_by_run(...)
list_paths_by_run(...)
get_path_by_run_and_public_id(...)
review_current_path_set(...)
assert_brief_eligible(...)
```

The `GENERATING_PATHS` durable stage activity:

- receives only canonical stage-attempt and dispatch-event IDs;
- reloads the run config and exact releases;
- writes raw provider output to quarantine object storage;
- parses into the provider candidate schema;
- validates bounded output;
- calls the application service with current lease/fence context;
- never assigns IDs, roles, truth, approval, or final status itself;
- never calls a route or legacy `ReportManager`;
- checkpoints stop and heartbeat through the Task 5 stage contract;
- treats fewer than four valid distinct paths as explicit incomplete output;
- never pads or silently discards a ninth path to claim success.

Cross-path synthesis, coverage, disconfirmation, and question validators may
be separate stage consumers, but each canonical write uses the same fence and
idempotency contract. No consumer can mark the run COMPLETED.

## Immutable review and brief gate

`PathService.review_current_path_set` accepts only existing path public IDs,
dispositions, and bounded notes. Scope, actor, membership role, current
path-set ID/hash, review ID/hash, timestamps, and overall status are
server-owned.

Approval requires:

- the reviewed set is the exact current head and hash;
- it contains four to eight paths;
- every path has an explicit disposition and no path is rejected or irrelevant
  without a replacement that leaves four to eight approved paths;
- coverage and distinctness pass;
- all branch bases resolve to the immutable run config;
- all truth, schema, provenance, safety, and non-leading-question validators
  pass;
- reviewer membership has the canonical review capability;
- the run is exactly `VALIDATING_OUTPUT` and not stopped or failed.

`assert_brief_eligible` returns an immutable `PathBriefGate` containing the
run ID, path-set ID/hash, review ID/hash, validator bundle IDs, and truth bundle.
The brief activity receives those IDs and reloads them. It never accepts path
content from the client or legacy report prose.

Any changed content, dependency, order, origin, semantic mapping, validator
release, or path-set head makes the old gate stale. A stale gate cannot start
or finalize a brief. `GENERATING_BRIEF -> COMPLETED` additionally requires the
brief and manifest to store these exact references. Partial, stopped, failed,
rejected, stale, or unreviewed sets remain inspectable but cannot expose a
final brief.

## Run-based API contract

Create routes under the existing simulation blueprint, but address canonical
runs rather than legacy simulation containers:

```text
GET /api/simulation/runs/<run_id>/path-set
GET /api/simulation/runs/<run_id>/paths
GET /api/simulation/runs/<run_id>/paths/<path_id>
GET /api/simulation/runs/<run_id>/path-review
PUT /api/simulation/runs/<run_id>/path-review
```

Do not add handlers to `backend/app/api/simulation.py`. Register
`path_routes.py` through `backend/app/api/routes/__init__.py`. Routes follow
`authenticate -> parse -> authorize -> dispatch -> present`, call one
application operation, and never open SQL, object storage, report directories,
threads, subprocesses, or Celery directly.

All routes remain hidden with 404 while
`DECISION_WORKSPACE_PATHS_V1=false`, the default. Public review writes also
remain unavailable until canonical actor authorization passes the hard gate.

### Read response

The list response includes at least:

```json
{
  "success": true,
  "data": {
    "run_id": "run_<server-id>",
    "path_set_id": "path_set_<server-id>",
    "revision": 1,
    "artifact_status": "NEEDS_REVIEW",
    "artifact_sha256": "<sha256>",
    "coverage_status": "PASS",
    "distinctness_status": "PASS",
    "paths": [],
    "truth": {
      "output_origin": "synthetic",
      "human_respondent_count": 0,
      "is_forecast": false,
      "is_public_opinion_measure": false,
      "is_causal_evidence": false,
      "source_role": "starting_conditions_only",
      "human_validation_scope": "external_to_synthetic_run"
    }
  }
}
```

Each path exposes its public and semantic IDs, display code, structured
content, explicit origin, reviewed dependency summaries, and truth. It never
exposes physical IDs, lease/fence data, hidden reasoning, raw provider output,
source text, internal error details, probability, support, rank, score, or a
winner. List and later spatial views consume this same canonical response.

Artifact status distinguishes `UNAVAILABLE`, `PARTIAL`, `NEEDS_REVIEW`,
`APPROVED`, `STALE`, and `FAILED`. Unavailable is not an empty successful path
set. Partial output is never serialized as approved or complete.

### Review write

`PUT path-review` requires:

- `Idempotency-Key` matching the canonical durable-command pattern;
- an `If-Match` value bound to the current path-set ID, version, and hash;
- a strict, extra-forbidden body containing only path public IDs,
  dispositions, and bounded notes.

It returns the stored receipt and ETag. Replaying the same canonical body and
key returns the same response. Stale `If-Match` returns
`path_set_version_conflict`. The request cannot set actor, role, organization,
workspace, run state, path-set hash, review status, truth, semantic identity,
brief eligibility, or final status.

### Stable errors

At minimum:

```text
run_not_found                       404
path_not_found                      404
canonical_paths_unavailable         409
path_set_incomplete                 409
path_set_review_required            409
path_set_review_stale               409
path_set_version_conflict           409
path_review_forbidden               403
idempotency_key_conflict            409
path_stage_lease_lost               409
path_dependency_not_found           422
path_dependency_role_invalid        422
path_dependency_forbidden           422
source_to_path_forbidden            422
path_count_invalid                  422
path_artifact_invalid               422
paths_feature_disabled              404
path_repository_unavailable         503
```

Cross-workspace resources return the same 404 as absent. Unexpected failures
return bounded codes without exception text, traceback, SQL, object keys,
source text, prompts, model output, or path prose.

## Legacy behavior and cutover

- Existing filesystem simulations, report markdown, related-run records, and
  the legacy `/compare` endpoint remain readable through their existing
  interfaces during TRANSITION.
- They are labeled `LEGACY / CANONICAL PATHS UNAVAILABLE` where the new
  workspace links to them.
- Do not parse headings, paragraphs, posts, metrics, or generated actions into
  `PossiblePath` rows. Do not fabricate branch bases, semantic IDs, review,
  coverage, provenance, or completion proof.
- Do not create `/api/simulation/<simulation_id>/paths` as a canonical alias.
  Canonical reads are run-based. A legacy simulation can produce canonical
  paths only by creating a new reviewed canonical run with a new run ID.
- No path object is dual-written to PostgreSQL and legacy report JSON/markdown.
  Each run has one immutable orchestration mode.
- Disabling the flag stops new path generation/review but preserves scoped
  reads and stop/recovery for already acknowledged canonical runs.
- The workspace manifest reports paths as `UNAVAILABLE` for legacy-only runs,
  `PARTIAL` for truthfully partial canonical artifacts, and `AVAILABLE` only
  when a canonical path set is readable. It never chooses one legacy
  simulation as a canonical run.
- Existing `/api/simulation/compare` remains a legacy diagnostic. It is not
  linked or relabeled as path comparison. Task 7 creates a separate exact-two
  canonical contract later.

## Staged implementation checkpoints

Execute in order. A blocked checkpoint does not authorize skipping ahead.

### Checkpoint 0 — Confirm authority packet approval

**Status after acceptance:** PROPOSED until named architecture, methodology,
product-truth, and docs owners approve the relation matrix and path-review
interpretation.

Normative work completed by `ce132a5`:

- versioned the exact `epistemic-ledger/v2` triple matrix;
- resolved disconfirming, missing-information, and brief lineage;
- documented independent path review while run state is
  `VALIDATING_OUTPUT`;
- revised the proposed design spec to exactly two later comparison inputs; and
- added structural validator locks for those contracts.

Remaining gate:

- record named architecture, methodology, product-truth, and docs approvals of
  `ce132a5`;
- rerun `python tools/validate_docs.py` with zero warnings/errors on the exact
  implementation head; and
- update the TRANSITION domain enum/allowlist only after approval, through the
  Checkpoint 1 TDD sequence.

No code enum or migration changes before approval.

### Checkpoint 1 — Build the richer pure domain

**Status after acceptance:** TRANSITION — DOMAIN ONLY.

**Files:**

- Create `backend/app/domain/identifiers.py`.
- Create `backend/app/domain/possible_path.py`.
- Modify `backend/app/domain/decision_workspace.py`.
- Modify `backend/app/domain/__init__.py`.
- Create `backend/tests/domain/test_identifiers.py`.
- Create `backend/tests/domain/test_possible_path.py`.
- Modify `backend/tests/domain/test_decision_workspace.py` only for the
  approved provenance-contract version.

TDD sequence:

1. Prove UUIDv4, malformed IDs, provider IDs, and client-assigned IDs fail.
2. Prove generated physical/public/semantic IDs have UUIDv7 version/variant
   bits and distinct identity purposes.
3. Prove three paths are explicit incomplete, four and eight are reviewable,
   and nine fail; prove no padding.
4. Prove duplicate IDs/codes/hashes and noncontiguous steps fail.
5. Prove every path requires branch bases, steps, consideration, missing
   information, disconfirming condition, and validation question.
6. Prove probability/rank/support/CoT and all unknown fields fail closed.
7. Prove canonical serialization and hashes are byte stable.
8. Prove same-object revision retains public/semantic IDs and new object gets
   new IDs.
9. Prove ambiguous predecessor mapping creates a new semantic ID.
10. Prove every approved provenance triple passes and the Cartesian complement
    fails, including direct source-to-path/consideration.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_identifiers.py tests/domain/test_possible_path.py tests/domain/test_decision_workspace.py -q
```

Stop here if the hard persistence prerequisite gate is not complete.

### Checkpoint 2 — Prove persistence prerequisites and migration parent

**Status after acceptance:** TRANSITION — READY FOR PATH MIGRATION.

This checkpoint changes no path production code. Record evidence that tenant
authorization, schema drift reconciliation, canonical ledger, durable run,
stage lease/fence, object storage, release identity, and reviewed input gates
all pass. Run the actual-head procedure. If any proof fails, stop.

### Checkpoint 3 — Add canonical schema and repository

**Status after acceptance:** TRANSITION behind a disabled feature flag.

**Files:**

- Modify `backend/app/db/schema.py` only after upstream metadata is canonical.
- Create
  `backend/migrations/versions/<actual_revision>_decision_workspace_paths_v1.py`.
- Create `backend/app/persistence/__init__.py` if the upstream package does not
  exist.
- Create `backend/app/persistence/path_repository.py`.
- Create `backend/tests/persistence/test_path_migrations.py`.
- Create `backend/tests/persistence/test_path_repository.py`.
- Create `backend/tests/persistence/test_path_rls.py`.

TDD sequence:

1. Migration upgrade/downgrade/re-upgrade on production-like PostgreSQL.
2. Assert every physical ID is UUIDv7 and every tenant row has both scope
   columns.
3. Assert all composite tenant FKs and RLS policies.
4. Assert snapshot/object/edge/review immutability under the application role.
5. Commit four and eight paths; reject invalid complete counts.
6. Roll back the whole transaction on one invalid child or edge.
7. Attempt direct source-to-path and every forbidden triple in SQL; fail.
8. Race two writers with one expected head version; exactly one advances.
9. Replay same idempotency key/payload; return one stored receipt and one
   artifact. Reuse with another payload; conflict.
10. Replace lease and submit from the stale fence; no canonical row/event/head
    advances.
11. Prove cross-workspace read/write under application and database roles is
    indistinguishable from absent.

### Checkpoint 4 — Integrate application service and durable path stage

**Status after acceptance:** PARTIAL until worker-kill and provider-failure
evidence passes.

**Files:**

- Create `backend/app/application/path_service.py`.
- Add the path stage activity through the Task 5 orchestration registry rather
  than inventing another worker framework.
- Create `backend/tests/application/test_path_service.py`.
- Create `backend/tests/orchestration/test_path_stage_activity.py`.

TDD sequence:

1. Candidate payload cannot assign identities, roles, truth, hashes, review, or
   final state.
2. Canonical role resolution rejects missing/wrong/cross-scope dependencies.
3. Provider output with three distinct paths records incomplete; nine fails.
4. Duplicate provider delivery creates one accepted set and receipt.
5. Kill the worker after raw artifact write, validation, each relational batch,
   head CAS, event append, and outbox publish; recovery does not duplicate.
6. Lose lease during validation/write; late output is quarantined only.
7. Stop during generation; partial accepted artifacts remain inspectable but no
   review approval or brief gate exists.
8. Retry creates a new stage attempt and does not mutate the earlier artifact.

### Checkpoint 5 — Add immutable review and run-based APIs

**Status after acceptance:** TRANSITION behind
`DECISION_WORKSPACE_PATHS_V1=false`.

**Files:**

- Modify `backend/app/config.py` for the default-off flag.
- Create `backend/app/api/path_schemas.py`.
- Create `backend/app/api/routes/path_routes.py`.
- Modify `backend/app/api/routes/__init__.py`.
- Create `backend/tests/test_path_api.py`.
- Create `backend/tests/test_path_review_api.py`.
- Create `backend/tests/test_path_brief_gate.py`.

TDD sequence:

1. Flag hides all routes by default.
2. Reads address canonical run IDs and never expose physical IDs.
3. Partial/unavailable/failed/needs-review/approved states serialize truthfully.
4. Cross-workspace reads and writes return indistinguishable 404.
5. Review requires authorization, idempotency, and exact hash/version ETag.
6. Identical review replay returns the stored response; conflicting replay
   fails.
7. Review request cannot override scope, actor, role, hash, status, semantic
   IDs, truth, or brief eligibility.
8. Four-to-eight exact current paths may approve; incomplete, rejected, stale,
   or failed sets may not.
9. Any new immutable revision stales the old review and relocks the brief.
10. Brief gate passes only exact approved set/review hashes in
    `VALIDATING_OUTPUT`; stop/failure/partial cannot pass.
11. Routes never call SQL, object storage, filesystem reports, Celery, threads,
    or subprocesses.
12. No canonical simulation-ID path alias or comparison route is registered.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_path_api.py tests/test_path_review_api.py tests/test_path_brief_gate.py -q
```

### Checkpoint 6 — Cut over new runs and preserve legacy reads

**Status after acceptance:** PARTIAL / REVISION REQUIRED until all production
gates pass.

**Files depend on the Task 5 interfaces that actually land; do not guess them
in advance.** At minimum:

- wire the canonical `GENERATING_PATHS`, synthesis, validation, and brief
  activities to `PathService`;
- make the run completion guard require exact path-set/review/brief manifest
  references;
- update workspace availability from canonical run/path reads;
- add a read-only legacy availability adapter that never fabricates paths;
- add `backend/tests/test_legacy_path_cutover.py` and
  `backend/tests/test_run_path_completion_gate.py`.

Cutover tests prove one orchestration mode per run, no dual writes, no legacy
prose parsing, no force-restart identity reuse, preserved canonical reads when
the flag is disabled, and no final brief from incomplete legacy or canonical
runs.

## Strict red-green-refactor discipline

For every invariant in every checkpoint:

1. write the smallest failing test first;
2. run it and record the expected RED failure in the Task 6 report;
3. implement the minimum production behavior;
4. rerun and record GREEN;
5. run the checkpoint regression set;
6. run independent specification and code-quality reviews;
7. commit only checkpoint-owned files;
8. keep the feature flag off until the next checkpoint is verified.

Do not write an ORM model before the pure contract passes. Do not generate a
migration before the hard prerequisite gate and single actual head pass. Do not
write an edge before canonical role resolution exists. Do not add routes before
the repository transaction and RLS tests pass. Do not start Task 7 before the
semantic identity completion gate passes.

## Production completion gates

Task 6 is not complete merely because a list endpoint returns four objects.
All of the following evidence is required.

### Identity and authority

- the provenance relation matrix and path-review/run-state reconciliation are
  approved in the normative docs;
- all physical IDs are UUIDv7;
- all external objects have stable server-issued public IDs;
- every path, consideration, conflict, missing-information item,
  disconfirming condition, and validation question has a non-null server-owned
  semantic ID;
- revision tests preserve public/semantic identity correctly;
- predecessor tests reuse identity only for exact unambiguous canonical
  lineage and create a new ID otherwise;
- providers and clients cannot set or merge identities.

### Method and truth

- all complete sets contain four to eight materially distinct paths;
- incomplete sets remain explicitly incomplete and are never padded;
- coverage and duplicate-path validators pass frozen and adversarial fixtures;
- every branch basis resolves to reviewed run-config inputs;
- every path has missing information, disconfirmation, and a non-leading
  validation question;
- no field, copy, ordering, color contract, or API response represents
  probability, prevalence, confidence, support, ranking, or a winner;
- every artifact and response preserves the immutable truth bundle;
- no source segment directly supports a path or consideration;
- no hidden chain-of-thought is stored.

### Persistence and reliability

- PostgreSQL is canonical; raw artifacts are in private object storage;
- migration actual-head, up/down/up, backup restore, and schema-drift evidence
  pass;
- every table and query is organization/workspace scoped with tested RLS;
- immutable snapshots/reviews/edges reject update and deletion under the
  application role;
- duplicate command/broker delivery does not duplicate paths, edges, events,
  receipts, outbox messages, or cost records;
- stale-fence output never becomes canonical;
- worker-kill recovery passes at every write boundary;
- stopped/failed runs expose only truthful partial artifacts and no final
  brief;
- completed runs reject path/review mutation; a rerun has a new run ID.

### API, legacy, and release

- the default-off feature flag and rollback behavior pass;
- canonical path APIs are run based, typed, bounded, and do not leak physical
  IDs or internal details;
- review and brief eligibility bind to exact immutable hashes;
- legacy simulations/reports remain readable but are never upgraded by
  inference;
- the existing legacy compare endpoint is not relabeled as semantic path
  comparison;
- no Task 7 comparison route exists in the Task 6 change set;
- focused suites, full backend suite, touched-file lint, docs validator, and
  `npm run verify` pass from a clean checkout;
- release notes, migration rollback, RLS operations, worker/lease/outbox
  alerts, and incident rollback are verified.

### Honest status claims

- Checkpoint 0 only: **PROPOSED / REVISION REQUIRED**.
- Checkpoint 1 only: **TRANSITION — DOMAIN ONLY**.
- Schema/repository without tenant authorization, durable runs, RLS, object
  storage, or fencing: **BLOCKED**, not partial production persistence.
- Routes behind the disabled flag: **TRANSITION — API CONTRACT ONLY**.
- Worker integration without kill/recovery and stale-fence evidence:
  **PARTIAL**.
- Legacy cutover without all gates above: **PARTIAL / REVISION REQUIRED**.
- Only all gates together permit **CURRENT** for first-class canonical paths.

## Task 7 admission gate

Two-run comparison remains a later task. It may start only when:

- Task 6 is at least production-ready for canonical path reads;
- semantic IDs are non-null and immutable for every comparison object;
- exact predecessor and ambiguity tests pass across related runs;
- both runs share the same canonical decision lineage and are COMPLETED;
- each run references an approved path set and exact review hash;
- the proposed design spec has been revised to exactly two inputs;
- the Task 7 request schema rejects any count other than two;
- no winner, score, rank, recommendation, probability, or confidence output is
  planned.

Task 6 must not create placeholder comparison tables, APIs, UI, or fake
semantic matches to make this gate appear complete.

## Rollback

Rollback disables new canonical path generation and review, but does not
delete or rewrite acknowledged path sets, reviews, events, semantic lineage,
or raw artifacts. Durable workers continue stop/recovery for acknowledged
work. Scoped canonical reads remain available. Legacy read-only history remains
available. Rollback never enables prose-to-path inference, dual writes, stale
fences, unreviewed brief generation, force restart, three-run comparison, or
client-assigned identity.

## Authority resolutions and dependency register

| Item | Binding resolution in this brief | Required action before affected checkpoint |
|---|---|---|
| Task 2 TRANSITION provenance enum differs from the normative ledger | **RESOLVED NORMATIVELY by `ce132a5`:** exact `epistemic-ledger/v2`, including disconfirmation, missing-information, and brief lineage; no aliases | Record named approval, then update the pure domain and exhaustive complement tests before any persisted edge |
| Methodology requires path review before brief; run machine has no post-path review state | **RESOLVED NORMATIVELY by `ce132a5`:** independent immutable path review while the run remains `VALIDATING_OUTPUT` | Record named architecture/methodology approval and implement the exact-hash gate before enabling brief generation |
| Proposed design previously allowed an optional third comparison | **RESOLVED NORMATIVELY by `ce132a5`:** exactly two only, later | Record named design/product approval; Task 7 remains blocked on semantic-identity evidence and its own exact-two schema/tests |
| Task 3 workspace identity lacks organization identity and is filesystem TRANSITION | Cannot authorize path rows | Land server-owned PostgreSQL organization/workspace membership and RLS |
| ORM metadata and root migration disagree | Task 6 may not absorb unrelated drift | Reconcile schema, then use sole actual head after tenant/run migrations |
| Durable run/stage/lease/fence infrastructure is absent on audited head | Domain-only work may proceed; persistence is blocked | Complete Task 5 prerequisites and worker recovery evidence |
| Canonical reviewed assumptions/uncertainties/ledger are absent | No role-resolved path dependency can be written | Land secure review aggregates and canonical assertions |
| Legacy report prose mentions possible paths but has no typed objects | Read-only legacy label; never parse/backfill | Canonical rerun required for canonical paths |
| Semantic lineage across ambiguous regenerated content cannot be guessed | New semantic ID on ambiguity | Task 7 may add reviewed alignment only after Task 6 identity evidence |
| User-authored path edits, advanced changed conditions, external evidence, and owner conclusions exceed this slice | Deferred; do not smuggle them into path generation | Separate later specifications and release gates |

The first three authority conflicts are resolved in the normative packet, but
their named approvals and implementation work remain open. None of the
remaining dependencies or resolved contracts permits a production-complete
claim.

## Verification commands

Run after each applicable checkpoint and record exact results:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_identifiers.py tests/domain/test_possible_path.py tests/domain/test_decision_workspace.py -q
.\.venv\Scripts\pytest tests/persistence/test_path_migrations.py tests/persistence/test_path_repository.py tests/persistence/test_path_rls.py -q
.\.venv\Scripts\pytest tests/application/test_path_service.py tests/orchestration/test_path_stage_activity.py -q
.\.venv\Scripts\pytest tests/test_path_api.py tests/test_path_review_api.py tests/test_path_brief_gate.py tests/test_legacy_path_cutover.py tests/test_run_path_completion_gate.py -q
.\.venv\Scripts\pytest

cd ..
python tools/validate_docs.py
npm run verify
```

Migration rehearsal runs separately against disposable production-like
PostgreSQL and uses the parent revision recorded at Checkpoint 2:

```powershell
cd backend
.\.venv\Scripts\alembic heads
.\.venv\Scripts\alembic current
.\.venv\Scripts\alembic check
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\alembic downgrade <recorded-parent-head>
.\.venv\Scripts\alembic upgrade head
```

## Implementation report

During execution, write `.superpowers/sdd/task-6-report.md`. For every
checkpoint record:

- status using PROPOSED / REVISION REQUIRED and the repository state legend;
- prerequisite evidence and named unresolved owner;
- files changed and exact commit;
- every RED command/failure and GREEN command/result;
- actual Alembic parent/head and schema digest;
- migration, RLS, fencing, idempotency, worker-kill, and rollback evidence;
- feature-flag state;
- exact path/semantic identity invariants proven;
- independent spec and code-quality review verdicts;
- confirmation that no Task 7 comparison or UI implementation was included;
- confirmation that no unrelated dirty work was staged.

Do not mark Task 6 complete because a provider returned several branches, a
JSON file contains `paths`, a report has a “Possible Paths” heading, or a
client can draw lanes. Completion requires canonical identity, typed lineage,
durable scoped persistence, immutable review, and the exact-hash brief gate.
