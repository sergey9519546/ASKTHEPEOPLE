---
title: "ADR-0012: Canonical Transactional and Object Persistence"
status: "Accepted"
version: "1.2.0"
owner: "Architecture Council + Data Platform"
last_reviewed: "2026-08-08"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "3"
applies_to: "all aggregates under backend/app/models/, all state.json files under backend/uploads/, all per-platform SQLite DBs, all object artifacts"
audit_relevance: "P1 'Non-atomic file persistence and unsafe concurrent reads', P1 'Force restart destroys provenance', P2 'Nested report-directory scans'"
---

# ADR-0012: Canonical transactional and object persistence

## Context

The current repository uses SQLite and JSONL artifacts for parts of local run
state. Production requirements include multi-tenant authorization, immutable
run configuration, concurrent workers, durable state transitions, deletion,
retention, provenance, auditability, and recoverable deployment. These
requirements need explicit transactional semantics and lifecycle-managed binary
storage.

## Decision

Use PostgreSQL as the canonical transactional system of record and
private object storage as the canonical home for uploaded source bytes and
large generated artifacts.

- Every workspace-owned relational row carries immutable physical
  `organization_id` and `workspace_id`, with a composite foreign key proving
  their relationship.
- Every addressable canonical row uses an application- or operator-issued RFC
  9562 UUIDv7 physical ID and a separate immutable server-issued public alias.
  Physical IDs never cross public, queue, log, or telemetry boundaries.
- The canonical foundation lives in an explicitly qualified PostgreSQL `core`
  schema. Schema changes are Alembic-only; web and worker startup never call
  `create_all`, stamp, migrate, provision, or backfill it.
- Application authorization is mandatory; PostgreSQL row-level security is an
  additional defense where operationally supported.
- Completed run configuration and release identifiers are immutable.
- State transitions use transactions, optimistic concurrency or row locks, and
  idempotency constraints.
- Object keys are environment/workspace scoped and never user supplied.
- Access uses short-lived authorized URLs or server streaming.
- Quarantine and approved-source prefixes have separate permissions.
- Database rows contain object IDs, cryptographic hashes, media metadata,
  retention class, and deletion state.
- SQLite/JSONL may remain for local development or migration evidence but are
  not production systems of record.
- The existing root migration is immutable. An operator-owned schema
  fingerprint distinguishes clean bootstrap, exact stamped upgrade, and
  explicit exact unversioned adoption; schema mismatch blocks stamping and
  migration.
- Adoption/backfill is offline, dry-run first, idempotent, hash reconciled, and
  preserves accepted legacy public aliases without inferring tenant ownership.
- Persistence modes are only `LEGACY`, read-only-comparison `SHADOW`, and
  `CANONICAL`. There is no dual-write mode. Once canonical is selected, any
  PostgreSQL error, timeout, absent row, or RLS denial fails closed and never
  reads or writes SQLite, filesystem, Redis, or another legacy store.

## Consequences

- Schema migrations, backup/restore, point-in-time recovery, and connection
  management become operating responsibilities.
- Object/database consistency requires an explicit state machine and repair
  jobs; distributed writes are not assumed atomic.
- Row-level security cannot replace application authorization, and owner or
  privileged-role bypass must be tested.
- Deletion status must remain truthful while backup/provider copies age out.
- A cutover record binds reconciliation evidence, application/build revision,
  operator, and rollback boundary. Before any canonical application write an
  approved rollback may return to a verified read-only legacy snapshot. After
  that write, only a schema-compatible application rollback or forward fix is
  allowed; legacy writes remain disabled.

## Rejected alternatives

- **Continue with SQLite/JSONL in production:** rejected for concurrency,
  tenant-isolation, migration, and audit limitations.
- **Put all source bytes in PostgreSQL:** rejected because large binary
  lifecycle, quarantine, and delivery are better handled in object storage.
- **Use object storage as the only database:** rejected because workflow,
  authorization, relations, and state transitions need transactional queries.
- **Treat vector or graph memory as canonical:** rejected because retrieval
  indexes are derived and must be rebuildable from approved records.

## Verification

- The checked-in legacy schema fingerprint is recreated from the unmodified
  baseline and matches byte-for-byte canonical JSON and SHA-256 evidence.
- Clean, exact-stamped, and explicit-exact-unversioned adoption rehearsals
  pass; drift, multiple heads, or edited baseline history fail closed.
- The `core` owner, migrator, application, temporary backfill, and read-only
  database roles are separate. The application role is not owner, superuser,
  or RLS-bypass.
