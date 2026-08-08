# Task 5 revised brief — Durable run control plane and cutover

Read this first. It is the complete implementation contract for Task 5.

## Status and authority

**Task status: PARTIAL / REVISION REQUIRED.** The short Task 5 entry in
`docs/superpowers/plans/2026-08-08-decision-workspace-foundation.md` is not an
implementation-ready plan and must not be treated as approval to add a second
best-effort lifecycle beside the existing one.

Authority for this task, in descending order:

1. law, contractual obligation, and approved legal advice;
2. `docs/product/PRODUCT_TRUTH_CONTRACT.md`;
3. `docs/product/USE_POLICY.md`;
4. `docs/security/*`;
5. `docs/privacy/*`;
6. `docs/product/METHODOLOGY.md`;
7. release acceptance and accessibility requirements, especially
   `docs/release/ACCEPTANCE.md`;
8. accepted ADRs, especially
   `docs/architecture/adr/ADR-0003-durable-run-orchestration.md`,
   `ADR-0009-multi-tenant-isolation.md`, and
   `ADR-0012-canonical-transactional-and-object-persistence.md`;
9. architecture and AI implementation guides, especially
   `docs/architecture/state-machines.md`,
   `docs/architecture/data-model.md`, and the applicable AI implementation
   guides;
10. `docs/design/*` and the content system;
11. execution plans, including
    `docs/exec-plans/04-durable-orchestration-and-path-engine.md` and this
    brief;
12. `AGENTS.md`;
13. code comments; and
14. generated documentation.

The combined normative authority packet is locked at commit `ce132a5`. Its
version-`1.2.0` data model, ADR-0009, ADR-0012, and state-machine corrections
resolve the prior contract conflicts and supersede stale identifier, tenancy,
migration-parent, and run-guard language in untracked planning briefs. Named
Architecture, Security, Privacy, Persistence, and Release approval and all
application evidence remain outstanding; the locked contract is not an
implementation-complete claim. In particular, no implementation may copy a
literal migration revision or `down_revision` from the earlier Task 3a brief.

Use the repository legend exactly:

- **CURRENT** — implemented and verified in the repository;
- **PARTIAL** — implemented but materially deficient;
- **TARGET** — approved production design not yet reached;
- **TRANSITION** — reversible work that moves CURRENT/PARTIAL toward TARGET.

The older lifecycle in `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` section 66 is
supporting synthesis, not the run-state authority. Its states
`SOURCE_PROCESSING`, `SOURCE_REVIEW_REQUIRED`, `RUNNING`, `STAGE_FAILED`, and
`QUALITY_REVIEW_REQUIRED` must not be introduced as aliases for the normative
states below.

## Audit conclusion

The CURRENT execution path is PARTIAL:

- `SimulationStatus` in `backend/app/services/simulation_manager.py:47`,
  `RunnerStatus` in `backend/app/services/simulation_runner.py:75`, and
  `TaskStatus` in `backend/app/models/task.py:61` each describe a different,
  overlapping lifecycle.
- simulation state is written to JSON directly
  (`backend/app/services/simulation_manager.py:207` and
  `backend/app/services/simulation_runner.py:404-409`); task state is cached in
  process memory and Redis with a 24-hour TTL
  (`backend/app/models/task.py:36`, `backend/app/models/task.py:182`, and
  `backend/app/models/task.py:264`). None is canonical production state.
- `SimulationRunner` owns run state, processes, and monitor threads in class
  dictionaries (`backend/app/services/simulation_runner.py:271-274`), so a
  different worker cannot safely recover ownership.
- the Celery task polls those process-local maps every 0.5 seconds
  (`backend/app/tasks/simulation_tasks.py:138-185`). Celery is currently both
  delivery and inferred truth, without late acknowledgement, worker-lost
  rejection, a lease, fencing, or a stalled-stage reaper.
- force start can stop a run, delete its journal files, reset the same
  simulation ID, and mark it running again
  (`backend/app/api/routes/execution_routes.py:95-269`). This destroys history
  and violates immutable rerun identity.
- `/api/jobs/<task_id>` calls a nonexistent `TaskManager.get_instance()`
  (`backend/app/api/jobs.py:28`).
- existing tests explicitly permit terminal idempotency-key reuse and
  `COMPLETED -> FAILED`
  (`backend/tests/test_task_manager_durability.py:286-291` and
  `backend/tests/test_task_manager_durability.py:478-490`). Both are invalid
  canonical command semantics.
- the report generation route loads a simulation but does not require a
  canonical `COMPLETED` run (`backend/app/api/report.py:61-114`), so a stopped
  or otherwise incomplete execution can enter report generation.
- the simulation WebSocket polls process-local snapshots and has no event
  cursor (`backend/app/api/ws.py:203-241`). A reconnect can miss history.
- `backend/app/db/schema.py` describes models and `version` columns that the
  only migration, `backend/migrations/versions/384c98f88d53_initial_schema.py`,
  does not create. There is no durable run attempt, stage attempt, event,
  command receipt, lease, or outbox schema.

This task replaces those semantics for new runs. It does not relabel legacy
files as durable history.

## Non-negotiable outcome

Build one server-owned durable run control plane with:

- the exact 20-state normative run lifecycle;
- independent immutable stage attempts;
- PostgreSQL-authoritative, organization/workspace-scoped run configurations,
  runs, stages, events, command receipts, leases, audit records, outbox
  records, and artifact references;
- optimistic concurrency and durable idempotency in the same transaction as
  every state change;
- Celery used only to deliver identifiers to workers;
- monotonic fencing tokens, heartbeats, stalled-lease recovery, and stale
  output quarantine;
- durable cooperative stop, retry-as-new-attempt, and rerun-as-new-run;
- cursor-based event reads and reconnect;
- a feature-flagged cutover that never dual-writes one run to two lifecycle
  authorities.

Do not add routes to `backend/app/api/simulation.py`. Do not start threads or
subprocesses from a route. Do not accept client-supplied organization/workspace scope,
canonical state, event sequence, lease owner, fencing token, artifact hash, or
final status.

## Authority packet resolutions and remaining hard gates

### `REVIEWING_CONDITIONS` omission

The audit baseline omitted two outgoing arrows from
`REVIEWING_CONDITIONS`. The same normative document said
`any active -> STOP_REQUESTED`, and every adjacent active stage could fail
retryably. The only coherent resolution is both transitions:

```text
REVIEWING_CONDITIONS -> STOP_REQUESTED
REVIEWING_CONDITIONS -> FAILED_RETRYABLE
```

Authority packet `ce132a5` resolves the omission in the normative document at
`docs/architecture/state-machines.md:60` and
`docs/architecture/state-machines.md:71`. Checkpoint 1 acceptance still
requires the docs steward to verify those exact arrows on the integration
branch, record the outstanding named approvals, and pass
`python tools/validate_docs.py`. If either arrow is absent, implementation
stops until the normative document is restored. The former omission never
permits an implementation to skip either transition.

### Five-value design union

The audit baseline's illustrative `RunAttempt.state` had only
`queued | running | stopped | failed | complete`; that was not a domain state
machine. Authority packet `ce132a5` retains the canonical correction at
`docs/superpowers/specs/2026-08-08-decision-chamber-experience-design.md:634-697`:
the exact `RunState`, a separate `RunPresentationSummary`, and the exhaustive
mapping below. That design spec remains `Proposed / Revision Required`, so
Checkpoint 5 must verify it is present on the integration branch and has the
required named approval before client cutover. No API, store, route guard,
action rule, report gate, or artifact finalizer may branch on the summary.

Use this exhaustive display-only mapping:

| Presentation summary | Canonical run states |
|---|---|
| `preflight` | `DRAFT`, `NEEDS_REVIEW`, `BLOCKED`, `READY` |
| `queued` | `QUEUED` |
| `active` | `PREPARING`, `EXTRACTING`, `REVIEWING_CONDITIONS`, `GENERATING_PROFILES`, `CONSTRUCTING_SCENARIOS`, `GENERATING_PATHS`, `SYNTHESIZING`, `VALIDATING_OUTPUT`, `GENERATING_BRIEF`, `STOP_REQUESTED` |
| `attention` | `FAILED_RETRYABLE` |
| `terminal` | `STOPPED`, `FAILED_TERMINAL`, `COMPLETED`, `ARCHIVED` |

The UI must still render exact plain-language copy and exact allowed actions
from the canonical state. `terminal` must never be rendered as “complete”
without confirming `COMPLETED`, or an `ARCHIVED` run whose last pre-archive
state was `COMPLETED`, from the event record.

### Tenant identity prerequisite

ADR-0009 and `docs/architecture/data-model.md` require both immutable physical
`organization_id` and `workspace_id` on every workspace-owned aggregate and
query. The TRANSITION workspace manifest from Task 3 supplies only a preserved
public alias for a one-project product projection. It is not organization,
membership, authentication, authorization, or RLS evidence. CURRENT
authentication is one application-wide bearer token with no object-level
membership check.

Task 5 therefore depends on the complete Task 3a tenant foundation. Before
Checkpoint 2 may create a migration, all of the following must be implemented,
reviewed, migration-tested, deployed behind its own controls, and recorded in
the Task 5 report:

- PostgreSQL UUIDv7 `core.organizations`, `core.users`, `core.workspaces`, and
  `core.projects`, each with a separate immutable prefixed alias containing an
  independently generated UUIDv7 and the normative
  `organization -> workspace -> project` ownership relation;
- active `core.organization_memberships` and `core.workspace_memberships`, the
  closed role-to-capability policy, revocation, and an immutable server-derived
  `ActorContext` for exactly one organization/workspace and optional project;
- exact-subject OIDC authentication through `(issuer, subject)`, with issuer,
  audience, algorithm, signature, time, and JWKS validation; claims never grant
  organization, workspace, project, role, or capability and failed OIDC never
  falls back to `APP_TOKEN` in production;
- bounded bootstrap resolvers for identity and project scope, explicit
  application authorization, transaction-local actor/organization/workspace
  context, `FORCE ROW LEVEL SECURITY`, mirrored `USING`/`WITH CHECK` policies,
  connection-pool context reset, and separate owner/migrator/application/read
  roles with the application role unable to own tables or bypass RLS;
- operator-approved adoption of every legacy project/workspace alias with
  reconciliation evidence; no organization, user, membership, or capability
  is inferred from a manifest, path, header, token custom claim, or client body;
- a narrowly credentialed service-principal/worker `ActorContext` extension for
  Task 5. An HTTP caller cannot construct `actor_type=SERVICE`, and a worker
  resolves its allowed tenant scope from the committed run rather than a task
  payload.

Domain-only work may land behind the disabled durable-runs flag before this
foundation. Persistence, production run creation, and production start remain
blocked until the foundation is canonical and its actual Alembic head is
known. This is an upstream dependency, not permission to weaken the schema,
reuse a manifest alias as physical scope, or claim the application is already
multi-tenant.

## Canonical run state machine

### States

`RunState` contains exactly these 20 values, with these uppercase serialized
forms:

```text
DRAFT
NEEDS_REVIEW
BLOCKED
READY
QUEUED
PREPARING
EXTRACTING
REVIEWING_CONDITIONS
GENERATING_PROFILES
CONSTRUCTING_SCENARIOS
GENERATING_PATHS
SYNTHESIZING
VALIDATING_OUTPUT
GENERATING_BRIEF
STOP_REQUESTED
STOPPED
FAILED_RETRYABLE
FAILED_TERMINAL
COMPLETED
ARCHIVED
```

The active execution states are exactly:

```text
QUEUED
PREPARING
EXTRACTING
REVIEWING_CONDITIONS
GENERATING_PROFILES
CONSTRUCTING_SCENARIOS
GENERATING_PATHS
SYNTHESIZING
VALIDATING_OUTPUT
GENERATING_BRIEF
```

`STOP_REQUESTED` is durable but is not a state from which new work may be
scheduled. `COMPLETED`, `STOPPED`, and `FAILED_TERMINAL` are terminal outcome
states. `ARCHIVED` is terminal storage state.

