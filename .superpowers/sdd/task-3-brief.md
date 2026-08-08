# Task 3 brief — Server-owned workspace manifest

Read this first. It is the complete requirement for this task.

## Deliverable

Add one read-only server endpoint that gives the new Decision Workspace a
stable server-issued identity and a typed manifest over the CURRENT project,
simulation, and report records. The client must not manufacture a decision ID
or guess relationships.

## Files

- Create `backend/app/application/__init__.py`.
- Create `backend/app/application/decision_workspace_service.py`.
- Create `backend/app/api/routes/workspace_routes.py`.
- Modify `backend/app/api/routes/__init__.py` to import `workspace_routes`.
- Create `backend/tests/test_decision_workspace_api.py`.
- Do not modify `backend/app/api/simulation.py`.

## Public API

```text
GET /api/simulation/workspaces/by-project/<project_id>
```

Success is HTTP 200:

```json
{
  "success": true,
  "data": {
    "workspace_id": "workspace_<32 lowercase hex characters>",
    "project_id": "proj_123",
    "decision_id": null,
    "decision_identity_status": "UNAVAILABLE",
    "manifest_version": 1,
    "storage_status": "TRANSITION",
    "simulation_ids": ["sim_1"],
    "report_ids": ["report_1"],
    "availability": {
      "sources": "AVAILABLE",
      "source_review": "UNAVAILABLE",
      "run": "AVAILABLE",
      "paths": "UNAVAILABLE",
      "brief": "AVAILABLE",
      "comparison": "UNAVAILABLE"
    },
    "truth": {
      "output_origin": "synthetic",
      "human_respondent_count": 0,
      "is_forecast": false,
      "is_public_opinion_measure": false,
      "is_causal_evidence": false,
      "source_role": "starting_conditions_only",
      "human_validation_scope": "external_to_synthetic_run"
    }
  }
}
```

Use `ABSENT`, `AVAILABLE`, `PARTIAL`, and `UNAVAILABLE` as the only capability
availability values. For this task:

- `sources` is `AVAILABLE` when the project has stored source files, otherwise
  `ABSENT`;
- `source_review` is always `UNAVAILABLE` until Task 4;
- `run` is `AVAILABLE` when at least one related simulation exists, otherwise
  `ABSENT`;
- `paths` is always `UNAVAILABLE` until Task 6;
- `brief` is `AVAILABLE` when at least one related report exists, otherwise
  `ABSENT`;
- `comparison` is always `UNAVAILABLE` until Task 7.

Errors use stable, non-leaking JSON:

```json
{"success": false, "error": "project_not_found"}
```

with HTTP 404, or:

```json
{"success": false, "error": "workspace_manifest_conflict"}
```

with HTTP 409 when an existing stored manifest is invalid, has an invalid
workspace ID, or names a different project. Unexpected failures return:

```json
{"success": false, "error": "workspace_manifest_unavailable"}
```

with HTTP 500. Do not return exception text or traceback.

## Server-owned identity

Persist only identity metadata at:

```text
<ProjectManager project directory>/workspace_manifest.json
```

The stored JSON is exactly:

```json
{
  "workspace_id": "workspace_<32 lowercase hex characters>",
  "project_id": "proj_123",
  "manifest_version": 1,
  "storage_status": "TRANSITION"
}
```

On first resolution, generate `workspace_` plus `uuid.uuid4().hex`, serialize
with stable key order/indentation, and write through
`ProjectManager._atomic_write_text`. On subsequent resolution, return the same
workspace ID. Do not accept a workspace ID from a request. Do not mutate
`project.json`.

Stored identity and response models are Pydantic v2 models with
`ConfigDict(frozen=True, extra="forbid", strict=True)`. Workspace IDs match
`^workspace_[0-9a-f]{32}$`. Project, simulation, and report IDs match the
server-ID contract from `app.domain.decision_workspace`.

## Relationship resolution

- Confirm the project exists with `ProjectManager.get_project(project_id)`.
- Resolve simulations with
  `SimulationManager().list_simulations(project_id=project_id)`.
- Resolve reports with `ReportManager.list_reports(limit=1000)` and include
  only reports whose `simulation_id` is one of the related simulation IDs.
- Sort simulation IDs and report IDs lexicographically for deterministic
  output.
- Multiple simulations or reports are listed; never choose a canonical one.
- `decision_id` remains `null`. Do not derive it from project, simulation, or
  report IDs.

## Required service interfaces

```python
class WorkspaceManifestConflict(ValueError): ...

class CapabilityAvailability(str, Enum):
    ABSENT = "ABSENT"
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"

class DecisionWorkspaceService:
    def __init__(
        self,
        project_manager=ProjectManager,
        simulation_manager_factory=SimulationManager,
        report_manager=ReportManager,
    ) -> None: ...

    def resolve_by_project(self, project_id: str) -> DecisionWorkspaceManifest:
        ...
```

The route owns one module-level service instance named `workspace_service` so
tests can replace it with a fake. Keep Flask parsing/presentation in the route
and identity/relationship work in the application service.

## Required TDD behaviors

Implement one test at a time and record RED then GREEN evidence.

1. Missing project returns 404 `project_not_found`.
2. First service resolution atomically creates a valid stored identity; second
   resolution returns the same workspace ID.
3. A caller cannot provide or override workspace or decision identity because
   the endpoint is GET-only and accepts no identity body.
4. Stored invalid JSON, extra fields, bad workspace ID, or project mismatch
   returns 409 `workspace_manifest_conflict` without regenerating over it.
5. Simulation and report relationships are filtered and sorted correctly;
   unrelated reports are excluded and multiple records are never collapsed.
6. Capability availability follows the exact rules above.
7. The response contains the complete `TruthBundle.synthetic()` values.
8. `decision_id` is always null and `decision_identity_status` is
   `UNAVAILABLE`.
9. Unexpected service exceptions return the stable 500 body without exception
   text or traceback.
10. `backend/app/api/routes/__init__.py` imports the module so the endpoint is
    registered.

Run focused tests:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_decision_workspace_api.py -q
```

Run contract regressions:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py tests/test_api_schemas.py -q
```

## Constraints

- Preserve the seven immutable truth fields exactly.
- No client-supplied canonical data.
- No heuristic decision ID.
- No route in `api/simulation.py`.
- No database migration in this task; `storage_status` truthfully says
  `TRANSITION`.
- No threads, subprocesses, LLM calls, path scans outside existing manager
  APIs, or new dependencies.
- Preserve all unrelated dirty work.

## Report

Write `.superpowers/sdd/task-3-report.md` with status, files changed, each RED
and GREEN command/result, regressions, self-review, commit, and concerns.

