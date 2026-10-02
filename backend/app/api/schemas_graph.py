"""Pydantic request schemas for the graph routes (exec-plan T26, T26 slice 4).

Scope is deliberately one model.  ``graph.py`` is the highest-risk route module
in the repository -- it holds the source-upload seam and the graph-mutation
seam -- and only one of its ten routes reads a JSON body.  A boundary that
looked wider than the input it actually validates would be worse than none, so
this file types that one body and leaves the rest alone.

SHAPE only.  Two kinds of check deliberately stay out:

* **Containment.** ``project_id`` reaches the filesystem through
  ``ProjectManager._get_project_dir`` -> ``safe_join``
  (``app/models/project.py:218``), and ``graph_id`` reaches
  ``resolve_project_graph`` (``app/services/graph_association.py:36``).  A shape
  check cannot tell whether a value stays inside its root or names a completed
  association, so neither primitive is pre-empted, reordered, or replaced here.
* **Ranges and lengths.** Those belong to ``app/utils/input_policy.py``, which
  already emits the specific error codes clients match on.

``extra="ignore"`` is a security property here, for the same reason it is on
``GenerateReportRequest``: ``tests/test_graph_worker_final_fixes.py``
(``test_build_route_only_enqueues_server_task_identity``) posts a ``graph_name``
canary to ``POST /api/graph/build`` and asserts that only server-owned ids reach
the Celery dispatch.  With ``extra="forbid"`` the request would be refused before
the handler ran, so the AGENTS.md rule 5 provenance guarantee would pass for the
wrong reason and become untestable.  ``tests/test_rate_limiting.py`` also posts a
``simulation_id`` field this route has no use for.

``strict=True`` is what still does the work.  Without it Pydantic coerces
``force: "yes"`` to True -- inventing a rebuild intent the client did not state
as a boolean -- and ``chunk_size: "500"`` to 500, which the worker then uses as
a splitter bound.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BuildGraphRequest(BaseModel):
    """Shape of the ``POST /api/graph/build`` body.

    Every field is optional because the handler already owns each of these
    conditions and its own error code.  Making ``project_id`` required here
    would replace ``"Please provide project_id"`` with a schema code and force
    clients onto a string they have never been asked to match; a ``min_length``
    on it would do the same for an empty string, which the handler already
    rejects through its own branch.
    """

    model_config = ConfigDict(extra="ignore", strict=True)

    project_id: Optional[str] = None
    force: Optional[bool] = None
    # No bounds.  The route has never constrained these ranges, and inventing a
    # bound here would narrow what the endpoint accepts under a new code rather
    # than describe the shape it already had.
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