### Exact allowed transitions

| From | To | Domain command / worker event | Required guard |
|---|---|---|---|
| `DRAFT` | `NEEDS_REVIEW` | `SUBMIT_FOR_REVIEW` | decision and config references exist |
| `NEEDS_REVIEW` | `BLOCKED` | `BLOCK_REVIEW` | named deficiency and authorized reviewer |
| `BLOCKED` | `NEEDS_REVIEW` | `RESUBMIT_REVIEW` | deficiency revision recorded |
| `NEEDS_REVIEW` | `READY` | `APPROVE_CONFIGURATION` | decision valid; policy allowed; secure sources ready; assumptions and decision lenses approved; immutable truth fields present; exact release identifiers present |
| `READY` | `QUEUED` | `START_RUN` | config sealed; config hash matches; durable idempotency receipt accepted |
| `QUEUED` | `PREPARING` | `ACCEPT_WORKFLOW` | a new `PREPARING` attempt for this start or run-level retry is durably created and leased |
| `PREPARING` | `EXTRACTING` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `EXTRACTING` | `REVIEWING_CONDITIONS` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `REVIEWING_CONDITIONS` | `GENERATING_PROFILES` | `SUCCEED_STAGE` | reviewed-condition artifact accepted |
| `GENERATING_PROFILES` | `CONSTRUCTING_SCENARIOS` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `CONSTRUCTING_SCENARIOS` | `GENERATING_PATHS` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `GENERATING_PATHS` | `SYNTHESIZING` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `SYNTHESIZING` | `VALIDATING_OUTPUT` | `SUCCEED_STAGE` | accepted immutable stage output exists |
| `VALIDATING_OUTPUT` | `GENERATING_BRIEF` | `SUCCEED_STAGE` | every critical truth, schema, provenance, coverage, and safety validator passes under the recorded validator bundle; the exact current immutable path-set ID/hash has an immutable `APPROVED` path review; the brief gate binds that path-set ID/hash, review ID/hash, and validator bundle |
| `GENERATING_BRIEF` | `COMPLETED` | `SUCCEED_STAGE` | brief and manifest artifact refs accepted; export eligibility calculated |
| every active execution state | `STOP_REQUESTED` | `REQUEST_STOP` | authorized stop actor; no terminal state |
| `STOP_REQUESTED` | `STOPPED` | `CONFIRM_STOPPED` | no accepted active lease/work remains; in-flight output was accepted before stop or quarantined |
| every stage state from `PREPARING` through `GENERATING_BRIEF` | `FAILED_RETRYABLE` | `RECORD_RETRYABLE_FAILURE` | stable retryable code; failed attempt closed; no final brief |
| `FAILED_RETRYABLE` | `QUEUED` | `ACCEPT_RETRY` | run-level retry budget remains; restart from a new `PREPARING` attempt; release set unchanged or an authorized replacement is recorded |
| `FAILED_RETRYABLE` | `FAILED_TERMINAL` | `EXHAUST_RETRY_BUDGET` | budget exhausted or authorized no-retry decision recorded |
| `COMPLETED` | `ARCHIVED` | `ARCHIVE_RUN` | retention and legal-hold rules allow |
| `STOPPED` | `ARCHIVED` | `ARCHIVE_RUN` | retention and legal-hold rules allow |
| `FAILED_TERMINAL` | `ARCHIVED` | `ARCHIVE_RUN` | retention and legal-hold rules allow |

Every other ordered pair is forbidden with stable code
`run_transition_forbidden`. `COMPLETED` never returns to an active state. A
rerun creates both a new physical UUIDv7 and a new prefixed public ID containing
an independently generated UUIDv7, with the new row's physical `parent_run_id`
referencing the parent; it is not a transition.

`RunEventType` is a closed string enum containing exactly:

```text
RUN_CREATED
RUN_STATE_CHANGED
RERUN_CREATED
STAGE_ATTEMPT_CREATED
STAGE_STATE_CHANGED
STAGE_LEASE_CLAIMED
STAGE_LEASE_EXPIRED
STAGE_OUTPUT_ACCEPTED
STAGE_OUTPUT_QUARANTINED
RUN_STOP_FENCE_ADVANCED
RETRY_BUDGET_EXHAUSTED
RUN_ARCHIVED
```

`RUN_STATE_CHANGED` carries the exact from/to states and command kind. Lease
heartbeats update lease timestamps but do not append a high-volume run event
or change semantic run version. Lease claim, expiry, output acceptance, and
quarantine do append events.

`QUEUED` broker-delivery failure does not fabricate a run failure transition,
because the normative machine has no `QUEUED -> FAILED_*` edge. The outbox
publisher retries delivery durably while the run remains `QUEUED`; an
authorized stop remains available. Changing this behavior requires an ADR or
normative state-machine amendment.

## Canonical stage-attempt state machine

`RunStageCode` contains exactly the nine executable stages:

```text
PREPARING
EXTRACTING
REVIEWING_CONDITIONS
GENERATING_PROFILES
CONSTRUCTING_SCENARIOS
GENERATING_PATHS
SYNTHESIZING
VALIDATING_OUTPUT
GENERATING_BRIEF
```

`RunStageAttemptState` contains exactly:

```text
PENDING
READY
RUNNING
VALIDATING
SUCCEEDED
RETRY_WAIT
FAILED_TERMINAL
CANCEL_REQUESTED
CANCELLED
```

Allowed attempt transitions are:

```text
PENDING -> READY -> RUNNING -> VALIDATING -> SUCCEEDED
RUNNING -> RETRY_WAIT
VALIDATING -> RETRY_WAIT
RUNNING -> FAILED_TERMINAL
VALIDATING -> FAILED_TERMINAL
RUNNING -> CANCEL_REQUESTED -> CANCELLED
```

A row is one immutable attempt identity. Stage-local automatic retry does not
change the run state: `RETRY_WAIT -> READY` in the normative conceptual diagram
is materialized by closing attempt N as `RETRY_WAIT` and inserting attempt N+1
for the same stage as `READY` in one transaction; attempt N is never reset. The
unique key is `(run_id, stage_code, attempt_number)`. When the stage-local
budget is exhausted, the failed attempt closes and the run takes the normative
stage-state `-> FAILED_RETRYABLE` edge. No same-stage attempt is pre-created
after that run-level failure.

`FAILED_RETRYABLE -> QUEUED` is a distinct authorized run-level retry. It does
not resume or reserve the failed stage. It preserves all prior attempts, enters
`QUEUED`, and `ACCEPT_WORKFLOW` creates a new `PREPARING` attempt with the next
attempt number for `PREPARING`; the run then executes the full canonical stage
sequence again under the sealed release set or recorded approved replacement.
This is the only interpretation compatible with the locked run graph's sole
`QUEUED -> PREPARING` edge.

Normal advancement is also atomic. `SUCCEED_STAGE` verifies and accepts the
current output under its fence, closes the current attempt `SUCCEEDED`, moves
the run to the next canonical stage, creates the next attempt `PENDING`,
derives and hashes its canonical inputs, changes it to `READY`, appends each
event, and requests dispatch through the outbox in one transaction. The final
`GENERATING_BRIEF` success performs the same acceptance/finalization but
creates no next attempt. A stage-local automatic retry copies the prior
accepted input hash. A run-level retry restarts at `PREPARING`, re-derives the
full canonical input chain, and records a replacement hash only when an
authorized replacement release changes the sealed input set.

The `VALIDATING_OUTPUT` success is the deliberate exception to any generic
“accepted output advances” shortcut. It may advance only after the Task 6
verifier atomically locks and matches the exact current immutable path-set
ID/hash, immutable `APPROVED` path-review ID/hash, validator bundle, and brief-
gate hash. Missing Task 6 persistence or a generic accepted artifact leaves the
attempt/run at `VALIDATING`/`VALIDATING_OUTPUT`; it does not skip, fabricate, or
defer the guard.

If stop arrives after an attempt enters `VALIDATING`, the run may enter
`STOP_REQUESTED` while deterministic validation finishes, but no output may be
accepted after the run stop fence. The output is quarantined and the run
becomes `STOPPED` only after the lease is released or expires. Do not invent a
`VALIDATING -> CANCEL_REQUESTED` edge without amending the normative stage
machine.

## Command transaction contract

Every mutating command executes once, in one PostgreSQL transaction, in this
order:

1. Authenticate before application dispatch, bootstrap an immutable
   `ActorContext`, and derive actor, organization, workspace, and optional
   project scope from canonical server-owned records, never request JSON.
2. Claim or read `core.command_idempotency` by
   `(organization_id, workspace_id, command_name, idempotency_key)`. Compute `request_sha256`
   from canonical command name, route resource IDs, expected version, and
   bounded normalized payload.
3. Re-authorize the actor against the server-derived workspace inside the
   transaction before returning either a new or replayed receipt.
4. Load the run/config with organization and workspace scope and verify
   `expected_version`.
5. Apply the exact transition guard and every policy/review/artifact guard. For
   `VALIDATING_OUTPUT -> GENERATING_BRIEF`, lock and verify the Task 6 current
   path-set ID/hash, immutable approved path-review ID/hash, matching validator
   bundle, and brief-gate hash in this transaction; general validator success
   or an untyped artifact reference cannot satisfy the guard.
6. Compare-and-swap the run from `expected_version` to
   `expected_version + 1`; update state and timestamps.
7. Append the next per-run `core.run_events.sequence`, append the audit event,
   insert the outbox event, and finalize the command receipt with the exact
   response body and status code.
8. Commit atomically. Dispatch occurs only from the committed outbox.

If any step fails, none of the run update, event, audit event, outbox record,
or receipt finalization commits.

Idempotency semantics are durable, not “in flight only”:

- the same scoped key plus the same request hash returns the stored receipt,
  including after completion, stop, failure, or archive;
- the same scoped key plus a different request hash returns HTTP 409 and
  `idempotency_key_conflict`;
- a rerun requires a new idempotency key and creates a new run;
- receipts remain at least as long as the run retention period; Redis TTL is
  not authority;
- a unique database constraint closes concurrent double-submit races. A
  read-then-write check in process memory is forbidden.

Optimistic concurrency semantics:

- every run starts at version `1`;
- every accepted state-changing command increments the version exactly once;
- a replayed idempotent command does not increment it;
- a stale expected version returns HTTP 409 `run_version_conflict` with the
  current version but no cross-workspace existence disclosure;
- workers use the same command service and do not update state columns
  directly.

## Lease, fencing, heartbeat, and reaper contract

PostgreSQL is lease authority. Celery task ownership is not a lease.

1. A worker claim is one atomic predicate over the exact committed dispatch
   outbox row, its `READY` stage attempt, and owning run. The outbox row must be
   eligible and name that exact attempt; the run must be in the matching active
   state with `current_stage_code` equal to the attempt's stage, its current
   `stop_fence` equal to the dispatched fence, no stop/terminal state, and no
   other active attempt. A delayed or duplicated message after
   `STOP_REQUESTED`, stage advancement, fence change, outbox cancellation, or
   another successful claim returns `lease_claim_ineligible` before provider
   work begins.
2. An eligible claim atomically increments the owning run's `lease_fence`, copies that
   globally monotonic value into the attempt's `fencing_token`, sets the
   physical `lease_owner_service_principal_id`, `lease_expires_at`, and
   `last_heartbeat_at`, and transitions the attempt to `RUNNING`.
3. Every heartbeat compares the physical
   `(stage_attempt_id, lease_owner_service_principal_id, fencing_token)` tuple
   and
   extends `lease_expires_at`. A mismatch returns `lease_lost` and the worker
   must stop accepting work.
4. Every artifact registration, cost record, stage status update, and final
   output acceptance includes the same token. The repository rejects a stale
   token. Bytes already written by a stale owner remain under a quarantine key
   and never become an accepted artifact ref.
5. The stop command advances a run-level `stop_fence` in the same transaction
   as `STOP_REQUESTED`. Output acceptance requires both the current stage token
   and the pre-stop fence value. This closes the race where a late worker
   finalizes after stop.
