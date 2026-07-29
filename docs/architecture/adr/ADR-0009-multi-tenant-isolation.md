---
title: "ADR-0009: Defense-in-depth multi-tenant isolation"
status: "Accepted"
version: "1.1.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
implements_gate: "3"
applies_to: "every aggregate, every query, every API response, every export"
audit_relevance: "P1 'No object-level authorization model'"
---
# ADR-0009: Defense-in-depth multi-tenant isolation

- **Status:** Accepted
- **Date:** 2026-07-29
- **Decision owners:** Product, Architecture, Security, Research

## Context

ASKTHEPEOPLE may process confidential decision documents and generated
artifacts. Application-layer filters alone are vulnerable to missed conditions,
background-job mistakes, cache key collisions, and export/retrieval leaks.

## Decision

Use organization-scoped authorization in API and domain services, PostgreSQL
row-level security as defense in depth, tenant-prefixed object keys, scoped
worker credentials, tenant-aware cache keys, and explicit tests for every data
path. Production database roles must not casually bypass RLS.

## Consequences

Every query and job carries tenant context. Operations and migrations require
careful role design. Defense in depth reduces blast radius and makes
cross-tenant access a testable security property.

## Alternatives considered

1. Single-tenant deployment per customer. May be offered for enterprise but is
   not the general architecture.
2. Application filters only. Rejected.
3. Encrypt every tenant with a unique key but omit RLS. Useful additional
   control, not a substitute for authorization.

## Verification

Cross-tenant API/database/object/job/search/export test suite, security review
of production database roles, and incident drill.

## References

- [PostgreSQL — Row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — Database-enforced tenant-isolation reference, including owner/superuser bypass considerations.

## Project-specific implication (baseline `8b616dc7`)

The audit's P1 finding "No object-level authorization model" is the
deepest hazard against this ADR in the current code. Resolving it is
gate 3, owned by `askthepeople-persistence-engineer`.

### Current authentication — PARTIAL

The current authorization is a single bearer token. The
`require_auth` middleware at
[`backend/app/__init__.py:125-141`](../../../backend/app/__init__.py:125)
checks `APP_TOKEN` via `hmac.compare_digest`. A valid token is allowed
to operate on every project, every simulation, every report, and every
export. There is no per-resource object-level check.

### No tenant field anywhere

The current data model has no `organization_id` and no `workspace_id`:

- [`models/project.py:30-99`](../../../backend/app/models/project.py:30) —
  the `Project` dataclass has no tenant column.
- [`models/task.py:30-43`](../../../backend/app/models/task.py:30) —
  the `Task` dataclass has no tenant column.
- The simulation lifecycle in
  [`services/simulation_manager.py`](../../../backend/app/services/simulation_manager.py)
  has no tenant column.
- The filesystem layout
  `backend/uploads/projects/{project_id}/...` is not tenant-prefixed.

### Required correction

Per this ADR and the audit, every aggregate must carry
`organization_id` and `workspace_id`. Every query must be scoped by both.
PostgreSQL row-level security is the defense-in-depth layer. Object
storage keys must be tenant-prefixed. Cache keys must be tenant-aware.
Worker credentials must be scoped.

### Acceptance tests (from the audit)

User A MUST NOT be able to discover, read, start, stop, export, search,
compare, query task status, retrieve profiles, or retrieve artifacts
for User B's objects. The test suite must cover every data path.

### RLS caveat — production roles

Per this ADR, production database roles must not casually bypass RLS.
When the canonical persistence layer lands in gate 3, the migration
MUST create separate roles for the application, for migrations, and
for the read-replica — and the application role MUST be subject to
RLS. The migration checklist in
[`docs/exec-plans/02-tenancy-data-and-secure-ingestion.md`](../../exec-plans/02-tenancy-data-and-secure-ingestion.md)
will pick this up.
