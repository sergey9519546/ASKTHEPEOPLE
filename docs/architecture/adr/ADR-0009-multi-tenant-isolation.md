---
title: "ADR-0009: Defense-in-depth multi-tenant isolation"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-07-29"
review_cycle: "On material change"
research_cutoff: "2026-07-29"
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
