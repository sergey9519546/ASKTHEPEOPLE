"""Server-owned project association for provider-backed graph access.

This module proves only that a graph identifier is the completed graph named
by a canonical project record.  It is not tenant or actor authorization; the
current global bearer-token model cannot provide that stronger boundary.
"""

from dataclasses import dataclass
from typing import Any

from ..models.project import ProjectManager, ProjectStatus


class GraphAssociationError(RuntimeError):
    """Stable, public-safe failure raised before any graph-provider access."""

    def __init__(self, code: str, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class GraphAssociation:
    project: Any
    project_id: str
    graph_id: str


def _exact_identifier(value: object) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    return value


def resolve_project_graph(
    project_id: object,
    requested_graph_id: object | None = None,
) -> GraphAssociation:
    """Resolve an exact completed project/graph association.

    ``requested_graph_id`` may be omitted only when the caller wants the
    canonical project graph.  If supplied, it must exactly match that graph.
    Storage failures are collapsed to a stable code so connection details or
    provider payloads never cross the HTTP boundary.
    """

    exact_project_id = _exact_identifier(project_id)
    if exact_project_id is None:
        raise GraphAssociationError("project_id_required", 400)

    try:
        project = ProjectManager.get_project(exact_project_id)
    except Exception:
        raise GraphAssociationError("project_lookup_unavailable", 503) from None

    if project is None:
        raise GraphAssociationError("project_not_found", 404)

    canonical_graph_id = _exact_identifier(getattr(project, "graph_id", None))
    status = getattr(project, "status", None)
    if isinstance(status, ProjectStatus):
        status = status.value

    requested = None
    if requested_graph_id is not None:
        requested = _exact_identifier(requested_graph_id)

    if (
        status != ProjectStatus.GRAPH_COMPLETED.value
        or canonical_graph_id is None
        or (requested_graph_id is not None and requested != canonical_graph_id)
    ):
        raise GraphAssociationError("graph_not_available_for_project", 404)

    return GraphAssociation(
        project=project,
        project_id=exact_project_id,
        graph_id=canonical_graph_id,
    )
