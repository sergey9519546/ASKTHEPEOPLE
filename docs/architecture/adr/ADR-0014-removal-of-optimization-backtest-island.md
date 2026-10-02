---
title: "ADR-0014: Removal of the Unreachable Optimization and Backtest Island"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council"
last_reviewed: "2026-10-02"
review_cycle: "Annual"
research_cutoff: "2026-10-02"
baseline_commit: "11eba8c"
implements_gate: "none (debt removal)"
implements: "ADR-0001"
applies_to: "backend/app/optimization/, backend/app/simulation/hybrid_simulator.py, backend/app/data/, backend/app/models/baseline_library.py, backend/app/evals/first_backtest.py, backend/scripts/migrate_json_to_postgres.py, backend/db/migrations/20260819_add_capability_registry.sql"
audit_relevance: "P1 dead code with production-hazard imports"
---

# ADR-0014: Removal of the Unreachable Optimization and Backtest Island

## Context

`PREDICTIVE_SIMULATION_ROADMAP.md` (archived as superseded 2026-10-01) defined
a product objective — fitting simulated output to observed real-world
behaviour — that [ADR-0001](ADR-0001-product-category-and-truth-contract.md)'s
truth contract forbids. The code that served that objective survived the
roadmap: a self-contained island of ~2,652 lines with **no production
importer**, no dependency from any route, service, or Celery task, and no
acceptance test wiring it to a live path.

Measured on 2026-10-02, the island was:

| File | Lines | State |
|---|---:|---|
| `backend/app/simulation/hybrid_simulator.py` | 563 | DO-NOT-WIRE header; 5 TODOs |
| `backend/app/optimization/learning_loop.py` | 474 | DO-NOT-WIRE header; **import-broken** (`app.db.models` never existed) |
| `backend/app/optimization/multi_objective_loss.py` | 406 | DO-NOT-WIRE header |
| `backend/app/optimization/theta_optimizer.py` | 456 | DO-NOT-WIRE header |
| `backend/app/data/outcome_fetcher.py` | 430 | no DO-NOT-WIRE; **untracked** — `.gitignore`'s broad `data/` rule swallowed the entire `backend/app/data/` package, which is also why the header pass silently missed it |
| `backend/app/models/baseline_library.py` | 323 | no DO-NOT-WIRE; imports `sklearn`, which is **not a declared dependency** |
| `backend/app/evals/first_backtest.py` | — | no DO-NOT-WIRE; unimported driver |

Adjacent broken artifacts on the same archived-roadmap lineage:

- `backend/scripts/migrate_json_to_postgres.py` — a one-shot script importing
  `app.db.database` and `app.db.models.project`, neither of which ever
  existed. Self-documented as broken in its own docstring.
- `backend/db/migrations/20260819_add_capability_registry.sql` — creates
  `capability_registry`, whose only reader was the deleted
  `backend/app/api/capability.py` FastAPI-in-a-Flask-app router.

Both import-broken files were kept alive only by a self-auditing allowance in
`backend/tests/test_no_phantom_imports.py` — the repository was paying test
machinery to tolerate defects it already knew about.

## Decision

Delete the island; do not wire it.

Nine artifacts are removed in one commit: the seven island modules above, the
one-shot migration script, and the superseded capability-registry SQL.
Guard machinery is updated in the same commit so no allowance outlives its
defect:

- `backend/tests/test_no_phantom_imports.py` — `KNOWN_UNRESOLVED` emptied and
  the two broken-import pinning tests removed (the scanning test and the
  anti-staleness guard remain).
- `backend/tests/test_backend_truth_terms.py` — the nine dead-island
  allowlist rows (group 1) removed; the file's own review comment records the
  deletion.

A future agent looking for this code finds this ADR, not a warning header.
The `.gitignore` `data/` rule is left in place; `backend/app/data/` is gone
entirely rather than excepted.

Any future predictive-fit or backtest capability requires a new accepted ADR
that supersedes ADR-0001's truth contract — that is the constitutional bar,
unchanged.

## Consequences

### Positive

- All 13 TODO/FIXME markers inside `backend/app` are gone with the island;
  production code carried none.
- Both known `ModuleNotFoundError` traps are eliminated with the allowance
  that tolerated them.
- No live test imports the island (verified by scan on 2026-10-02), so the
  deletion is behaviour-preserving for the entire suite.
- The untracked-file discovery closes an audit hole: `.gitignore`'s `data/`
  broad-rule had made an application package invisible to every previous
  sweep.

### Negative / accepted

- ~2,652 lines of optimisation research code (theta search, multi-objective
  loss, baseline evaluators) are no longer in the repo. The design notes live
  on in `docs/archive/misc/PREDICTIVE_SIMULATION_ROADMAP-2026-08-19.md`,
  annotated as forbidden.
- Any legitimate future need for these ideas requires re-authoring under a new
  ADR, not resurrection of this code.

### Verification

- `backend/tests/test_no_phantom_imports.py` and
  `backend/tests/test_backend_truth_terms.py` pass with empty/pruned maps.
- Full backend suite and `npm run verify` pass after the deletion commit.