6. A periodic reaper uses `FOR UPDATE SKIP LOCKED` to claim expired attempts.
   It closes the abandoned attempt as `RETRY_WAIT`, emits events, and creates
   attempt N+1 as `READY` in one transaction.
7. Automatic worker-loss recovery is allowed once per stage: attempt 1 may
   create attempt 2. A second lease expiry closes attempt 2 as
   `FAILED_TERMINAL`, then records `RECORD_RETRYABLE_FAILURE` and a separate
   idempotent `EXHAUST_RETRY_BUDGET` command with the next expected version.
   No command skips the required `FAILED_RETRYABLE` state. A crash between
   those commands is resumable from their deterministic idempotency keys. An
   authorized manual retry may use a separately recorded policy only if the
   normative retry guard still passes.
8. When a run is `STOP_REQUESTED`, the reaper cancels or quarantines expired
   work and confirms `STOPPED`; it never schedules a replacement attempt.

Celery configuration for durable stage tasks is mandatory and scoped through
task annotations/decorators so legacy task delivery is not silently changed:

```text
task_acks_late = true
task_reject_on_worker_lost = true
worker_prefetch_multiplier = 1
task_track_started = true
```

Stage tasks receive prefixed public identifiers only:
`stage_attempt_public_id` and `dispatch_outbox_public_id`. A worker resolves
them under its scoped service principal and rehydrates physical run,
organization, workspace, config, release, and lease records from PostgreSQL.
It does not receive physical UUIDs, source text, prompt text, a client tenant
ID, a final state, or arbitrary serialized configuration in the Celery
message.

Retry classification is closed and tested. Retryable categories are provider
timeout, provider 429, provider 5xx, transient database/object-store
unavailability, and worker loss. Broker publication failure stays in the
outbox retry path and does not create a stage failure. Terminal categories are authentication or
authorization failure, tenant mismatch, missing canonical input, policy
denial, schema/provenance/truth validation failure, hash mismatch, malformed
provider output after the bounded repair policy, and exhausted cost/retry
budget. An unclassified exception fails closed as terminal under
`unclassified_stage_failure`; broad `autoretry_for=(Exception,)` is forbidden.

## Persistence schema and migration contract

### Identifier contract

`docs/architecture/data-model.md` controls: every aggregate's physical primary
key is PostgreSQL `uuid` and is RFC 9562 UUIDv7. A prefixed public ID is a
separate, immutable, server-generated column used at every API, event-stream,
WebSocket, log, and queue boundary. Physical UUIDs never appear in URLs,
request/response JSON, Celery payloads, browser state, logs, or telemetry.

Task 5 consumes the tenant foundation's current tested
`new_uuid7() -> UUID` and
`new_public_id(kind, physical_id, *, uuid7_factory=None) -> str` factories.
The `physical_id` argument validates the physical UUIDv7 and permits bounded
collision rejection; it is not alias input. Each row receives two independently
generated RFC 9562 UUIDv7 values: the PostgreSQL `uuid` physical primary key
and the UUIDv7 suffix encoded inside its prefixed public ID. The public suffix
must not equal or be derived from the physical key. No row falls back to
UUIDv4. Each aggregate migration adds a physical UUID-version check equivalent
to `(get_byte(uuid_send(id), 6) >> 4) = 7`; it also validates the public suffix
as UUIDv7 and requires it to differ from `id`. The tenant foundation must prove
both generators are monotonic enough for the selected deployment and
collision-safe under concurrent workers.

Each new public alias is a separate immutable database column formed as
`<kind>_<independent_public_uuid7.hex>`. The alias is stable after insert and
is the only serialized identifier; its separate column, prefix/version
validation, immutability trigger, and authorized repository mapping are
mandatory. Exact public patterns are:

```text
run_config_[0-9a-f]{32}
run_[0-9a-f]{32}
run_stage_[0-9a-f]{32}
run_event_[0-9a-f]{32}
command_receipt_[0-9a-f]{32}
outbox_[0-9a-f]{32}
artifact_[0-9a-f]{32}
audit_[0-9a-f]{32}
service_[0-9a-f]{32}
```

The migration encodes the exact pattern, UUIDv7 public-suffix version, and
physical/public inequality. For example, `run.public_id` must match
`^run_[0-9a-f]{32}$`; its suffix must parse as UUIDv7; and its suffix UUID must
not equal `run.id`. It must not contain a derivation constraint tying the two
identities together. A public alias authenticates nothing: lookup first
validates its prefix, shape, and UUID version, then resolves it only under the
server-derived `ActorContext`, explicit organization/workspace predicates, and
RLS. Bare UUID text supplied where a prefixed public alias is required is
rejected before repository lookup.

Organization, workspace, project, decision-version, source, membership, user,
and release public-ID prefixes are owned by the tenant/domain foundation and
must already be fixed before this migration. Task 5 stores their physical UUID
foreign keys after resolving caller-visible public IDs inside authorized
organization/workspace scope.

Semantic identifiers remain semantic and never become physical keys:
`RunStageCode`, stage `attempt_number`, per-run event `sequence`,
`Idempotency-Key`, configuration/artifact hashes, release semantic versions,
trace IDs, and later path display codes such as `P-03`. Non-addressable join
tables use composite physical primary keys as permitted by the data model.

### Actual-head migration procedure

Do not hardcode Task 5's revision ID, parent revision, or `down_revision` in
this brief. The earlier Task 3a planning literals `7d2c1a9e4b60` and
`down_revision = "384c98f88d53"` are stale after authority packet `ce132a5` and
must not be copied, even if those filenames still exist in an untracked brief.
Task 5 may create its migration only after the Task 3a organization/workspace/
user/membership/OIDC/ActorContext/RLS foundation has landed, reached an
acceptable canonical cutover state for this slice, and every required
decision/source/review/release schema dependency has landed through reviewed
revisions.

1. Immediately after the accepted Task 3a core foundation lands, run
   `alembic heads` on that exact integration commit. It must return one head.
   Record the commit and returned revision as `CORE_FOUNDATION_HEAD` in
   `.superpowers/sdd/task-5-report.md`; this proves ancestry, not necessarily
   Task 5's eventual direct parent.
2. After all required dependency revisions land, run `alembic heads` again on
   the exact Task 5 integration branch. It must return one head. Verify from
   `alembic history` that `CORE_FOUNDATION_HEAD` is an ancestor and record the
   current value as `RUN_CONTROL_PARENT_HEAD`.
3. Run `alembic current` against the disposable migration-test database and
   upgrade it to `RUN_CONTROL_PARENT_HEAD`.
4. Reconcile the qualified `core` SQLAlchemy metadata with that actual head and
   require `alembic check` to report no unrelated drift.
5. Generate the durable revision with
   `alembic revision -m "durable run control plane"`. Its generated
   `down_revision` must equal the recorded `RUN_CONTROL_PARENT_HEAD`. Record the
   generated revision ID and filename as `DURABLE_RUN_HEAD`.
6. If either `alembic heads` check returns zero or multiple heads, if the core
   foundation is not an ancestor, or if the direct parent changes before
   migration review, stop. Do not guess a parent, edit an older revision, copy
   a planning literal, or create an unreviewed merge revision.

The new revision creates the following explicitly qualified structures in the
canonical PostgreSQL `core` schema selected by ADR-0012. Every workspace-owned table has
physical UUID `organization_id` and `workspace_id`, every relationship uses
physical UUID foreign keys, and every repository query includes both scopes.
The tenant foundation must expose
`core.workspaces(organization_id, id)` as a composite unique key so every child row
has a composite tenant-boundary foreign key. Every tenant-owned foreign key in
this revision includes organization and workspace when the referenced table is
workspace-owned; a bare physical aggregate foreign key is forbidden.

### Scoped run-worker service identity

Task 3a reserves `ActorContext.actor_type=SERVICE` but deliberately does not
persist or authorize a service principal. Task 5 needs that missing typed actor
before an ID-only worker can bootstrap RLS scope. The architecture and security
owners must approve this extension before the durable migration is generated:

```text
core.service_principals
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^service_[0-9a-f]{32}$)
purpose varchar(32) not null check (purpose in (
  'RUN_STAGE_WORKER',
  'RUN_OUTBOX_DISPATCHER',
  'RUN_LEASE_REAPER'
))
status varchar(16) not null check (status in ('ACTIVE', 'REVOKED'))
row_version bigint not null default 1 check (row_version >= 1)
created_at timestamp with time zone not null
revoked_at timestamp with time zone null
```

No credential or token is stored in this table. Deployment maps three distinct
authenticated workload identities to three physical service-principal rows;
one credential may not hold multiple purposes. Three narrowly granted,
schema-qualified `SECURITY DEFINER` seams are mandatory:

1. `bootstrap_run_stage_worker(service_id, stage_attempt_public_id,
   dispatch_outbox_public_id)` returns one organization/workspace/run scope
   only when the service is active with purpose `RUN_STAGE_WORKER`, the exact
   committed outbox row names that exact attempt, the run is in the matching
   active stage, its stop fence is unchanged, no stop/terminal state exists,
   and no other active attempt exists.
2. `claim_run_dispatch_batch(service_id, batch_size)` accepts an active
   `RUN_OUTBOX_DISPATCHER`, bounds `batch_size`, claims only eligible committed
   dispatch rows with `FOR UPDATE SKIP LOCKED`, and returns opaque public
   outbox/attempt aliases plus the single row's tenant scope. It cannot read
   content or perform a general tenant scan outside the claim result.
3. `claim_expired_run_lease_batch(service_id, batch_size, observed_before)`
   accepts an active `RUN_LEASE_REAPER`, bounds both inputs, claims only expired
   active attempts with `FOR UPDATE SKIP LOCKED`, and returns opaque attempt
   aliases plus each claimed row's tenant scope. It cannot claim healthy,
   stopped, terminal, or already-owned work.

Each function has a fixed `search_path`, no dynamic SQL, no content access, no
general alias lookup, and execution revoked from `PUBLIC`. Each result creates
one immutable purpose-bound service `ActorContext`; it never gives a service
principal unrestricted cross-tenant query authority or RLS bypass. The worker,
dispatcher, and reaper cannot submit organization/workspace scope, exchange
purposes, or call user/reviewer commands, and a user HTTP adapter cannot
construct any service actor. Revocation, wrong-purpose, over-broad-batch,
cross-tenant, replay, and zero-visible-row tests are mandatory. Until all three
seams are accepted, Checkpoints 2–3 remain TRANSITION and production dispatch
and recovery are blocked.

Task 5 extends the single central capability enum with exactly:

```text
run_config:create
run_config:review
run:create
run:read
run:start
run:stop
run:retry
run:archive
run_event:read
run_audit:read
run_stage:execute
run_outbox:dispatch
run_lease:reap
```

Only the explicit workspace role controls user run access; an organization role
does not silently widen it. Workspace OWNER/ADMIN receive every user capability
except `run_stage:execute`, `run_outbox:dispatch`, and `run_lease:reap`; EDITOR receives `run_config:create`, `run:create`,
`run:read`, `run:start`, `run:stop`, `run:retry`, and `run_event:read`; REVIEWER
receives `run_config:review`, `run:read`, and `run_event:read`; VIEWER receives
`run:read` and `run_event:read`; SECURITY receives `run:read`, `run_event:read`,
and `run_audit:read`. `run:archive` is OWNER/ADMIN only.
`run_stage:execute`, `run_outbox:dispatch`, and `run_lease:reap` are
service-only and effective only for their exact purpose-bound bootstrap/claim
seam. No service principal receives a user or reviewer capability. Central-
policy Cartesian tests prove every unlisted role/capability and every wrong-
purpose service/capability pair is denied. Product, security, and architecture
owners must approve this policy extension before Checkpoint 2; routes and
workers must not hard-code a second matrix.

