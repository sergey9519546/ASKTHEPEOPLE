# Zep report worker context repair brief

Status: IMPLEMENTATION IN PROGRESS

## Objective

Repair the Celery report task so its decision text and Zep graph identity come
only from server-owned simulation/project records. The graph-backed report
workflow remains Zep-required; it must not silently fall back to an empty or
unscoped graph.

## Required behavior

1. Add focused tests first and record a real RED result before production code.
2. Resolve the simulation by `simulation_id`, then resolve its project by the
   simulation's stored `project_id`; missing records fail with stable codes.
3. Use the project's persisted `simulation_requirement` as the decision text.
   It must be a non-empty stripped string. Do not access nonexistent
   `project.decision_text`.
4. Use the project's persisted `graph_id` as the authoritative source graph.
   If the simulation also stores a graph ID, it must exactly match the project
   graph. A mismatch fails closed with `report_graph_scope_mismatch`; a missing
   authoritative project graph fails with `report_graph_id_missing`.
5. Ignore any task payload `graph_id`, `decision_text`, or
   `simulation_requirement`. Do not allow caller/task payload values into the
   ReportAgent constructor.
6. Construct `ReportAgent` with the resolved authoritative graph ID, requested
   simulation ID, and stripped project decision text. Preserve existing report
   generation behavior otherwise.
7. Use stable non-sensitive task/public failure codes. Do not log decision
   text, graph provider response bodies, credentials, or client instructions.
8. Do not introduce local/empty graph fallback. Zep remains required for this
   graph-backed report experience while canonical project/simulation records
   remain outside Zep.
9. Do not edit `backend/app/models/project.py`, `backend/app/config.py`,
   Supabase files, `backend/app/api/simulation.py`, or unrelated dirty files.

## Likely files

- `backend/app/tasks/report_tasks.py`
- new focused tests under `backend/tests/`

## Verification

- Capture exact RED and GREEN output.
- Run report task tests plus relevant report/Zep regressions.
- Run Ruff on touched files if available.
- Do not call live Zep and do not use the compromised credential.

## Report

Write `.superpowers/sdd/zep-report-worker-report.md` with RED/GREEN evidence,
touched files, decisions, and concerns. Do not commit or stage.
