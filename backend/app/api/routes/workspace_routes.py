"""Decision Workspace manifest HTTP routes."""

from app.application.decision_workspace_service import (
    DecisionWorkspaceService,
    WorkspaceManifestConflict,
    WorkspaceProjectNotFound,
)

from .. import simulation_bp
from ..presentation import error_response, present


workspace_service = DecisionWorkspaceService()


@simulation_bp.route("/workspaces/by-project/<project_id>", methods=["GET"])
def get_workspace_by_project(project_id: str):
    """Resolve the server-owned workspace manifest for one project."""
    try:
        manifest = workspace_service.resolve_by_project(project_id)
        return present(manifest.model_dump(mode="json"))
    except WorkspaceProjectNotFound:
        return error_response("project_not_found", status=404)
    except WorkspaceManifestConflict:
        return error_response("workspace_manifest_conflict", status=409)
    except Exception:
        return error_response("workspace_manifest_unavailable", status=500)