### `core.run_configs`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^run_config_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
project_id uuid not null
decision_version_id uuid not null
source_bundle_version_id uuid not null
scenario_rules jsonb not null
prompt_release_set_id uuid not null
model_release_set_id uuid not null
validator_bundle_version varchar(128) not null
simulation_adapter_version varchar(128) not null
seed_manifest jsonb not null
configuration_sha256 char(64) not null
version bigint not null default 1 check (version >= 1)
sealed_at timestamp with time zone null
created_at timestamp with time zone not null
created_by_user_id uuid not null
unique (organization_id, workspace_id, id)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, project_id) references core.projects(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, decision_version_id) references core.decision_versions(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, source_bundle_version_id) references core.source_bundles(organization_id, workspace_id, id)
foreign key (prompt_release_set_id) references core.prompt_release_sets(id)
foreign key (model_release_set_id) references core.model_release_sets(id)
foreign key (created_by_user_id) references core.users(id)
```

The two bare release-set foreign keys above are permitted only if the reviewed
governance schema defines those release sets as global. If either release table
is workspace-owned, its foreign key must instead include
`(organization_id, workspace_id, release_set_id)`. The same rule applies to
every governance reference below: global scope must be explicit in the owning
normative schema; otherwise the relationship is tenant-composite.

Normalize selected inputs into these non-addressable join tables:

```text
core.run_config_source_versions
core.run_config_starting_conditions
core.run_config_assumptions
core.run_config_decision_lenses
core.run_config_critical_uncertainties
```

Each has physical UUID `organization_id`, `workspace_id`, `run_config_id`, the
typed referenced aggregate UUID, and `ordinal >= 0`; its composite primary key
is `(organization_id, workspace_id, run_config_id, referenced_id)`, and
`(organization_id, workspace_id, run_config_id, ordinal)` is unique. Every
reference uses an organization/workspace composite foreign key. Do not store
UUID lists in unvalidated JSON.

The application validates selected public IDs, resolves them to physical UUIDs
inside tenant scope, and canonicalizes structured JSON before hashing. Once any
associated run reaches `QUEUED`, updates are rejected in the repository and by
a PostgreSQL trigger. The source/decision/release references are mandatory:
production start remains disabled until their canonical records exist.

### `core.runs`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^run_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
run_config_id uuid not null
parent_run_id uuid null
state varchar(32) not null
version bigint not null default 1 check (version >= 1)
current_stage_code varchar(32) null
workflow_ref varchar(255) null
orchestration_mode varchar(32) not null check (= 'DURABLE_V1')
stop_fence bigint not null default 0 check (stop_fence >= 0)
lease_fence bigint not null default 0 check (lease_fence >= 0)
latest_event_sequence bigint not null default 0 check (latest_event_sequence >= 0)
output_origin varchar(16) not null check (= 'synthetic')
human_respondent_count integer not null check (= 0)
is_forecast boolean not null check (= false)
is_public_opinion_measure boolean not null check (= false)
is_causal_evidence boolean not null check (= false)
source_role varchar(32) not null check (= 'starting_conditions_only')
human_validation_scope varchar(64) not null check (= 'external_to_synthetic_run')
created_at timestamp with time zone not null
updated_at timestamp with time zone not null
started_at timestamp with time zone null
completed_at timestamp with time zone null
stop_requested_at timestamp with time zone null
stopped_at timestamp with time zone null
failure_code varchar(128) null
manifest_sha256 char(64) null
created_by_user_id uuid not null
unique (organization_id, workspace_id, id)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_config_id) references core.run_configs(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, parent_run_id) references core.runs(organization_id, workspace_id, id)
foreign key (created_by_user_id) references core.users(id)
```

The database check for `state` uses all 20 values. Completed run records reject
semantic mutation; archive may change only lifecycle/archive metadata through
the command service.

### `core.run_stages`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^run_stage_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
run_id uuid not null
stage_code varchar(32) not null
attempt_number integer not null check (attempt_number >= 1)
state varchar(32) not null
input_sha256 char(64) not null
output_sha256 char(64) null
prompt_release_id uuid null
model_release_id uuid null
schema_version varchar(128) not null
failure_code varchar(128) null
retryable boolean null
lease_owner_service_principal_id uuid null
fencing_token bigint not null default 0 check (fencing_token >= 0)
lease_expires_at timestamp with time zone null
last_heartbeat_at timestamp with time zone null
started_at timestamp with time zone null
completed_at timestamp with time zone null
created_at timestamp with time zone not null
unique (organization_id, workspace_id, id)
unique (organization_id, workspace_id, run_id, stage_code, attempt_number)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id)
foreign key (prompt_release_id) references core.prompt_releases(id)
foreign key (model_release_id) references core.model_releases(id)
foreign key (lease_owner_service_principal_id) references core.service_principals(id)
```

### `core.run_events`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^run_event_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
run_id uuid not null
sequence bigint not null check (sequence >= 1)
event_type varchar(64) not null
from_state varchar(32) null
to_state varchar(32) null
actor_type varchar(32) not null check (actor_type in ('USER', 'SERVICE'))
actor_user_id uuid null
actor_service_principal_id uuid null
payload jsonb not null
occurred_at timestamp with time zone not null
trace_id varchar(128) null
unique (organization_id, workspace_id, id)
unique (organization_id, workspace_id, run_id, sequence)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id)
foreign key (actor_user_id) references core.users(id)
foreign key (actor_service_principal_id) references core.service_principals(id)
check ((actor_type = 'USER' and actor_user_id is not null and actor_service_principal_id is null) or (actor_type = 'SERVICE' and actor_user_id is null and actor_service_principal_id is not null))
```

Payloads contain prefixed public IDs, semantic versions, hashes, bounded error
codes, and safe metadata only. They contain no physical UUID, organization or
workspace ID, source text, model output, unrestricted prompt text, credentials,
or hidden reasoning.

### `core.command_idempotency`

```text
id uuid primary key check (UUID version = 7)
receipt_public_id varchar(64) not null unique check (^command_receipt_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
command_name varchar(64) not null
idempotency_key varchar(128) not null
request_sha256 char(64) not null
actor_type varchar(32) not null check (actor_type in ('USER', 'SERVICE'))
actor_user_id uuid null
actor_service_principal_id uuid null
run_config_id uuid null
run_id uuid null
status varchar(16) not null check (status in ('IN_PROGRESS', 'COMMITTED'))
response_status integer null
response_body jsonb null
event_sequence bigint null
created_at timestamp with time zone not null
completed_at timestamp with time zone null
unique (organization_id, workspace_id, id)
unique (organization_id, workspace_id, command_name, idempotency_key)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_config_id) references core.run_configs(organization_id, workspace_id, id) deferrable initially deferred
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id) deferrable initially deferred
foreign key (actor_user_id) references core.users(id)
foreign key (actor_service_principal_id) references core.service_principals(id)
check ((actor_type = 'USER' and actor_user_id is not null and actor_service_principal_id is null) or (actor_type = 'SERVICE' and actor_user_id is null and actor_service_principal_id is not null))
check ((run_config_id is not null)::integer + (run_id is not null)::integer = 1)
```

For an aggregate-creation command, trusted application code allocates the new
physical UUIDv7 and independent public UUIDv7 alias in memory before step 2,
inserts the receipt with that physical target, then inserts the target in the
same transaction. The two typed target FKs are deferrable and must resolve at
commit. No empty target, orphan receipt, or committed `IN_PROGRESS` receipt is
permitted; a deferred constraint trigger rejects an unfinished receipt at
commit. For an existing aggregate command, the receipt points to the
already-resolved physical row.

### `core.outbox_events`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^outbox_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
run_id uuid not null
run_stage_id uuid null
run_event_id uuid null
event_type varchar(64) not null
payload jsonb not null
status varchar(16) not null check (status in ('PENDING', 'PUBLISHED', 'DEAD'))
publish_attempts integer not null default 0
available_at timestamp with time zone not null
published_at timestamp with time zone null
last_error_code varchar(128) null
created_at timestamp with time zone not null
unique (organization_id, workspace_id, id)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, run_stage_id) references core.run_stages(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, run_event_id) references core.run_events(organization_id, workspace_id, id)
```

The publisher claims rows with `FOR UPDATE SKIP LOCKED`, publishes by the
outbox row's prefixed public ID, and marks `PUBLISHED` only after broker
acknowledgement. The physical UUID remains inside the repository transaction.
Duplicate delivery is expected and safe. Exhausted publication is `DEAD`,
alerted, and does not rewrite canonical run state.

`OutboxEventType` is closed to:

```text
RUN_STAGE_DISPATCH_REQUESTED
RUN_EVENT_PUBLISH_REQUESTED
RUN_STOP_WAKE_REQUESTED
```

The migration check requires the exact typed reference for each event:
`RUN_STAGE_DISPATCH_REQUESTED` has `run_stage_id` and no `run_event_id`;
`RUN_EVENT_PUBLISH_REQUESTED` has `run_event_id` and no `run_stage_id`; and
`RUN_STOP_WAKE_REQUESTED` has neither optional ID. Outbox payloads contain only
the matching prefixed public aliases, semantic event sequence, committed stop
fence where applicable, and safe routing metadata. The publisher never trusts
an untyped `aggregate_type + aggregate_id` pair.

### `core.immutable_artifact_refs`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^artifact_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
run_id uuid not null
run_stage_id uuid not null
artifact_type varchar(64) not null
storage_key varchar(512) not null
sha256 char(64) not null
byte_size bigint not null check (byte_size >= 0)
media_type varchar(255) not null
acceptance_state varchar(16) not null check (acceptance_state in ('QUARANTINED', 'ACCEPTED'))
fencing_token bigint not null
created_by_service_principal_id uuid not null
created_at timestamp with time zone not null
accepted_at timestamp with time zone null
unique (organization_id, workspace_id, id)
unique (organization_id, workspace_id, run_id, run_stage_id, artifact_type, sha256, acceptance_state)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, run_stage_id) references core.run_stages(organization_id, workspace_id, id)
foreign key (created_by_service_principal_id) references core.service_principals(id)
```

Add a PostgreSQL partial unique index on
`(organization_id, workspace_id, run_id, run_stage_id, artifact_type)` where
`acceptance_state = 'ACCEPTED'`. Object bytes live in private object storage.
Database rows are immutable refs: a worker writes a quarantine object first;
the fenced repository either inserts a `QUARANTINED` ref, or promotes bytes to
an approved server-derived key and inserts a separate `ACCEPTED` ref. It never
updates a quarantine row into accepted. Storage keys derive from environment,
organization, workspace, run, stage, and artifact IDs; the client never
supplies them.

### `core.run_audit_events`

```text
id uuid primary key check (UUID version = 7)
public_id varchar(64) not null unique check (^audit_[0-9a-f]{32}$)
organization_id uuid not null
workspace_id uuid not null
aggregate_type varchar(32) not null check (aggregate_type in ('RUN_CONFIG', 'RUN', 'RUN_STAGE', 'ARTIFACT'))
run_config_id uuid null
run_id uuid null
run_stage_id uuid null
artifact_ref_id uuid null
action varchar(64) not null
actor_type varchar(32) not null check (actor_type in ('USER', 'SERVICE'))
actor_user_id uuid null
actor_service_principal_id uuid null
reason_code varchar(128) null
before_version integer null
after_version integer null
occurred_at timestamp with time zone not null
trace_id varchar(128) null
safe_metadata jsonb not null
unique (organization_id, workspace_id, id)
foreign key (organization_id, workspace_id) references core.workspaces(organization_id, id)
foreign key (organization_id, workspace_id, run_config_id) references core.run_configs(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, run_id) references core.runs(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, run_stage_id) references core.run_stages(organization_id, workspace_id, id)
foreign key (organization_id, workspace_id, artifact_ref_id) references core.immutable_artifact_refs(organization_id, workspace_id, id)
foreign key (actor_user_id) references core.users(id)
foreign key (actor_service_principal_id) references core.service_principals(id)
check ((run_config_id is not null)::integer + (run_id is not null)::integer + (run_stage_id is not null)::integer + (artifact_ref_id is not null)::integer = 1)
check ((actor_type = 'USER' and actor_user_id is not null and actor_service_principal_id is null) or (actor_type = 'SERVICE' and actor_user_id is null and actor_service_principal_id is not null))
```