- Shadow comparison performs zero writes and canonical failure produces a
  stable unavailable result without any legacy access.
- Migration rehearsals compare counts, hashes, relationships, and authorization.
- Cross-tenant negative tests run at application and database layers.
- Backup restoration is tested against declared recovery objectives.
- Object deletion, orphan repair, retention, and legal-hold flows are tested.
- A derived index can be destroyed and rebuilt without losing canonical facts.

## Project-specific implication (baseline `8b616dc7`)

The current code uses five storage substrates, none of which satisfies
this ADR. Gate 3 is owned by `askthepeople-persistence-engineer`.

### Storage today vs. the decision

| Substrate | Path / service | ADR requirement | Status |
|---|---|---|---|
| Filesystem JSON (projects) | `backend/uploads/projects/{project_id}/project.json` | PostgreSQL canonical | CURRENT, non-atomic — must migrate |
| Filesystem JSON (simulations) | `backend/uploads/simulations/{simulation_id}/state.json` | PostgreSQL canonical | CURRENT, non-atomic, repair-on-read |
| Filesystem JSON (reports) | `backend/uploads/reports/{report_id}/...` | Object storage canonical | CURRENT, must migrate |
| Per-platform SQLite (actions) | `backend/uploads/simulations/{simulation_id}/{reddit,twitter}_simulation.db` | PostgreSQL canonical | CURRENT, audit-flagged path-escape endpoint |
| Redis (Task) | `task:{task_id}` keys with 24h TTL | Broker / cache / rate-limit only | CURRENT, must not be the only canonical store |
| ZEP Cloud | external | Derived index, not canonical | CURRENT |
| NetworkX | in-process | Derived, must be rebuildable | CURRENT |

### Non-atomic file writes — release-blocker (audit P1)

Every JSON write today is a non-atomic
`open(..., 'w').write(...)` with no temporary file, no atomic rename, no
file lock, no version check, no compare-and-swap, no transaction, and
no coordination with job state. The audit cites this as P1
"Non-atomic file persistence and unsafe concurrent reads".

A reader of `state.json` during a write can observe a partial file. A
parser failure becomes an empty array or `None`, creating a
false-valid state. Reaching this ADR requires write →
verify → hash → mark-ready, with the canonical row in PostgreSQL
gating access to the artifact in object storage.

### Force restart destroys provenance — release-blocker (audit P1)

The force-restart path in
[`backend/app/api/simulation.py`](../../../backend/app/api/simulation.py)
can stop an existing run, delete logs, reset state, and rerun under
the same simulation ID. This violates "Completed run configuration and
release identifiers are immutable" and the
[`docs/architecture/data-model.md`](../data-model.md) append-only rule.
Reaching the ADR requires separate identifiers per
[`docs/architecture/data-model.md`](../data-model.md) — `project_id`,
`decision_version_id`, `source_bundle_version_id`, `scenario_version_id`,
`simulation_id`, `preparation_attempt_id`, `run_attempt_id`,
`report_version_id`, `export_id` — and per-attempt
immutability.

### In-memory rate limiter — release-blocker for multi-worker

[`backend/app/api/__init__.py:36-42`](../../../backend/app/api/__init__.py:36)
uses `storage_uri="memory://"` for the Flask-Limiter. The ADR requires
production rate limits to be tenant-aware and to share state across
workers. The memory store is fine for single-worker development but
must move to Redis for production.

### Object storage — TARGET

There is no object storage today. Source bytes are written to
`backend/uploads/projects/{project_id}/files/{uuid}{ext}`
([`models/project.py:247-278`](../../../backend/app/models/project.py:247)).
Reports are written to `backend/uploads/reports/{report_id}/...`.
Reaching the ADR requires the storage substrate to be private object
storage with environment/workspace-scoped keys, separate
quarantine/approved prefixes, and short-lived authorized URLs. The
existing filesystem layout becomes a development-only fallback.

### Outbox events — TARGET

State transitions today have no outbox event. Reaching the ADR requires
every state transition to write the row version increment and the
outbox event in the same transaction, with a separate publisher.

### Migrations — TARGET

Schema migrations, backup/restore, point-in-time recovery, and
connection management are not yet operating responsibilities because
the canonical store does not exist. When PostgreSQL lands, the
[`docs/release/RUNBOOK.md`](../../release/RUNBOOK.md) must be extended
with rehearsal procedures; the
[`docs/release/ACCEPTANCE.md`](../../release/ACCEPTANCE.md) must include
migration rehearsals as a release evidence item.
