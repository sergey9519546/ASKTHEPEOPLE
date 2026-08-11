# Zep graph worker repair brief

Status: IMPLEMENTED AND VERIFIED

## Objective

Replace the broken Celery graph-worker seam with one synchronous, retry-safe,
Celery-owned source-graph build operation. The HTTP route must only enqueue;
no route, service entry point, or worker may spawn a background thread for the
new path.

## Required behavior

1. Add focused tests before production code and capture an actual RED result.
2. `build_graph_task` must call a real synchronous `GraphBuilderService`
   operation whose API is owned by the worker.
3. The synchronous operation must perform create graph -> set ontology -> add
   source episodes -> wait for processing -> read graph information and return
   a serializable result.
4. Load the project, its approved/extracted source text, and ontology on the
   server. Do not accept source text, ontology, graph identity, or result data
   from the client task payload.
5. Use bounded Celery retry only for transient Zep failures. Deterministic
   validation/auth/not-found/input errors must fail without retry. Reuse the
   existing Zep retry classification where possible.
6. A terminal failure must move the project out of GRAPH_BUILDING into FAILED,
   persist a non-sensitive stable error, and fail the task record. Do not log
   source content, provider response bodies, or credentials.
7. A successful build must persist the server-created graph ID and mark the
   project GRAPH_COMPLETED.
8. Prevent orphaned client-visible success: if persistence fails after Zep
   creation, fail closed and preserve enough non-secret operator evidence for
   reconciliation. Do not invent a deletion workflow in this bounded repair.
9. Keep Zep mandatory for this graph-backed workflow and preserve PostgreSQL /
   object storage (or the current transition store) as canonical input truth;
   Zep is the rebuildable derived graph index.
10. Preserve `backend/app/api/simulation.py`, `backend/app/config.py`, and all
    unrelated dirty work. The review required bounded additions to the dirty
    `backend/app/models/project.py` and untracked
    `backend/app/services/project_repository.py`: graph-build ownership CAS
    operations and migration-shaped canonical ontology persistence/loading
    only. Existing Supabase behavior outside those seams remains untouched.
11. Route dispatch must claim graph-build ownership with an atomic comparison
    against the exact server-observed status/task snapshot. A lost claim is a
    stable `graph_build_conflict` 409, fails only the new task, and never
    enqueues it. Legacy dispatch unwind must also require `GRAPH_BUILDING`.
12. The graph task must late-ack and reject on worker loss at the task level so
    a killed worker is redelivered without changing global Celery defaults.
13. A task-completion exception must reread the task before compensation. A
    persisted `COMPLETED` task is canonical success and may never be downgraded;
    ambiguous reads also may not trigger a terminal overwrite.
14. Canonical ontology versions must retain the server ontology task identity.
    Unchanged saves remain idempotent; a changed version without producer
    identity fails closed rather than fabricating provenance.

## Likely files

- `backend/app/tasks/graph_tasks.py`
- `backend/app/services/graph_builder.py`
- bounded graph-build CAS additions in `backend/app/models/project.py`
- bounded graph-build CAS and ontology additions in
  `backend/app/services/project_repository.py`
- `backend/app/utils/zep_paging.py` for bounded status-aware safe reads
- a new focused test file under `backend/tests/tasks/` or `backend/tests/`
- an existing retry helper only if required and currently clean

## Verification

- Record the exact failing test output before implementation.
- Run the focused tests green.
- Run existing Zep/runtime regressions relevant to the touched code.
- Run Ruff only on touched Python files if available.
- Do not call live Zep and do not use the compromised local credential.

## Report

Write `.superpowers/sdd/zep-graph-worker-report.md` with RED evidence, GREEN
evidence, touched files, design decisions, and remaining concerns. Do not
commit or stage files.