This transactional table is required because the CURRENT JSONL audit helper
cannot share a commit with a run transition. JSONL may remain a derived local
export, never the canonical audit record.

`core.run_events`, accepted `core.immutable_artifact_refs`, and
`core.run_audit_events` are
append-only under PostgreSQL update/delete-blocking triggers. Production
PostgreSQL enables and forces row-level security on every new workspace-owned
table using the parameterized transaction-local calls
`SELECT set_config('app.actor_id', :actor_id, true)`,
`SELECT set_config('app.organization_id', :organization_id, true)` and
`SELECT set_config('app.workspace_id', :workspace_id, true)`, plus the bounded
request ID, while application queries retain explicit predicates for both
scope IDs. Settings come only from an immutable user or service `ActorContext`.
Missing/malformed settings yield no rows; `WITH CHECK` mirrors `USING`; pooled
connections prove transaction-local context cannot leak into reuse. The
application role is not a table owner, superuser, or RLS-bypass role. Migration
tests exercise owner, authorized user, authorized service worker, revoked
membership/service identity, unauthorized organization/workspace, pool reuse,
and privileged incident-response roles.

Migration acceptance requires:

- upgrade from recorded `RUN_CONTROL_PARENT_HEAD` to recorded
  `DURABLE_RUN_HEAD` on a production-like PostgreSQL copy;
- downgrade back to `RUN_CONTROL_PARENT_HEAD` on a disposable copy, then
  upgrade to `DURABLE_RUN_HEAD` again;
- prove the separately recorded `CORE_FOUNDATION_HEAD` remains an ancestor in
  both directions;
- every physical aggregate ID is UUIDv7 and every separate public-alias column
  contains its exact prefix plus an independently issued UUIDv7's lowercase
  32-character hexadecimal form; the public UUIDv7 differs from and is not
  derived from the physical UUIDv7; no bare uuid-typed value or UUID syntax is
  serialized at a public/queue/log boundary;
- public-ID lookup resolves one physical row only inside the authorized
  organization/workspace and returns not-found across tenant boundaries;
- SQLAlchemy metadata inspection matches `DURABLE_RUN_HEAD`;
- row counts, physical IDs, public IDs, and hashes for tenant-foundation tables
  are unchanged;
- all new uniqueness, UUID-version, public-prefix, check, foreign-key, RLS,
  role, service-bootstrap, revocation, connection-reset, and organization/
  workspace-scope tests pass;
- `Base.metadata.create_all()` is not used as a production migration path.

## Checkpoint 1 — Lock the domain kernel

**Status after acceptance:** TRANSITION; safe to merge because it has no route
or persistence side effects.

**Files:**

- Create `backend/app/domain/run_attempt.py`.
- Modify `backend/app/domain/identifiers.py` to add the exact Task 5 public-ID
  kinds without changing Task 3a foundation aliases.
- Modify `backend/app/domain/__init__.py` to export the public run types.
- Create `backend/tests/domain/test_run_attempt.py`.

Required interfaces:

- `RunState`: exact 20-value string enum listed under “States”.
- `RunStageCode`: exact nine-value string enum listed under “Canonical
  stage-attempt state machine”.
- `RunStageAttemptState`: exact nine-value string enum listed there.
- `RunCommandKind`: exact string enum containing `SUBMIT_FOR_REVIEW`,
  `BLOCK_REVIEW`, `RESUBMIT_REVIEW`, `APPROVE_CONFIGURATION`, `START_RUN`,
  `ACCEPT_WORKFLOW`, `SUCCEED_STAGE`, `REQUEST_STOP`, `CONFIRM_STOPPED`,
  `RECORD_RETRYABLE_FAILURE`, `ACCEPT_RETRY`, `EXHAUST_RETRY_BUDGET`, and
  `ARCHIVE_RUN`.
- `RunSnapshot`: frozen, strict, extra-forbidden Pydantic model containing
  physical UUIDv7 `id`, immutable `public_id`, physical UUID
  `organization_id`, `workspace_id`, and `run_config_id`, nullable physical
  UUID `parent_run_id`, `state`, integer `version >= 1`, nullable
  `current_stage_code`, integer `stop_fence >= 0`, and the immutable
  `TruthBundle`. Physical fields remain internal; presentation DTOs expose
  public IDs only.
- `RunGuardFacts`: frozen, strict, extra-forbidden Pydantic model containing
  explicit booleans for `decision_and_config_refs_exist`,
  `deficiency_recorded`, `deficiency_revision_recorded`, `review_approved`,
  `policy_allowed`, `sources_ready`, `assumptions_approved`,
  `decision_lenses_approved`, `truth_fields_present`, `release_ids_present`,
  `config_sealed`, `config_hash_verified`, `idempotency_accepted`,
  `stage_attempt_leased`, `critical_validators_pass`,
  `current_path_set_review_approved`, `path_set_review_hashes_match`,
  `path_validator_bundle_matches`, `brief_gate_hashes_bound`,
  `brief_manifest_accepted`, `export_eligibility_calculated`,
  `authorized_stop`, `active_work_drained`, `retry_budget_remaining`,
  `release_set_unchanged`, `approved_replacement_release`,
  `retry_budget_exhausted`, and `retention_allows_archive`; plus nullable
  internal physical UUIDv7 `accepted_stage_output_artifact_ref_id`,
  `current_path_set_id`, and `approved_path_review_id`; nullable lowercase
  SHA-256 values `current_path_set_sha256`, `approved_path_review_sha256`, and
  `brief_gate_sha256`; nullable bounded `path_validator_bundle_version`; and
  nullable bounded `retryable_failure_code`. These physical references are
  never serialized; public DTOs use the corresponding prefixed public aliases.
  The `VALIDATING_OUTPUT` guard requires every path/review/gate field to be
  non-null and atomically verified against the current Task 6 heads; a generic
  accepted artifact or general validator success is insufficient.
- `RunTransition`: frozen, strict, extra-forbidden Pydantic model containing
  `command`, `from_state`, `to_state`, `next_version`, and stable
  `event_type`.
- Pure function signature:
  `decide_run_transition(snapshot: RunSnapshot, *, command: RunCommandKind, guards: RunGuardFacts) -> RunTransition`.

The domain function is pure. It does not import Flask, Celery, SQLAlchemy,
Redis, filesystem managers, or the legacy runner.

Extend the tenant foundation's `PublicIdKind` and independent
`new_public_id(kind, physical_id, *, uuid7_factory=None)` generator with exactly
`run_config`, `run`,
`run_stage`, `run_event`, `command_receipt`, `outbox`, `artifact`, `audit`, and
`service`. The function returns the exact aliases in the Identifier contract;
it generates a fresh UUIDv7 suffix distinct from the row's physical UUIDv7,
never truncates entropy, and never accepts an ordinary client-supplied alias
as the identity for a new row.

TDD sequence:

1. Assert the enum contains exactly the 20 serialized values.
2. Parameterize every allowed transition in the table above.
3. Generate the Cartesian complement of all 20 x 20 ordered pairs and assert
   stable `run_transition_forbidden` for every unlisted pair.
4. Parameterize stop from all ten active states, including
   `REVIEWING_CONDITIONS`.
5. Parameterize retryable failure from all nine stage states, including
   `REVIEWING_CONDITIONS`.
6. Prove `VALIDATING_OUTPUT -> GENERATING_BRIEF` is rejected unless the exact
   current immutable path-set ID/hash, immutable `APPROVED` review ID/hash, and
   brief gate all match, even when the general validators pass.
7. Prove terminal outcomes cannot return to active states.
8. Prove rerun is not a transition and requires a new physical UUIDv7, a new
   independently generated prefixed UUIDv7 public ID, and the parent physical
   UUID relation.
9. Exhaustively test stage-attempt transitions and attempt-number rules.
10. Assert strict models reject coercion, extra fields, non-v7 physical UUIDs,
   non-v7 public suffixes, a public UUID equal to the physical UUID,
   malformed/wrong-prefix public IDs, and overridden `TruthBundle` fields.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_run_attempt.py -q
