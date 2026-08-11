"""Tests for Task 5 concrete fixes: jobs endpoint + report terminal-state gate.

1. /api/jobs/<task_id> must use TaskManager() (singleton __new__), not the
   nonexistent TaskManager.get_instance() — the old code crashed with
   AttributeError.
2. Report generation must reject non-terminal simulations (RUNNING, PREPARING,
   etc.) — a non-terminal run's data is incomplete or in-flight.
"""

from types import SimpleNamespace

import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


# --- Jobs endpoint fix --- #


def test_jobs_endpoint_does_not_crash_on_get_instance(client):
    """Regression: /api/jobs/<task_id> called TaskManager.get_instance() which
    does not exist (TaskManager uses __new__ singleton, not get_instance()).
    The endpoint must return 404 for an unknown task, not 500 AttributeError."""
    resp = client.get("/api/jobs/nonexistent-task-id")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "task_not_found"


def test_jobs_endpoint_returns_task_for_known_id(client):
    from app.models.task import TaskManager, TaskStatus

    tm = TaskManager()
    tm._tasks.clear()
    tid = tm.create_task("test_job")
    tm.update_task(tid, status=TaskStatus.COMPLETED, progress=100)

    resp = client.get(f"/api/jobs/{tid}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["job"]["task_id"] == tid


# --- Report terminal-state gate --- #


def _mock_simulation_state(status):
    return SimpleNamespace(
        status=status,
        simulation_id="sim_test",
        project_id="proj_test",
    )


def test_report_rejects_running_simulation(client, monkeypatch):
    """Report generation must reject a RUNNING simulation — its data is
    in-flight, not reviewable."""
    from app.services.simulation_manager import SimulationManager, SimulationStatus

    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda self, sid: _mock_simulation_state(SimulationStatus.RUNNING),
    )

    resp = client.post(
        "/api/report/generate",
        json={"simulation_id": "sim_test"},
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "report_run_not_terminal"


@pytest.mark.parametrize("terminal", ["completed", "stopped", "interrupted", "failed"])
def test_report_accepts_terminal_simulation(client, monkeypatch, terminal):
    """Terminal states (completed/stopped/interrupted/failed) may generate a
    report — a stopped/failed run has partial data worth surfacing."""
    from app.services.simulation_manager import SimulationManager, SimulationStatus

    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda self, sid: _mock_simulation_state(SimulationStatus(terminal)),
    )
    # Also mock ReportManager so it doesn't find a real report.
    from app.api.report import ReportManager
    monkeypatch.setattr(
        ReportManager, "get_report_by_simulation", lambda sid: None
    )

    # The request will proceed past the status gate (that's what we're testing)
    # and may fail later for other reasons (missing project, etc.). The key
    # assertion: it does NOT return 409 report_run_not_terminal.
    resp = client.post(
        "/api/report/generate",
        json={"simulation_id": "sim_test"},
    )
    assert resp.status_code != 409 or resp.get_json().get("error") != "report_run_not_terminal"
