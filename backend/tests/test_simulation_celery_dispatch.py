"""
Tests for Celery application, task wrapper, distributed task state manager,
and 202 Accepted HTTP simulation dispatch endpoint.
"""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import pytest
from flask import Flask

from app import create_app
from app.api import simulation as simulation_api
from app.celery_app import celery_app
from app.models.task import TaskManager, TaskStatus, Task
from app.services.simulation_manager import SimulationManager, SimulationStatus
from app.services.simulation_runner import SimulationRunner, RunnerStatus, SimulationRunState
from app.tasks.simulation_tasks import run_simulation_task


@pytest.fixture(autouse=True)
def configure_celery_eager(monkeypatch):
    """Enable Celery eager mode during tests to avoid network connection retries."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)


@pytest.fixture
def api_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_celery_app_configuration():
    """Verify Celery app is configured with task serializer and settings."""
    assert celery_app.main == 'askthepeople'
    assert celery_app.conf.task_serializer == 'json'
    assert celery_app.conf.accept_content == ['json']


def test_simulation_start_returns_202_accepted(api_client, monkeypatch):
    """Verify POST /api/simulation/start returns HTTP 202 Accepted with task metadata."""
    sim_id = "sim_test_202"

    state = SimpleNamespace(
        simulation_id=sim_id,
        status=SimulationStatus.READY,
        graph_id="test-graph",
    )

    class FakeManager:
        def get_simulation(self, sid):
            return state if sid == sim_id else None

        def _save_simulation_state(self, saved_state):
            pass

    dummy_run_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.COMPLETED,
        total_rounds=5,
        current_round=5,
    )

    monkeypatch.setattr(simulation_api, "SimulationManager", FakeManager)
    monkeypatch.setattr(simulation_api, "_check_simulation_prepared", lambda sid: (True, {}))
    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: dummy_run_state)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sid: dummy_run_state)

    response = api_client.post(
        "/api/simulation/start",
        json={"simulation_id": sim_id, "platform": "parallel"}
    )

    assert response.status_code == 202
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["simulation_id"] == sim_id
    assert json_data["status"] == "queued"
    assert "task_id" in json_data
    assert json_data["message"] == "Simulation execution queued."
    assert "data" in json_data


def test_run_simulation_task_executes_and_updates_task_manager(monkeypatch):
    """Verify run_simulation_task Celery wrapper initializes and completes execution."""
    sim_id = "sim_task_test"
    task_id = "task_test_uuid_123"

    run_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.COMPLETED,
        total_rounds=5,
        current_round=5,
        started_at="2026-07-29T00:00:00",
    )

    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: run_state)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sid: run_state)

    task_manager = TaskManager()
    task_manager.create_task("simulation_run", metadata={"simulation_id": sim_id}, task_id=task_id)

    res = run_simulation_task.apply(
        kwargs={
            "simulation_id": sim_id,
            "task_id": task_id,
            "platform": "parallel",
        }
    )

    result_data = res.get()
    assert result_data["success"] is True
    assert result_data["simulation_id"] == sim_id
    assert result_data["status"] == "completed"

    updated_task = task_manager.get_task(task_id)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.progress == 100


def test_task_manager_redis_and_memory_fallback():
    """Verify TaskManager creates, updates, and retrieves tasks correctly."""
    tm = TaskManager()
    tid = tm.create_task("test_task", metadata={"key": "val"})

    task = tm.get_task(tid)
    assert task is not None
    assert task.task_id == tid
    assert task.status == TaskStatus.PENDING

    tm.update_task(tid, status=TaskStatus.PROCESSING, progress=50, message="Halfway")
    updated = tm.get_task(tid)
    assert updated.status == TaskStatus.PROCESSING
    assert updated.progress == 50
    assert updated.message == "Halfway"

    tm.complete_task(tid, result={"summary": "done"})
    completed = tm.get_task(tid)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.progress == 100
    assert completed.result == {"summary": "done"}


def test_get_simulation_and_task_status_endpoints(api_client, monkeypatch):
    """Verify GET status endpoints for simulation and task IDs."""
    tm = TaskManager()
    tid = tm.create_task("simulation_run", metadata={"simulation_id": "sim_status_123"})
    tm.update_task(tid, status=TaskStatus.PROCESSING, progress=30, message="In progress")

    resp = api_client.get(f"/api/simulation/task/{tid}/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["task_id"] == tid
    assert data["data"]["status"] == "processing"
    assert data["data"]["progress"] == 30

    resp2 = api_client.get("/api/simulation/sim_status_123/status")
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2["success"] is True
    assert data2["simulation_id"] == "sim_status_123"
    assert data2["task_id"] == tid


def test_prepare_simulation_returns_202_and_enqueues_task(monkeypatch, api_client):
    """P0 daemon-thread fix (audit §5 P0). The /prepare route enqueues
    work to a Celery worker and returns 202 Accepted with a Location
    header. The route no longer creates a `threading.Thread`; the work
    runs in a worker process that can survive a web restart.
    """
    from app.tasks.simulation_tasks import prepare_simulation_task

    # Patch the heavy work so the test is fast and deterministic.
    captured_kwargs = {}

    def fake_delay(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(id="celery-task-id-fake")

    monkeypatch.setattr(prepare_simulation_task, "delay", staticmethod(fake_delay))

    # Patch the synchronous entity-count read so the test does not hit Zep.
    fake_state = SimpleNamespace(
        project_id="proj_x",
        entities_count=10,
        entity_types=["Student"],
        status=SimulationStatus.CREATED,
        error=None,
    )
    fake_prepare_info = {"already_prepared": False}
    monkeypatch.setattr(
        simulation_api, "_check_simulation_prepared", lambda sim_id: (False, fake_prepare_info)
    )
    monkeypatch.setattr(
        SimulationManager, "get_simulation", lambda self, sim_id: fake_state
    )
    monkeypatch.setattr(
        SimulationManager, "_save_simulation_state", lambda self, state: None
    )
    fake_project = SimpleNamespace(simulation_requirement="a decision")
    monkeypatch.setattr(
        "app.api.simulation.ProjectManager.get_project",
        lambda project_id: fake_project,
    )
    # Skip the synchronous entity count read.
    class _FakeReader:
        def filter_defined_entities(self, **_):
            return SimpleNamespace(filtered_count=0, entity_types=[])
    monkeypatch.setattr(
        simulation_api, "ZepEntityReader", _FakeReader
    )

    response = api_client.post(
        "/api/simulation/prepare",
        json={"simulation_id": "sim_test_prepare"},
    )

    assert response.status_code == 202
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["simulation_id"] == "sim_test_prepare"
    assert data["data"]["task_id"]  # non-empty
    assert data["data"]["already_prepared"] is False

    # The Location header is set to /api/jobs/{task_id}.
    assert response.headers.get("Location", "").startswith("/api/jobs/")

    # The Celery task was enqueued with the right parameters.
    assert captured_kwargs["simulation_id"] == "sim_test_prepare"
    # entity_types comes from the request body, not from the simulation
    # state. The test does not pass entity_types, so the default (None)
    # is enqueued.
    assert captured_kwargs["entity_types"] is None
    assert captured_kwargs["use_llm_for_profiles"] is True
    assert captured_kwargs["document_text"] == ""  # no Zep reads
