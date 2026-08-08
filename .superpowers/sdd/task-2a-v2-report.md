# Task 2A — Epistemic Ledger v2 Domain Report

Status: IMPLEMENTED / REVIEW REQUIRED

Date: 2026-08-08

Authority: `docs/product/PRODUCT_TRUTH_CONTRACT.md` § Epistemic Ledger

## Outcome

The pure domain contract now implements the closed `epistemic-ledger/v2`
vocabulary and exact ordered triple matrix. TRANSITION relation names are not
accepted as aliases. Every `ProvenanceEdge` records the locked v2 contract
version, and the complete Cartesian complement fails closed.

This checkpoint changes only the pure contract and its tests. It does not claim
that canonical provenance persistence, endpoint-role resolution, tenant-scoped
repositories, source review, or a production writer exists.

## Code evidence

- Exact six-origin vocabulary:
  `backend/app/domain/decision_workspace.py:11`.
- Exact 23-role vocabulary:
  `backend/app/domain/decision_workspace.py:20`.
- Exact 14-relation vocabulary:
  `backend/app/domain/decision_workspace.py:46`.
- Locked edge contract version:
  `backend/app/domain/decision_workspace.py:155`.
- Closed 18-triple matrix and fail-closed validator:
  `backend/app/domain/decision_workspace.py:178` and
  `backend/app/domain/decision_workspace.py:274`.
- Exact vocabulary, all allowed triples, complete Cartesian complement,
  transition-name rejection, and version-lock tests:
  `backend/tests/domain/test_epistemic_ledger_v2.py:17`,
  `backend/tests/domain/test_epistemic_ledger_v2.py:69`,
  `backend/tests/domain/test_epistemic_ledger_v2.py:115`,
  `backend/tests/domain/test_epistemic_ledger_v2.py:132`, and
  `backend/tests/domain/test_epistemic_ledger_v2.py:137`.

## TDD evidence

RED:

```text
.\.venv\Scripts\pytest tests/domain/test_epistemic_ledger_v2.py -q
23 failed, 1 passed
```

Failures proved the current code lacked `EXTERNAL_HUMAN_EVIDENCE`, the v2
roles and relations, the locked contract version, and rejection of legacy
relation aliases.

GREEN:

```text
.\.venv\Scripts\pytest tests/domain/test_epistemic_ledger_v2.py -q
24 passed

.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py \
  tests/domain/test_epistemic_ledger_v2.py -q
7510 passed

.\.venv\Scripts\pytest tests/domain tests/test_decision_workspace_api.py -q
7551 passed
```

Ruff initially found three import-order issues. `ruff check --fix` corrected
only those import blocks; the final touched-file check is recorded with the
commit verification.

## Explicit remaining gates

- Canonical writers must resolve endpoint roles and origins from persisted
  assertions; no route, provider payload, import, or task message may supply
  them authoritatively.
- `REVISED_AS` graph semantics and the ban on an accompanying `INFORMS` edge
  require graph-level transaction validation in the source-review slice.
- PostgreSQL persistence, outbox records, RLS scope, and migration evidence
  remain unavailable until the tenant/core foundation lands.
- External-human-evidence and decision-owner-conclusion relations remain
  deferred; their reserved roles do not enable writers.
