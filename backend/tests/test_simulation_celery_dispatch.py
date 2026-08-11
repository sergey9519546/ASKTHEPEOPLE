"""
Tests for Celery application, task wrapper, distributed task state manager,
and 202 Accepted HTTP simulation dispatch endpoint.
"""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import pytest
from flask import Flask

from app import create_app
from app.api.routes import execution_routes as execution_api
from app.api.routes import prep_routes
from app.celery_app import celery_app
from app.models.task import TaskManager, TaskStatus, Task
from app.services.simulation_manager import SimulationManager, SimulationStatus
from app.services.simulation_runner import SimulationRunner, RunnerStatus, SimulationRunState
from app.tasks.simulation_tasks import (
    finalize_decision_lens_preparation_task,
    prepare_simulation_task,
    reconcile_stale_simulation_runs_task,
    run_simulation_task,
)
from app.tasks.graph_tasks import generate_ontology_task


@pytest.fixture(autouse=True)
def configure_celery_eager(monkeypatch):
    """Enable Celery eager mode during tests to avoid network connection retries."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setattr(
        execution_api,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: {},
    )


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


def test_no_module_in_app_package_shadows_the_celery_distribution():
    """`app/celery.py` must not come back.

    It re-exported celery_app under a name that collides with the installed
    distribution. Harmless while every entry point runs from backend/ — the
    Procfile and worker_wrapper.sh both do — but the moment backend/app/ lands
    on sys.path, `from celery import Celery` inside celery_app.py resolves to
    that alias and imports itself.
    """
    import os
    import celery as celery_distribution
    import app as app_package

    app_dir = os.path.dirname(os.path.abspath(app_package.__file__))
    celery_file = os.path.abspath(celery_distribution.__file__)
    assert not celery_file.startswith(app_dir + os.sep), (
        f"`import celery` resolved inside the app package: {celery_file}"
    )
    assert not os.path.exists(os.path.join(app_dir, "celery.py"))


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

    monkeypatch.setattr(execution_api, "SimulationManager", FakeManager)
    monkeypatch.setattr(execution_api, "_check_simulation_prepared", lambda sid: (True, {}))
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


def test_simulation_start_dispatch_failure_fails_task_without_running_in_request(
    api_client, monkeypatch
):
    """A broker failure must fail closed at the HTTP dispatch seam.

    The request process does not own OASIS execution. If Celery cannot accept
    the job, callers receive a stable service-unavailable response and the
    client-facing task record becomes terminal instead of running OASIS inside
    the request process.
    """
    sim_id = "sim_dispatch_unavailable"
    state = SimpleNamespace(
        simulation_id=sim_id,
        status=SimulationStatus.READY,
        graph_id="source-graph",
    )

    class FakeManager:
        def get_simulation(self, sid):
            return state if sid == sim_id else None

        def _save_simulation_state(self, _saved_state):
            raise AssertionError("dispatch failure must not persist RUNNING")

    def reject_dispatch(**_kwargs):
        raise ConnectionError("broker unavailable")

    def reject_direct_runner(**_kwargs):
        raise AssertionError("request route must not run OASIS directly")

    from app.tasks.simulation_tasks import run_simulation_task

    monkeypatch.setattr(execution_api, "SimulationManager", FakeManager)
    monkeypatch.setattr(
        execution_api, "_check_simulation_prepared", lambda _sid: (True, {})
    )
    monkeypatch.setattr(run_simulation_task, "apply_async", reject_dispatch)
    monkeypatch.setattr(
        SimulationRunner, "start_simulation", reject_direct_runner
    )

    response = api_client.post(
        "/api/simulation/start",
        json={"simulation_id": sim_id, "platform": "parallel"},
    )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["code"] == "simulation_dispatch_unavailable"
    assert payload["task_id"]
    task = TaskManager().get_task(payload["task_id"])
    assert task is not None
    assert task.status == TaskStatus.FAILED
    assert task.public_error == "simulation_dispatch_unavailable"
    assert state.status == SimulationStatus.READY


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


def test_run_simulation_task_passes_task_id_as_attempt_owner(monkeypatch):
    sim_id = "sim_owner_test"
    task_id = "task_owner_uuid_123"
    captured = {}
    completed = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.COMPLETED,
        total_rounds=1,
        current_round=1,
    )

    def start_simulation(**kwargs):
        captured.update(kwargs)
        return completed

    monkeypatch.setattr(SimulationRunner, "start_simulation", start_simulation)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda _sid: completed)
    TaskManager().create_task(
        "simulation_run", metadata={"simulation_id": sim_id}, task_id=task_id
    )

    run_simulation_task.apply(
        kwargs={"simulation_id": sim_id, "task_id": task_id}
    ).get()

    assert captured["owner_id"] == task_id


def test_run_simulation_task_records_cooperative_stop_as_cancelled(monkeypatch):
    """A manually stopped run is terminal cancellation, not completion."""
    sim_id = "sim_task_stopped"
    task_id = "task_stopped_uuid_123"
    stopped_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.STOPPED,
        total_rounds=10,
        current_round=4,
        started_at="2026-08-08T00:00:00",
        completed_at="2026-08-08T00:04:00",
    )

    monkeypatch.setattr(
        SimulationRunner, "start_simulation", lambda **_kwargs: stopped_state
    )
    monkeypatch.setattr(
        SimulationRunner, "get_run_state", lambda _sid: stopped_state
    )

    task_manager = TaskManager()
    task_manager.create_task(
        "simulation_run",
        metadata={"simulation_id": sim_id},
        task_id=task_id,
    )

    result = run_simulation_task.apply(
        kwargs={
            "simulation_id": sim_id,
            "task_id": task_id,
            "platform": "parallel",
        }
    ).get()

    assert result["success"] is True
    assert result["status"] == "cancelled"
    cancelled = task_manager.get_task(task_id)
    assert cancelled is not None
    assert cancelled.status == TaskStatus.CANCELLED
    assert cancelled.progress == 40
    assert cancelled.result["runner_status"] == RunnerStatus.STOPPED.value


def test_run_simulation_task_failed_runner_path_fails_once_with_specific_error(monkeypatch):
    """When the runner reports FAILED, the task must be failed exactly once
    with the runner's specific error — not double-failed with the second
    call clobbering the first's message (regression: the FAILED path used
    to call fail_task then raise into an except that called it again)."""
    sim_id = "sim_failed_path"
    task_id = "task_failed_once"
    runner_error = "OASIS subprocess exited with code 137"

    failed_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.FAILED,
        total_rounds=3,
        current_round=2,
        started_at="2026-07-29T00:00:00",
        error=runner_error,
    )

    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: failed_state)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sid: failed_state)

    task_manager = TaskManager()
    task_manager.create_task("simulation_run", metadata={"simulation_id": sim_id}, task_id=task_id)

    # Spy on fail_task to count calls.
    fail_calls = []
    original_fail = task_manager.fail_task

    def counting_fail(tid, error=None, **kwargs):
        fail_calls.append((tid, error))
        return original_fail(tid, error=error, **kwargs)

    monkeypatch.setattr(task_manager, "fail_task", counting_fail)

    # The FAILED-runner path raises RuntimeError (propagates in eager mode).
    import pytest as _pytest
    with _pytest.raises(RuntimeError, match="code 137"):
        run_simulation_task.apply(
            kwargs={"simulation_id": sim_id, "task_id": task_id, "platform": "parallel"}
        )

    # fail_task called exactly once (not twice), carrying the runner's error.
    assert len(fail_calls) == 1, f"expected one fail_task call, got {len(fail_calls)}"
    assert fail_calls[0][0] == task_id
    assert fail_calls[0][1] == runner_error

    failed = task_manager.get_task(task_id)
    assert failed.status == TaskStatus.FAILED
    assert failed.error == runner_error


def test_run_simulation_task_interrupted_path_fails_once_with_public_code(monkeypatch):
    sim_id = "sim_interrupted_path"
    task_id = "task_interrupted_once"
    interrupted = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.INTERRUPTED,
        total_rounds=8,
        current_round=3,
        error="run-attempt heartbeat expired",
    )
    monkeypatch.setattr(
        SimulationRunner, "start_simulation", lambda **_kwargs: interrupted
    )
    monkeypatch.setattr(
        SimulationRunner, "get_run_state", lambda _sid: interrupted
    )

    manager = TaskManager()
    manager.create_task(
        "simulation_run", metadata={"simulation_id": sim_id}, task_id=task_id
    )
    fail_calls = []
    original_fail = manager.fail_task

    def counting_fail(tid, error, **kwargs):
        fail_calls.append((tid, error, kwargs))
        return original_fail(tid, error, **kwargs)

    monkeypatch.setattr(manager, "fail_task", counting_fail)

    with pytest.raises(RuntimeError, match="heartbeat expired"):
        run_simulation_task.apply(
            kwargs={"simulation_id": sim_id, "task_id": task_id}
        )

    assert len(fail_calls) == 1
    failed = manager.get_task(task_id)
    assert failed.status == TaskStatus.FAILED
    assert failed.public_error == "simulation_interrupted"


def test_celery_beat_registers_bounded_stale_run_reconciliation():
    schedule = celery_app.conf.beat_schedule["reconcile-stale-simulation-runs"]

    assert schedule["task"] == "tasks.reconcile_stale_simulation_runs"
    assert 0 < schedule["kwargs"]["limit"] <= 1000


def test_stale_run_reconciliation_task_scans_only_the_requested_limit(
    monkeypatch, tmp_path
):
    for simulation_id in ("sim-1", "sim-2", "sim-3"):
        (tmp_path / simulation_id).mkdir()
    visited = []
    monkeypatch.setattr(
        "app.tasks.simulation_tasks.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "reconcile_stale_run",
        lambda simulation_id: visited.append(simulation_id),
    )

    result = reconcile_stale_simulation_runs_task.run(limit=2)

    assert result == {
        "success": True,
        "scanned": 2,
        "reconciled": 0,
        "errors": 0,
    }
    assert len(visited) == 2


def test_stale_run_reconciliation_task_rotates_sorted_cursor(
    monkeypatch, tmp_path
):
    for simulation_id in ("sim-3", "sim-1", "sim-2"):
        (tmp_path / simulation_id).mkdir()
    visited = []
    monkeypatch.setattr(
        "app.tasks.simulation_tasks.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "reconcile_stale_run",
        lambda simulation_id: visited.append(simulation_id),
    )

    first = reconcile_stale_simulation_runs_task.run(limit=2)
    second = reconcile_stale_simulation_runs_task.run(limit=2)

    assert first["scanned"] == 2
    assert second["scanned"] == 2
    assert visited == ["sim-1", "sim-2", "sim-3", "sim-1"]
    assert (tmp_path / ".stale_run_reconcile_cursor.json").exists()


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

    def fake_apply_async(*, kwargs, task_id):
        captured_kwargs.update(kwargs)
        captured_kwargs["delivery_task_id"] = task_id
        return SimpleNamespace(id="celery-task-id-fake")

    monkeypatch.setattr(
        prepare_simulation_task,
        "apply_async",
        staticmethod(fake_apply_async),
    )

    # Patch the synchronous entity-count read so the test does not hit Zep.
    fake_state = SimpleNamespace(
        project_id="proj_x",
        graph_id="source-graph",
        entities_count=10,
        entity_types=["Student"],
        status=SimulationStatus.CREATED,
        error=None,
    )
    fake_prepare_info = {"already_prepared": False}
    # prep_routes did `from ..simulation import _check_simulation_prepared`, so
    # it holds its own reference; patching the name on app.api.simulation would
    # leave the route calling the real helper.
    monkeypatch.setattr(
        prep_routes, "_check_simulation_prepared", lambda sim_id: (False, fake_prepare_info)
    )
    monkeypatch.setattr(
        SimulationManager, "get_simulation", lambda self, sim_id: fake_state
    )
    monkeypatch.setattr(
        SimulationManager, "_save_simulation_state", lambda self, state: None
    )
    fake_project = SimpleNamespace(
        graph_id="source-graph",
        status="graph_completed",
        simulation_requirement="a decision",
    )
    monkeypatch.setattr(
        "app.api.routes.prep_routes.ProjectManager.get_project",
        lambda project_id: fake_project,
    )
    # Skip the synchronous entity count read. /prepare is served by
    # app.api.routes.prep_routes, which resolves ZepEntityReader from its own
    # module globals.
    class _FakeReader:
        def filter_defined_entities(self, **_):
            return SimpleNamespace(filtered_count=0, entity_types=[])
    monkeypatch.setattr(
        prep_routes, "ZepEntityReader", _FakeReader
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
def test_simulation_delivery_is_requeued_after_worker_loss():
    for task in (
        run_simulation_task,
        prepare_simulation_task,
        finalize_decision_lens_preparation_task,
        generate_ontology_task,
    ):
        assert task.acks_late is True
        assert task.reject_on_worker_lost is True
