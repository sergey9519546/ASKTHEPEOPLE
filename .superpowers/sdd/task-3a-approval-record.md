# Task 3A Checkpoint 3A-0 — Named Approval Record

Status: APPROVED FOR DISABLED CHECKPOINT 3A-2 ONLY

Date: 2026-08-08

Approved authority commit:
`8a67476d2e5238640587731080c7d08ae9b5ee1a`

## Named approvals

| Owner | Verdict | Exact authority SHA |
|---|---|---|
| Architecture | APPROVE | `8a67476d2e5238640587731080c7d08ae9b5ee1a` |
| Security / kill-switch | APPROVE | `8a67476d2e5238640587731080c7d08ae9b5ee1a` |
| Privacy | APPROVE | `8a67476d2e5238640587731080c7d08ae9b5ee1a` |
| Persistence | APPROVE | `8a67476d2e5238640587731080c7d08ae9b5ee1a` |
| Release | APPROVE | `8a67476d2e5238640587731080c7d08ae9b5ee1a` |

## Verification at approval

- `python tools/validate_docs.py`: PASS, 69 Markdown, 12 ADRs, zero warnings,
  zero errors.
- `python tools/validate_task3a_brief.py`: PASS, four exact audit event/reason
  pairs and one exact retention policy version.
- Baseline migration SHA-256:
  `ad37205fd879561a8a0f46d8916abb921e15601fae4c8e85da5c772356958c55`.
- The baseline migration remained byte-identical.

## Authorized boundary

Approval authorizes strict one-test-at-a-time implementation of disabled,
schema-only Checkpoint 3A-2 tests 6–18 and its owned files on disposable
PostgreSQL 16 or newer.

It does not authorize Checkpoint 3A-3 files or behavior, application or
retention grants, RLS/bootstrap/expiry functions, routes, workers, application
wiring, source/run persistence, backfill, deployment, SHADOW/CANONICAL mode,
customer or production data, production credentials, feature enablement, or a
production-readiness claim.

## Binding stop conditions

Stop on baseline mutation, role drift, migration-credential crossing,
non-PostgreSQL fallback, multiple heads, unexpected schema, partition/key
weakening, retention extension, identity reactivation, tombstone disclosure,
deletion skip edge, operator-evidence overwrite, unlisted audit event/reason/
metadata, or any required test that cannot produce recorded RED and GREEN.
