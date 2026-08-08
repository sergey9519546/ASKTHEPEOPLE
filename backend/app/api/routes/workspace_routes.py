"""Decision Workspace manifest HTTP routes."""

from flask import jsonify

from app.application.decision_workspace_service import (
    DecisionWorkspaceService,
    WorkspaceManifestConflict,
    WorkspaceProjectNotFound,
)

from .. import simulation_bp


workspace_service = DecisionWorkspaceService()


@simulation_bp.route("/workspaces/by-project/<project_id>", methods=["GET"])
def get_workspace_by_project(project_id: str):
    """Resolve the server-owned workspace manifest for one project."""
    try:
        manifest = workspace_service.resolve_by_project(project_id)
        return (
            jsonify(
                {"success": True, "data": manifest.model_dump(mode="json")}
            ),
            200,
        )
    except WorkspaceProjectNotFound:
        return jsonify({"success": False, "error": "project_not_found"}), 404
    except WorkspaceManifestConflict:
        return (
            jsonify(
                {"success": False, "error": "workspace_manifest_conflict"}
            ),
            409,
        )
    except Exception:
        return (
            jsonify(
                {"success": False, "error": "workspace_manifest_unavailable"}
            ),
            500,
        )
