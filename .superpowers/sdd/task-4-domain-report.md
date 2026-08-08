# Task 4 Checkpoint 4A — Secure Source Domain Report

Status: TRANSITION / REVIEW REQUIRED

Date: 2026-08-08

## Implemented boundary

- Closed 11-state, 26-pair source lifecycle with 27 command edges.
- Strict separation of operational `FAILED` and policy/review `REJECTED`.
- Deletion request fencing from every eligible state and unresolved-target guard.
- Exact candidate, flag, processing-attempt, deletion-kind, and deletion-state
  vocabularies from the accepted brief.
- Strict disabled-domain aggregate records for sources, versions, segments,
  candidates, conditions, flags, review events, processing attempts, deletion
  requests, and deletion target statuses.
- Immutable, strict, server-scoped source command context.
- Independent UUIDv7 public aliases for all eight source-domain identifier kinds.
- Candidate review finalization, including the valid zero-candidate case.
- Unchanged acceptance retains `SOURCE_EXTRACTED` and creates `INFORMS`.
- Unchanged acceptance is bound to the persisted canonical statement SHA-256;
  matching caller text alone cannot create source-attributed provenance.
- Revised text becomes `USER_STATED` and cannot create an `INFORMS` claim.
- Deletion completion requires primary absence, a non-empty target inventory,
  only accepted terminal target states, and disclosed scheduled-expiry status.
- Upload, clean-scan, reviewable-parse, and deletion-request transitions require
  decomposed server-derived facts rather than one aggregate assertion.
- Every addressable aggregate enforces its own public-ID kind prefix.
- The closed command vocabulary includes state-changing and non-state review,
  authorization, intent, and deletion-result commands.
- Flag release and suspicious reporting require authorization plus durable
  event, invalidation, extraction, and schema-reference facts as applicable.

## Verification

- RED evidence was captured before each new contract implementation.
- Focused source suite after second review fixes: 59 passed.
- Focused source plus identifier suite: 81 passed.
- Full domain regression after second review fixes: 7,668 passed.
- Ruff on the touched domain, export, and test files: 0 findings.
- Documentation validator: 69 Markdown, 12 ADRs, 0 warnings, 0 errors.

## Honest boundary

This checkpoint is domain-only. It does not claim secure upload, scanning,
parsing, persistence, tenant authorization, object storage, worker execution,
or production rollout. Those remain gated by later Task 4 checkpoints and the
tenant persistence foundation.