```

## Checkpoint 2 — Reconcile schema and persist commands atomically

**Status after acceptance:** TRANSITION. It is not production authority until
the complete PostgreSQL tenant foundation, server-owned organization/workspace
authorization, and object storage are configured and migration evidence is
attached.

**Files:**

- Modify `backend/app/domain/actor_context.py` only to activate the reviewed
  service-actor shape; HTTP construction remains forbidden.
- Modify `backend/app/domain/authorization.py` to add reviewed run/user and
  run-stage-worker capabilities to the single central policy.
- Create `backend/app/application/ports/run_worker_identity.py`.
- Create `backend/app/application/ports/path_brief_gate.py` as the fail-closed
  interface that Task 6 must implement.
- Create `backend/app/infrastructure/auth/run_worker_authenticator.py`.
- Create `backend/app/infrastructure/persistence/run_schema.py`, explicitly
  using `schema="core"` and the Task 3a canonical metadata/session foundation.
- Modify `backend/app/infrastructure/persistence/core_session.py` only to expose
  the bounded run-worker bootstrap transaction and preserve pool-reset rules.
- Modify `backend/migrations/env.py` to import the qualified core and run
  metadata without importing legacy `backend/app/db/schema.py` as authority.
- Create the generated durable-run migration under
  `backend/migrations/versions/` only through the actual-head procedure above;
  record its exact revision and filename in the implementation report.
- Create `backend/app/infrastructure/persistence/run_repository.py`.
- Create `backend/app/infrastructure/persistence/outbox_repository.py`.
- Create `backend/app/application/run_attempt_service.py`.
- Create `backend/tests/persistence/test_run_migrations.py`.
- Create `backend/tests/persistence/test_run_repository.py`.
- Create `backend/tests/application/test_run_attempt_service.py`.

Required application interface is `RunAttemptService`, with these exact
methods and return type `CommandReceipt`:

- `create_run(command: CreateRunCommand)`;
- `submit_for_review(command: RunCommand)`;
- `block_review(command: ReviewRunCommand)`;
- `resubmit_review(command: RunCommand)`;
- `approve_configuration(command: ReviewRunCommand)`;
- `start(command: RunCommand)`;
- `request_stop(command: RunCommand)`;
- `accept_retry(command: RunCommand)`;
- `archive(command: RunCommand)`;
- `record_worker_transition(command: WorkerRunCommand)`;
- `create_rerun(command: CreateRerunCommand)`.

All command/receipt types are frozen, strict, extra-forbidden Pydantic models:

- `WorkerRunCommandKind`: a separate closed enum containing only
  `ACCEPT_WORKFLOW`, `SUCCEED_STAGE`, `RECORD_RETRYABLE_FAILURE`,
  `CONFIRM_STOPPED`, and `EXHAUST_RETRY_BUDGET`. It is not an alias of the
  13-value user/reviewer `RunCommandKind` and cannot represent submission,
  review approval/blocking, start, manual retry, archive, rerun, or a generic
  state assignment;

- `RunCommand`: caller-visible `run_public_id`, immutable server-derived user
  `actor: ActorContext`, `expected_version >= 1`, `idempotency_key`, and
  `command`;
- `CreateRunCommand`: caller-visible `project_public_id` and
  `run_config_public_id`, immutable server-derived user
  `actor: ActorContext`, and `idempotency_key`;
- `ReviewRunCommand`: every `RunCommand` field plus bounded `reason_code` and
  nullable `deficiency_revision_public_id`;
- `WorkerRunCommand`: repository-resolved physical UUID `run_id` and
  `stage_attempt_id`, immutable server-derived service
  `actor: ActorContext` whose physical actor ID equals the attempt's
  `lease_owner_service_principal_id`,
  `fencing_token`, `stop_fence`, `expected_version`, deterministic
  `idempotency_key`, `command: WorkerRunCommandKind`, nullable physical UUID
  `accepted_artifact_ref_id`, and nullable stable `failure_code`;
- `CreateRerunCommand`: `parent_run_public_id`, immutable server-derived user
  `actor: ActorContext`, `expected_parent_version`, `idempotency_key`, and
  optional approved `replacement_run_config_public_id`;
- `CommandReceipt`: `receipt_public_id`, `run_public_id`, `state`, `version`,
  `event_sequence`, `response_status`, immutable bounded `response_body`, and
  `replayed`.

The HTTP authentication/application boundary constructs `ActorContext`; it is
not deserialized from request JSON. The service uses that context to authorize
the command and resolve canonical rows under matching physical organization/
workspace scope. No command accepts organization/workspace scope, actor type,
actor ID, roles, capabilities, current state, next state, event sequence, truth
values, or final status from a caller.

Purpose is checked again transactionally for every service command.
`RUN_STAGE_WORKER` may issue only `ACCEPT_WORKFLOW`, `SUCCEED_STAGE`, or
`RECORD_RETRYABLE_FAILURE` for its currently leased attempt;
`RUN_LEASE_REAPER` may issue only `RECORD_RETRYABLE_FAILURE`,
`CONFIRM_STOPPED`, or `EXHAUST_RETRY_BUDGET` for a row returned by its exact
claim seam; `RUN_OUTBOX_DISPATCHER` may publish a claimed outbox row but may not
issue a run command. The application rejects every other purpose/command pair
with `service_command_forbidden` before mutation.

`RunConfigurationService` is the only writer of `core.run_configs` and has these
exact methods:

- `create(command: CreateRunConfigurationCommand) -> RunConfigurationReceipt`;
- `seal_for_start(run_config_public_id: str, *, actor: ActorContext) -> SealedRunConfiguration`.

`CreateRunConfigurationCommand` contains caller-visible prefixed public IDs for
project and canonical decision/source/review/release selections, bounded
scenario controls, immutable server-derived user `actor: ActorContext`, and
`idempotency_key`; request JSON contains no actor or physical UUID,
organization/workspace ID,
source text, prompt text, hash, sealed flag, or readiness claim. The service
resolves every public ID under authorization, rehydrates the physical records,
derives tenant scope, canonical JSON, configuration hash, truth fields, and
readiness. `seal_for_start` is invoked inside the `READY -> QUEUED` transaction
and is idempotent for the same config hash. `RunConfigurationReceipt` contains
`receipt_public_id`, `run_config_public_id`, `version`,
`configuration_sha256`, `sealed`, and `replayed`.
`SealedRunConfiguration` is a frozen strict snapshot of every persisted config
field and its hash; it is never built from the request body after creation.

`PathBriefGateVerifier` is a required application port. Task 5 defines the
interface; Task 6 supplies the canonical PostgreSQL implementation and owns the
path-set/review tables. In the same transaction as
`VALIDATING_OUTPUT -> GENERATING_BRIEF`, it must lock and return the exact
current immutable path-set physical/public IDs and SHA-256, immutable
`APPROVED` review physical/public IDs and SHA-256, matching validator-bundle
version, and immutable brief-gate SHA-256 for the scoped run. The service
compares those values with the accepted validation-stage output and persists
their public IDs/hashes in the event and manifest reference. Missing Task 6
tables, an absent/incomplete/rejected/stale/superseded review, a changed head or
hash, a validator-bundle mismatch, or a generic artifact with no typed path
identity returns a stable fail-closed result and leaves the run exactly
`VALIDATING_OUTPUT`. No caller or worker may submit these facts.

TDD sequence:

1. Prove Task 3a is at an accepted canonical cutover state, its OIDC/
   ActorContext/membership/RLS/role contract passes, the legacy root migration
   and legacy `public.*` tables remain untouched, and production startup cannot
   call `create_all`.
2. Capture `CORE_FOUNDATION_HEAD`, then capture the later single actual
   `RUN_CONTROL_PARENT_HEAD` after required dependency revisions, add the
   generated child migration, and verify upgrade/downgrade/upgrade against the
   recorded IDs and ancestry.
3. Prove UUIDv4/UUIDv1 physical IDs, UUIDv4/UUIDv1 public suffixes,
   malformed/wrong-prefix public IDs, a public UUID equal to the physical UUID,
   invalid truth fields, and invalid states reject direct inserts; prove two
   independent UUIDv7 values persist and map correctly.
4. Prove every workspace-owned FK carries the same organization/workspace,
   every typed actor/outbox/audit reference resolves, and no bare aggregate FK
   can cross a tenant boundary.
5. Race two commands with one expected version; exactly one commits.
6. Race two identical idempotency keys; both receive the same receipt and only
   one event/outbox/audit set exists.
7. Reuse the same key with a different request hash; assert
   `idempotency_key_conflict`.
8. Replay a key after `COMPLETED`; assert the original receipt and no new
   version/event.
9. Inject failure after each transaction step and prove no partial state,
   event, audit, outbox, or receipt commits.
10. Prove event sequences are gap-free per run under concurrency.
11. Prove every public-ID lookup, query, and mutation fails closed for another
    organization or workspace, including when the same semantic identifier is
    valid in each tenant.
12. Prove an authorized active service principal can bootstrap only the exact
    committed stage/outbox pair, while a revoked/wrong-purpose user or service,
    mismatched pair, guessed alias, and reused connection fail closed.
13. Prove completed configs/runs and accepted artifact refs reject mutation.
14. Prove rerun creates a new physical UUIDv7 and an independently generated
    prefixed UUIDv7 public ID while preserving the physical parent relation and
    returning public IDs only.
15. Before Task 6 lands, prove `VALIDATING_OUTPUT -> GENERATING_BRIEF` fails
    closed. After its test implementation is present, race path-head/review
    replacement against the worker command and prove only the exact locked
    path-set ID/hash, approved review ID/hash, validator bundle, and brief-gate
    hash can commit with the run event/outbox/audit/receipt.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/persistence/test_run_migrations.py tests/persistence/test_run_repository.py tests/application/test_run_attempt_service.py -q
```

## Checkpoint 3 — Add leased orchestration and dedicated stage workers

**Status after acceptance:** PARTIAL until all nine production stage adapters
consume canonical inputs and worker-kill evidence passes. A test adapter or a
wrapper around process-local `SimulationRunner` is not production completion.

**Files:**

- Create `backend/app/orchestration/__init__.py`.
- Create `backend/app/orchestration/contracts.py`.
- Create `backend/app/orchestration/celery_run_orchestrator.py`.
- Create `backend/app/orchestration/stage_worker.py`.
- Create `backend/app/orchestration/stage_registry.py`.
- Create `backend/app/orchestration/stalled_stage_reaper.py`.
- Create `backend/app/orchestration/oasis_stage_adapter.py`.
- Modify `backend/app/celery_app.py` with late-ack, worker-lost, prefetch, run
  queue, outbox publisher, and reaper settings.
- Modify `backend/app/tasks/simulation_tasks.py` to add ID-only
  `execute_run_stage_task`, `publish_run_outbox_task`, and
  `reap_stalled_run_stages_task`. Keep legacy task names only for legacy reads
  during the flag transition.
- Create `backend/tests/orchestration/test_stage_leases.py`.
- Create `backend/tests/orchestration/test_outbox_dispatch.py`.
- Create `backend/tests/orchestration/test_stage_worker.py`.
- Create `backend/tests/test_run_attempt_celery_integration.py`.

Required interfaces:

- `RunOrchestrator.dispatch_committed_event(outbox_public_id: str) -> None`;
- `StageActivity.stage_code: RunStageCode` and
  `StageActivity.execute(context: StageExecutionContext) -> StageExecutionResult`;
- `StageWorker.execute(stage_attempt_public_id: str, dispatch_outbox_public_id: str) -> None`;
- `StalledStageReaper.reap(*, batch_size: int = 100) -> ReapSummary`.

Required orchestration models are frozen, strict, and extra-forbidden:

- `StageExecutionContext`: immutable service `ActorContext`; server-derived
  physical UUID `organization_id`,
  `workspace_id`, `run_id`, `run_config_id`, and `stage_attempt_id`; immutable
  public IDs for safe telemetry; `stage_code`, `attempt_number`, physical UUID
  `lease_owner_service_principal_id` equal to the context actor, `fencing_token`,
  `stop_fence`, exact physical release IDs, and immutable physical input
  artifact-ref IDs;
- `StageExecutionResult`: exact outcome
  `SUCCEEDED | RETRYABLE_FAILURE | TERMINAL_FAILURE | STOP_OBSERVED`, accepted
  or quarantined artifact descriptors, bounded `failure_code`, and normalized
  internal UUIDv7 usage/cost record IDs. Any serialized worker result or
  telemetry projects only the corresponding prefixed public IDs;
- `ReapSummary`: non-negative counts `inspected`, `reclaimed`, `retried_once`,
  `failed_terminal`, `stopped`, and `skipped`.

The stage registry must have one real production consumer for each of the nine
stage codes. Each consumer reloads immutable inputs and exact release IDs,
checks the stop fence between provider calls, heartbeats during bounded work,
and registers output by hash and fencing token. No activity marks the run
complete itself; it submits a worker command through `RunAttemptService`.
The `VALIDATING_OUTPUT` consumer must call the Task 6 path-brief-gate verifier;
without its canonical implementation, that consumer fails closed and cannot
request `GENERATING_BRIEF`. The `GENERATING_BRIEF` consumer rehydrates the same
committed gate references and cannot accept a replacement path/review pair.

The OASIS adapter must execute in a dedicated worker queue and must not use
class dictionaries as recoverable truth. Any temporary process/thread handle
exists only to control the current leased activity; killing the worker and
reaping the lease must reconstruct work from canonical IDs without trusting
`run_state.json`.

TDD sequence:

1. Race two workers for one `READY` attempt; one lease wins.
2. Expire and reclaim a lease; the new fencing token is greater.
3. Submit output from the old token; it is quarantined and cannot advance the
   run.
4. Heartbeat with wrong owner or token; assert `lease_lost`.
5. Deliver one Celery message twice; one stage attempt/output/event set exists.
6. Kill a worker after lease, artifact write, validation, event append, and
   outbox publish boundaries; recovery does not duplicate an accepted artifact
   or cost record.
7. Reap attempt 1 into attempt 2 once; a second expiry becomes terminal under
   the exact failure transitions.
8. Request stop in each active run state; no new stage is scheduled, late
   output is quarantined, and `STOPPED` appears only after accepted work ends.
9. Simulate Redis/Celery result-backend loss after PostgreSQL commit; status
   and event history remain readable and dispatch resumes from outbox.
10. Assert task payloads contain only valid prefixed stage-attempt and outbox
    public IDs, never physical UUIDs or tenant IDs.
11. Prove the validation worker cannot advance on general validators or a
    generic artifact, and prove changing any Task 6 path-set/review/validator/
    brief-gate reference before commit leaves the run `VALIDATING_OUTPUT`.
12. Deliver an otherwise valid delayed broker message after
    `STOP_REQUESTED`, current-stage advancement, stop-fence change, and outbox
    cancellation; every claim returns `lease_claim_ineligible` and no provider
    work begins.
13. Prove the dispatcher and reaper see work only through their bounded claim
    seams under forced RLS, wrong-purpose principals see zero rows, and a
    revoked principal cannot claim or continue work.
14. Generate the Cartesian complement of service purpose and
    `WorkerRunCommandKind`; every unlisted pair fails with
    `service_command_forbidden` before mutation.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/orchestration/test_stage_leases.py tests/orchestration/test_outbox_dispatch.py tests/orchestration/test_stage_worker.py tests/test_run_attempt_celery_integration.py -q
