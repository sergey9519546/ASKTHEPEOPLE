"""
Path-traversal tests at the service-helper and route level.

Priority is the unit-level coverage: confirm the chokepoint helpers used by the
most dangerous sinks (ReportManager._get_report_folder feeding shutil.rmtree,
and SimulationManager._get_simulation_dir) reject traversal ids. A route-level
test for DELETE /api/report/<report_id> confirms the attack does not result in a
200 and does not delete anything outside the reports root.
"""

import json
import os

import pytest

from app import create_app
from app.services.report_agent import ReportManager
from app.services.simulation_manager import SimulationManager
from app.utils.safe_path import SafePathError


# ----------------------------- unit-level ----------------------------------

def test_report_manager_get_report_folder_rejects_traversal():
    """The sink feeding shutil.rmtree (delete_report) must reject traversal ids."""
    with pytest.raises(SafePathError):
        ReportManager._get_report_folder("../evil")


def test_report_manager_get_report_folder_rejects_absolute():
    with pytest.raises(SafePathError):
        ReportManager._get_report_folder("/etc/passwd")


def test_report_manager_get_report_folder_rejects_empty():
    with pytest.raises(SafePathError):
        ReportManager._get_report_folder("")


def test_report_manager_get_report_folder_accepts_legit_id():
    legit = "report_aabbccddeeff"
    result = ReportManager._get_report_folder(legit)
    assert result == os.path.realpath(os.path.join(ReportManager.REPORTS_DIR, legit))
    assert result.startswith(os.path.realpath(ReportManager.REPORTS_DIR))


def test_simulation_manager_get_simulation_dir_rejects_traversal():
    """The directory helper used across simulation file ops must reject traversal."""
    with pytest.raises(SafePathError):
        SimulationManager()._get_simulation_dir("../evil")


def test_simulation_manager_get_simulation_dir_rejects_empty():
    with pytest.raises(SafePathError):
        SimulationManager()._get_simulation_dir("")


def test_simulation_runner_get_run_state_dir_rejects_traversal():
    """The runner helper used across ~20 join sites must reject traversal."""
    from app.services.simulation_runner import SimulationRunner
    with pytest.raises(SafePathError):
        SimulationRunner._get_run_state_dir("../evil")


# ----------------------------- route-level ---------------------------------

@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_delete_report_traversal_does_not_succeed(client):
    """DELETE /api/report/..%2F..%2Fetc must not return 200 and must not delete
    anything outside the reports root.

    The attack is blocked because ReportManager.delete_report() calls
    _get_report_folder() first, which now raises SafePathError. The exact status
    code depends on the route's error handling (owned elsewhere) — what matters
    is that it is NOT 200 and that no directory outside REPORTS_DIR is removed.
    """
    # Snapshot an important outside path to confirm it survives the request.
    outside_marker = os.path.join(os.path.dirname(ReportManager.REPORTS_DIR))
    assert os.path.exists(outside_marker)  # parent of reports dir exists

    # URL-encoded "../../etc" as a single path segment.
    response = client.delete("/api/report/..%2F..%2Fetc")

    # Not a success response under any circumstance.
    assert response.status_code != 200
    # The attack must not have deleted the parent of REPORTS_DIR.
    assert os.path.exists(outside_marker)


def test_get_simulation_posts_traversal_returns_400(client):
    """The posts route (sqlite sink) returns a clean 400 on traversal ids.

    Note on encoding: Werkzeug does not decode %2F into a path separator for
    route matching, so a single-encoded `..%2F` is rejected at the routing
    layer (returns the SPA fallback) and never reaches the sink. The realistic
    vector that reaches Python is a literal traversal fragment in the segment,
    which we simulate here. Whatever the encoding, the assertion is the same:
    the request must NOT succeed (200) and must NOT touch the sqlite sink.
    """
    # Literal traversal fragment reaching the route handler -> safe_join rejects.
    response = client.get("/api/simulation/..%252F..%252Fetc/posts")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["error"] == "invalid_id"


def test_get_simulation_comments_traversal_returns_400(client):
    """The comments route (sqlite sink) returns a clean 400 on traversal ids."""
    response = client.get("/api/simulation/..%252F..%252Fetc/comments")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["error"] == "invalid_id"
