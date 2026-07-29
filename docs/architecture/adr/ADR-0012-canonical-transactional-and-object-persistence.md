---
title: "ADR-0012: Canonical Transactional and Object Persistence"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council + Data Platform"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
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

- Every tenant-owned relational row carries `workspace_id`.
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

## Consequences

- Schema migrations, backup/restore, point-in-time recovery, and connection
  management become operating responsibilities.
- Object/database consistency requires an explicit state machine and repair
  jobs; distributed writes are not assumed atomic.
- Row-level security cannot replace application authorization, and owner or
  privileged-role bypass must be tested.
- Deletion status must remain truthful while backup/provider copies age out.

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

- Migration rehearsals compare counts, hashes, relationships, and authorization.
- Cross-tenant negative tests run at application and database layers.
- Backup restoration is tested against declared recovery objectives.
- Object deletion, orphan repair, retention, and legal-hold flows are tested.
- A derived index can be destroyed and rebuilt without losing canonical facts.