```

## Checkpoint 4 — Expose typed commands and cursor-based reads

**Status after acceptance:** TRANSITION behind
`DECISION_WORKSPACE_DURABLE_RUNS_V1=false` by default.

**Files:**

- Modify `backend/app/api/schemas.py` with strict run request/response models.
- Create `backend/app/api/routes/run_routes.py`.
- Modify `backend/app/api/routes/__init__.py` to import `run_routes`.
- Modify `backend/app/api/ws.py` to add the durable run event stream without
  removing legacy streams yet.
- Create `backend/app/application/run_stream_ticket_service.py`.
- Create `backend/app/infrastructure/auth/run_stream_ticket_store.py`.
- Create `backend/app/api/routes/run_stream_ticket_routes.py`.
- Fix `backend/app/api/jobs.py` to instantiate `TaskManager()` for legacy jobs;
  canonical run clients use run/event endpoints instead.
- Create `backend/tests/test_run_attempt_api.py`.
- Create `backend/tests/test_run_event_reconnect.py`.
- Create `backend/tests/test_jobs_api.py`.

Public durable API under the existing simulation blueprint:

```text
POST /api/simulation/run-configurations
POST /api/simulation/runs
GET  /api/simulation/runs/<run_public_id>
POST /api/simulation/runs/<run_public_id>/submit-review
POST /api/simulation/runs/<run_public_id>/start
POST /api/simulation/runs/<run_public_id>/stop
POST /api/simulation/runs/<run_public_id>/retry
POST /api/simulation/runs/<run_public_id>/rerun
POST /api/simulation/runs/<run_public_id>/archive
POST /api/simulation/runs/<run_public_id>/event-ticket
GET  /api/simulation/runs/<run_public_id>/events?after_sequence=<n>&limit=<n>
WS   /ws/runs/<run_public_id>?after_sequence=<n>&ticket=<signed-ticket>
```

The event-ticket endpoint is protected by the canonical OIDC bootstrap. It
derives `ActorContext`, resolves the run inside organization/workspace scope,
requires `run_event:read`, rechecks current organization/workspace membership
in the issuance transaction, and issues a random, single-use, short-lived
signed ticket bound to the run public alias, authenticated OIDC subject, and
current membership row versions. Only the ticket nonce hash and expiry live in
a namespaced shared Redis replay store; the raw ticket and physical IDs are
never logged, used as Redis keys, or serialized in claims.

The WebSocket handshake first validates the signature and binding, then
atomically consumes the pre-existing nonce record with a fixed Redis Lua
compare-and-delete script: it compares the stored binding digest in constant
time and deletes only on an exact match. Missing, mismatched, expired, or
already deleted keys fail. `SET NX` is issuance/replay registration only and is
never treated as consumption. The stream opens only when the expiry,
route-bound run alias, OIDC subject, and membership versions also match a fresh
transactional membership recheck. The shared atomic compare-and-delete is the
multi-worker replay control; process memory and the APP_TOKEN-era
`AccessController.used_tickets` set are not authority. Redis unavailability or
consumption failure fails closed, is indistinguishable from not found, and
opens no stream. Reconnect requires a new ticket and replays committed events
from `after_sequence`; the ticket never grants mutation or another run's
stream. Ticket state is ephemeral authentication state, not canonical run
state, and its loss does not alter event history.

Reviewer-only `BLOCK_REVIEW`, `RESUBMIT_REVIEW`, and
`APPROVE_CONFIGURATION` remain application commands called by the canonical
review service; do not expose a generic “set state” endpoint.

Capability checks are exact: create-configuration and submit/resubmit use
`run_config:create`; block/approve use `run_config:review`; create-run uses
`run:create`; status uses `run:read`; start uses `run:start`; stop uses
`run:stop`; retry uses `run:retry`; rerun requires both `run:retry` on the
parent and `run:create` for the new row; archive uses `run:archive`; HTTP event
reads, WebSocket-ticket issue, replay, and reconnect use `run_event:read`.
Stage-worker transitions use only `run_stage:execute`; dispatcher claims use
only `run_outbox:dispatch`; reaper transitions use only `run_lease:reap`.
Every check includes the exact service purpose and occurs again in the
transaction against current membership/service status before a new or replayed
receipt is returned.

All mutating routes require `Idempotency-Key` matching
`^[A-Za-z0-9._:-]{1,128}$` and, after creation, an `If-Match` header exactly
`"run:<run_public_id>:v<version>"`. Routes authenticate,
strictly parse IDs/headers/body, authorize, call one application command, and
present its stored receipt. They never call Celery directly.

External identifier mapping is exact:

- request paths and JSON accept only the appropriate prefixed public alias;
  raw UUID text, organization/workspace IDs, and an alias with the wrong
  aggregate prefix return `public_id_invalid` before lookup;
- create-configuration accepts project, decision/source/review, and release
  public aliases; create-run accepts only a
  `run_config_[0-9a-f]{32}` alias; rerun accepts only the parent route's
  `run_[0-9a-f]{32}` alias and an optional replacement
  `run_config_[0-9a-f]{32}` alias;
- the application resolves aliases to physical UUIDv7 rows only after
  `ActorContext` bootstrap and within both organization/workspace scopes;
- response keys ending in `_id` in this public API contain public aliases. No
  response, event, error, ETag, WebSocket ticket, or Location header serializes
  a physical UUID, `organization_id`, or `workspace_id`;
- internal repositories, FKs, leases, and worker command services use physical
  UUIDs only after this mapping. They never parse a public alias as a UUID.
- no HTTP, WebSocket, Celery, or provider payload accepts a path-set ID/hash,
  path-review ID/hash/status, validator-bundle match, or brief-gate hash as a
  guard fact. Public reads expose only committed prefixed aliases/hashes after
  the transactional Task 6 verifier succeeds; until then the canonical state
  remains exactly `VALIDATING_OUTPUT`.

Status responses include at least:

```json
{
  "success": true,
  "data": {
    "run_id": "run_0194f2a87bca7be28d9c4f6a813e55c1",
    "run_config_id": "run_config_0194f2a87bc97a10a64d5481f0583c42",
    "parent_run_id": null,
    "state": "QUEUED",
    "presentation_summary": "queued",
    "current_stage_code": null,
    "version": 5,
    "event_cursor": 12,
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

The event endpoint returns each event's `run_event_[0-9a-f]{32}` public alias and
semantic sequence, ordered by sequence strictly greater than `after_sequence`,
plus a `next_sequence` cursor and `has_more`. Limit is 1-200, default 100. The
WebSocket first replays committed database events after the cursor, then uses
notification only as a wake-up hint and queries PostgreSQL again.
Disconnect/reconnect never derives history from a snapshot or Redis.

Stable errors include:

```text
run_not_found                  404
run_config_not_found           404
public_id_invalid              400
run_transition_forbidden       409
run_version_conflict           409
idempotency_key_conflict       409
run_config_not_ready           409
retry_not_allowed              409
retry_budget_exhausted         409
run_events_cursor_invalid      400
path_review_required           409
path_review_stale              409
path_review_gate_mismatch      409
path_review_gate_unavailable   503
durable_runs_disabled          404
run_command_unavailable        503
```

Unexpected errors return bounded codes without exception text, traceback,
source text, prompt text, database details, or artifact content.

TDD sequence:

1. Prove the flag blocks new canonical configuration/run creation and start by
   default, while canonical reads, event replay, ticket issuance, stop,
   publisher delivery, lease heartbeat/recovery, and reaper handling remain
   available for every already acknowledged canonical run.
2. Prove all mutable commands require valid idempotency and version headers.
3. Prove every route rejects a raw physical UUID, a malformed alias, and a
   wrong aggregate prefix; valid requests and every response/event/Location/
   ETag/WS message contain only the correct public aliases.
4. Prove route JSON cannot override organization, workspace, state, version,
   sequence, lease, fencing, truth, or final status.
5. Prove idempotent replay returns the stored body/status/ETag.
6. Prove cross-organization and cross-workspace aliases are indistinguishable
   from not found, including through WebSocket ticket issue and reconnect.
7. Prove 202 responses reference durable run/event resources, not Redis task
   TTL state.
8. Prove an HTTP cursor reconnect and WebSocket reconnect replay every event
   once in order from the client's perspective.
9. Prove exception details never cross the API boundary.
10. Prove route registration and the legacy `/api/jobs` regression.
11. Prove request JSON, headers, task payloads, and WebSocket messages cannot
    inject path/review/gate facts or make a run appear past
    `VALIDATING_OUTPUT`; only a committed verifier result exposes public
    path-set/review references and permits the next canonical state.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_run_attempt_api.py tests/test_run_event_reconnect.py tests/test_jobs_api.py -q
```

## Checkpoint 5 — Cut over legacy lifecycle and client presentation

**Status after acceptance:** PARTIAL until the production completion gates
below pass. No dual-write period is allowed.

**Files:**

- Modify `backend/app/config.py` to add
  `DECISION_WORKSPACE_DURABLE_RUNS_V1`, default `false`.
- Modify `backend/app/api/routes/execution_routes.py` so durable-linked starts,
  stops, retries, and reruns call `RunAttemptService`; reject `force=true` with
  `force_restart_removed` and create a new run for rerun.
- Modify `backend/app/api/routes/prep_routes.py` so readiness comes from the
  canonical review/config guards, not legacy status inference.
- Modify `backend/app/api/report.py` so final report/brief generation requires
  the exact canonical run state `COMPLETED`, accepted manifest/artifact refs,
  passing validators, and the manifest's exact Task 6 path-set ID/hash,
  immutable approved path-review ID/hash, validator bundle, and brief-gate hash
  to match the records that authorized `GENERATING_BRIEF`. Generic accepted
  artifacts are insufficient. `STOP_REQUESTED`, `STOPPED`,
  `FAILED_RETRYABLE`, `FAILED_TERMINAL`, and partial stages return
  `run_not_complete`.
- Modify `backend/app/models/task.py` so legacy terminal task states are
  immutable and terminal idempotency-key reuse does not represent a rerun.
- Modify `backend/tests/test_task_manager_durability.py` to reverse the two
  audit-invalid expectations rather than preserving them as compatibility.
- Create `backend/app/application/legacy_run_read_adapter.py`.
- Create `backend/tests/test_legacy_run_cutover.py`.
- Create `backend/tests/test_report_run_gate.py`.
- Verify the integration-head
  `docs/superpowers/specs/2026-08-08-decision-chamber-experience-design.md`
  contains canonical state plus display-only `RunPresentationSummary`; the
  docs steward restores the `ce132a5` correction and records the outstanding
  design approval before client cutover if it does not.
- Verify the reviewed integration-head `docs/architecture/state-machines.md`
  contains both `REVIEWING_CONDITIONS` arrows; the docs steward lands the
  locked `ce132a5` correction first if it does not. Update implementation
  status using CURRENT/PARTIAL/TARGET/TRANSITION only to match verified code.
- Create `frontend/src/domain/runState.js` with the exact canonical values and
  exhaustive display-only mapping.
- Modify `frontend/src/components/Step3Simulation.vue`.
- Modify `frontend/src/components/Step3RunWayfinder.vue`.
- Modify `frontend/src/components/Step5Interaction.vue`.
- Create `frontend/src/__tests__/run-state-presentation.spec.js`.
- Create `frontend/src/__tests__/run-event-reconnect.spec.js`.

Cutover rules:

- each run has one immutable `orchestration_mode`; no command writes both
  canonical PostgreSQL and legacy JSON/Redis lifecycle state;
- legacy simulations stay readable through `LegacyRunReadAdapter` and are
  labeled `LEGACY / LIFECYCLE NOT DURABLE`; do not synthesize missing events,
  attempts, hashes, or completion proof;
- enabling the flag affects only newly created runs; existing legacy IDs do
  not silently become canonical;
- rerunning legacy input creates a new canonical run/config after current
  review guards pass; it does not delete legacy files or reuse the ID;
- canonical execution may reach `VALIDATING_OUTPUT` before Task 6, but it must
  remain there and final report/brief routes must stay locked until the exact
  current path set, approved immutable review, validator bundle, and brief gate
  are atomically verified; no feature flag converts a generic artifact into
  that evidence;
- disabling the flag stops new canonical starts but preserves canonical reads,
  events, stop capability, and worker recovery for already acknowledged runs;
- client buttons derive allowed actions from canonical state and server
  capabilities, never phase integers, percentages, local storage, or the
  presentation summary;
- no stopped/failed/incomplete run can expose a final brief;
- replacing or superseding the current path set/review after validation relocks
  brief generation and cannot be masked by a cached status or presentation
  summary.

Checkpoint 5 tests must prove a run with passing generic validators and an
accepted generic artifact remains `VALIDATING_OUTPUT`; missing, rejected,
incomplete, stale, superseded, wrong-hash, wrong-validator-bundle, and
wrong-tenant path reviews cannot unlock brief generation; a verified exact
Task 6 gate can; and report generation rechecks the same committed references
rather than trusting state text alone.

Focused verification:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_legacy_run_cutover.py tests/test_report_run_gate.py tests/test_task_manager_durability.py -q

cd ..\frontend
npm run test -- run-state-presentation.spec.js run-event-reconnect.spec.js
```

Documentation verification:

```powershell
cd ..
python tools/validate_docs.py
python tools/validate_task5_brief.py
```

## Required red-green implementation order

Execute checkpoints in order. Within each checkpoint:

1. write one failing test for the next invariant;
2. run the smallest command and record the expected RED failure;
3. implement the minimum production behavior;
4. rerun and record GREEN;
5. run the checkpoint regression set;
6. review for spec compliance and code quality;
7. commit only the checkpoint files;
8. keep the feature flag off until the next checkpoint is verified.

Do not build API adapters before the pure transition table passes. Do not
dispatch work before transactional idempotency/outbox exists. Do not cut over
legacy routes before worker-kill and stale-fence tests pass.

## Production completion gates

Passing unit tests for the enum is not Task 5 completion. Overall Task 5 stays
PARTIAL until all of the following evidence exists:

### Dependency gates

- the Task 3a `core` foundation is at an accepted canonical cutover: UUIDv7
  organizations/users/workspaces/projects, active organization and workspace
  memberships, immutable ActorContext, exact-subject production OIDC with no
  `APP_TOKEN` fallback, capability authorization, forced RLS, application-role
  non-ownership/non-bypass, connection-pool context reset, backup/restore, and
  cross-tenant evidence all pass;
- every durable HTTP/WS route uses the canonical OIDC/ActorContext path; a route
  still protected only by the CURRENT application-wide token blocks rollout;
- the three Task 5 purpose-bound service-principal rows, workload
  authenticators, scoped stage-worker bootstrap, bounded dispatcher/reaper
  claim seams, revocation, wrong-purpose denials, and service-only capabilities
  are approved and proven under forced RLS;
- every addressable run-control row has an application-issued UUIDv7 physical
  key and a separate exact prefixed alias containing an independently issued
  UUIDv7, every external boundary uses only the alias, and every
  workspace-owned FK/query includes the authorized organization and workspace;
- canonical decision version and immutable run configuration identities exist;
- secure source ingestion and review report every referenced source version
  `READY`; no filesystem presence heuristic is accepted;
- exact prompt, model, schema, validator, simulation-adapter, and methodology
  release IDs are available for the run manifest;
- private object storage is canonical for immutable stage artifacts, with
  quarantine and accepted prefixes;
- dedicated stage workers can rehydrate all nine stages without relying on
  `SimulationRunner` class maps or `run_state.json`;
- Task 6 path sets, immutable path reviews, validator records, and brief gates
  persist as first-class tenant-scoped canonical records; the exact current
  path-set ID/hash, immutable `APPROVED` review ID/hash, matching validator
  bundle, and brief-gate hash are atomically verified before
  `VALIDATING_OUTPUT -> GENERATING_BRIEF`, and the final manifest reuses those
  exact references before a run may become `COMPLETED`.

### Reliability evidence

- acknowledged runs survive web, Celery worker, Redis, and runtime process
  restart without losing PostgreSQL state;
- worker-kill tests pass at every activity boundary for all nine stages;
- duplicate broker delivery, duplicate HTTP command, outbox replay, and
  concurrent command tests create no duplicate accepted artifact, event,
  finalization, or avoidable billing record;
- stop passes from all ten active states, including
  `REVIEWING_CONDITIONS`; no final brief exists for stopped work;
- stale workers cannot finalize after lease replacement or stop;
- one automatic stalled-stage recovery works and the second expiry fails
  truthfully under the recorded budget;
- HTTP and WebSocket reconnect from every event cursor returns an ordered,
  gap-free timeline;
- path-head/review replacement races cannot advance the run or expose a brief;
  generic validator/artifact success never substitutes for the exact Task 6
  path/review/validator/gate binding;
- migration upgrade/downgrade/re-upgrade, backup restore, and outbox recovery
  pass on production-like PostgreSQL from the recorded
  `RUN_CONTROL_PARENT_HEAD`, with `CORE_FOUNDATION_HEAD` proven in its ancestry;
- cross-organization/workspace negative tests pass at API, WebSocket,
  application, database/RLS, object, queue/bootstrap, cache, export, and log/
  telemetry boundaries, with wrong-tenant existence hidden;
- touched-file lint, focused suites, full backend/frontend suites, and
  `npm run verify` pass from a clean checkout;
- `python tools/validate_docs.py` reports zero errors and zero warnings, and
  `python tools/validate_task5_brief.py` locks the duplicated 20-state,
  40-edge, nine-stage, nine-attempt-state, ten-attempt-edge, Task 6 gate,
  service-purpose, ticket, retry, and feature-flag contracts;
- release runbook, rollback, alerts, lease-age dashboard, dead-outbox alert,
  queue-depth alert, and worker-stall alert are verified.

### Honest state claims

- Checkpoint 1 alone: **TRANSITION**, domain kernel only.
- Checkpoint 2 on SQLite or without authorization/object storage:
  **TRANSITION**, never production persistence.
- Checkpoint 3 with fake activities or a process-local runner wrapper:
  **PARTIAL**, never durable production orchestration.
- Checkpoint 4 behind the disabled flag: **TRANSITION**, API contract only.
- Checkpoint 5 without the dependency and reliability evidence above:
  **PARTIAL / REVISION REQUIRED**.
- Only all gates together permit **CURRENT** for durable runs and completion of
  Task 5.

## Rollback

Rollback disables creation/start of new durable runs but does not delete or
rewrite canonical rows. Workers continue stop/recovery for already acknowledged
runs. Durable status/events remain readable. Legacy read-only history remains
available. Rollback never re-enables force restart, terminal mutation,
idempotency-key reuse, or report generation from incomplete runs.

## Authority and dependency register

| Item | Resolution for implementation | Remaining action |
|---|---|---|
| Audit baseline omitted `REVIEWING_CONDITIONS` stop/failure arrows | Authority packet `ce132a5` resolves the contract with both normative arrows | Verify the locked packet on integration HEAD, record outstanding named approvals, and keep the validator clean before Checkpoint 1 acceptance |
| Audit baseline used a five-value `RunAttempt.state` | Authority packet `ce132a5` retains exact canonical `RunState`; `RunPresentationSummary` remains display-only | Record outstanding approval of the still-proposed experience spec and complete frontend cutover in Checkpoint 5 |
| ADR-0009 requires organization plus workspace scope; the Task 3 manifest is only a project projection and CURRENT auth has no object membership | Consume the Task 3a independent UUIDv7 physical/public identities, organization/workspace/project, membership, OIDC, ActorContext, capability, and forced-RLS foundation; keep persistence and production creation/start disabled until canonical cutover evidence passes | Task 3a must land, its `CORE_FOUNDATION_HEAD` must be captured, and no manifest/client inference is permitted |
| Task 3a reserves `ActorContext.actor_type=SERVICE` but has no persisted/authorized service principal or RLS bootstrap for stage workers, dispatchers, or reapers | Propose purpose-bound `core.service_principals`, `service_[0-9a-f]{32}` aliases, three service-only capabilities, workload authentication, and exact bounded worker/dispatcher/reaper bootstrap or claim seams | Architecture and security owner approval plus normative doc update are required before Checkpoint 2 migration generation |
| Canonical decision, source bundle, review, prompt/model release-set, and artifact schemas may not exist at the core-foundation head | Keep physical non-null references and tenant-composite FKs in the TARGET; do not replace them with client JSON or unverified UUIDs | Their reviewed migrations must land before Task 5 captures the actual single `RUN_CONTROL_PARENT_HEAD`; otherwise Checkpoint 2 stops |
| Task 6 owns canonical path sets, immutable path reviews, validator bindings, and brief gates | Define a fail-closed Task 5 application port; keep the run exactly `VALIDATING_OUTPUT` until Task 6 atomically returns the exact current path-set ID/hash, approved review ID/hash, validator bundle, and brief-gate hash | Task 6 implementation, tenant/RLS proof, replacement-race tests, and named approval are required before brief generation or `COMPLETED` can become available |
| Supporting build-plan section 66 uses a different coarse lifecycle | Normative ADR/state-machine hierarchy controls; do not add aliases | No action unless product/architecture intentionally proposes a new ADR |
| Normative run machine has no `QUEUED -> FAILED_*` edge | Keep committed work queued and retry outbox delivery; allow durable stop | An ADR/state-machine amendment is required if product wants queue exhaustion to become a run failure |
| Normative stage machine has no `VALIDATING -> CANCEL_REQUESTED` edge | Persist run stop fence, finish/quarantine validation output, and confirm stop after work drains | An ADR/state-machine amendment is required before adding that stage edge |
| ADR-0003 project-specific baseline text still describes preparation/cleanup daemon threads as CURRENT, while current code and `docs/architecture/index.md` record their Celery replacement | Treat the ADR decision as normative and current code/index as CURRENT evidence; do not reintroduce route-owned work | Docs steward should refresh the stale project-specific implication without weakening the durable target |
| Legacy declarative ORM metadata and the immutable root migration disagree | Keep legacy `public.*` metadata out of canonical authority; consume the qualified Task 3a `core` metadata and preserve root migration bytes | Actual-head schema-drift proof, legacy fingerprint, and migration rehearsal in Checkpoint 2 |

None of these items permits a production-complete claim. The organization
identity/authorization gap and canonical source/config/artifact dependencies
are hard blockers to enabling new durable runs in production.

## Full verification commands

Run in this order after all checkpoints:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_run_attempt.py tests/persistence/test_run_migrations.py tests/persistence/test_run_repository.py tests/application/test_run_attempt_service.py -q
.\.venv\Scripts\pytest tests/orchestration/test_stage_leases.py tests/orchestration/test_outbox_dispatch.py tests/orchestration/test_stage_worker.py tests/test_run_attempt_celery_integration.py -q
.\.venv\Scripts\pytest tests/test_run_attempt_api.py tests/test_run_event_reconnect.py tests/test_jobs_api.py tests/test_legacy_run_cutover.py tests/test_report_run_gate.py tests/test_task_manager_durability.py -q
.\.venv\Scripts\pytest

cd ..\frontend
npm run test
npm run lint

cd ..
python tools/validate_docs.py
python tools/validate_task5_brief.py
npm run verify
```

Migration rehearsal uses a disposable production-like PostgreSQL database:

```powershell
cd backend
.\.venv\Scripts\alembic heads
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\alembic current
.\.venv\Scripts\alembic downgrade -1
.\.venv\Scripts\alembic current
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\alembic current
```

Run this only while the recorded `DURABLE_RUN_HEAD` is the single head and its
direct parent is the recorded `RUN_CONTROL_PARENT_HEAD`, with the separately
recorded `CORE_FOUNDATION_HEAD` still in its ancestry. The report copies each
exact revision printed before/after downgrade and fails the rehearsal if the
middle revision is not the recorded run-control parent head. Never copy a
revision literal from this brief or guess a parent from a filename.

## Implementation report

Write `.superpowers/sdd/task-5-report.md` during execution. For every
checkpoint include:

- status using CURRENT/PARTIAL/TARGET/TRANSITION;
- files changed and exact commit;
- each RED command/failure and GREEN command/result;
- migration and chaos evidence;
- feature-flag state;
- unresolved dependencies, outstanding named approvals, and any newly
  discovered authority conflicts;
- independent spec and code-quality review verdicts;
- confirmation that no unrelated dirty work was staged.

Do not mark Task 5 complete merely because a client can display a run, a
Celery task returned success, or a JSON file says `completed`.
