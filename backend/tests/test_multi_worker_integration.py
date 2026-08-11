"""
Multi-worker integration test suite verifying end-to-end simulation lifecycle:
1. Async simulation start (POST /api/simulation/start) returning HTTP 202 Accepted with task metadata.
2. Redis-backed task status polling (GET /api/simulation/<id>/status and /api/simulation/task/<task_id>/status).
3. Durable scenario controls claimed exactly once across independent workers.
4. Persistent per-simulation observation SQLite store operating in WAL mode post-completion.
5. Path traversal defense enforcement on file access endpoints.
6. Direct safe_join path containment verification rejecting invalid traversal inputs.
7. Configurable persistent storage path environment variable resolution.
8. Full end-to-end multi-worker simulation lifecycle integration.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app import create_app
from app.api.routes import execution_routes
from app.celery_app import celery_app
from app.config import Config
from app.models.task import Task, TaskManager, TaskStatus
from app.services.simulation_artifacts import canonical_agents_path
from app.services.simulation_manager import SimulationManager, SimulationStatus
from app.services.simulation_observation_store import (
    ensure_observation_store,
    get_observation_db_journal_mode,
    observation_db_path,
    record_injected_event,
    search_observations,
    sync_observation_store,
)
from app.services.run_attempt_store import RunAttemptStore
from app.services.runtime_control_store import RuntimeControlStore
from app.services.simulation_runner import RunnerStatus, SimulationRunner, SimulationRunState
from app.tasks.simulation_tasks import run_simulation_task
from app.utils.safe_path import safe_join, SafePathError


@pytest.fixture(autouse=True)
def configure_celery_eager(monkeypatch):
    """Enable Celery eager mode during integration tests."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setattr(
        execution_routes,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: {},
    )


@pytest.fixture(autouse=True)
def isolate_simulation_storage(monkeypatch, tmp_path):
    """Point every storage resolver at tmp_path for the whole module.

    These tests drive real routes and the eager Celery task, and several code
    paths (SimulationManager.__init__, ensure_observation_store) create
    directories as a side effect. Without this the suite writes simulation
    directories into the repository's own backend/uploads/simulations.
    """
    storage_root = tmp_path / "simulations"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(storage_root))
    return storage_root


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_generated_run_instructions_use_the_unified_production_engine():
    run_instructions = SimulationManager().get_run_instructions(
        "sim_unified_runtime_instructions"
    )
    commands = run_instructions["commands"]
    parallel_command = (
        f'python "{os.path.join(run_instructions["scripts_dir"], "run_parallel_simulation.py")}" '
        f'--config "{run_instructions["config_file"]}"'
    )

    assert commands["twitter"] == f"{parallel_command} --twitter-only"
    assert commands["reddit"] == f"{parallel_command} --reddit-only"
    assert commands["parallel"] == parallel_command
    assert "run_twitter_simulation.py" not in run_instructions["instructions"]
    assert "run_reddit_simulation.py" not in run_instructions["instructions"]


def test_async_simulation_start_returns_202_accepted(client, monkeypatch):
    """Verify POST /api/simulation/start dispatches asynchronously and returns HTTP 202 Accepted."""
    sim_id = "sim_integration_start_202"

    state = SimpleNamespace(
        simulation_id=sim_id,
        status=SimulationStatus.READY,
        graph_id="test-graph-202",
        config={"name": "Integration Simulation"},
    )

    class FakeManager:
        def get_simulation(self, sid):
            return state if sid == sim_id else None

        def _save_simulation_state(self, saved_state):
            pass

    dummy_run_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.COMPLETED,
        total_rounds=3,
        current_round=3,
    )

    monkeypatch.setattr(execution_routes, "SimulationManager", FakeManager)
    monkeypatch.setattr(execution_routes, "_check_simulation_prepared", lambda sid: (True, {}))
    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: dummy_run_state)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sid: dummy_run_state)

    response = client.post(
        "/api/simulation/start",
        json={"simulation_id": sim_id, "platform": "parallel"},
    )

    assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}"
    data = response.get_json()
    assert data["success"] is True
    assert data["simulation_id"] == sim_id
    assert data["status"] == "queued"
    assert "task_id" in data
    assert data["message"] == "Simulation execution queued."


def test_redis_backed_task_status_polling(client):
    """Verify task status polling via GET /api/simulation/<id>/status and task ID endpoint."""
    sim_id = "sim_integration_poll_123"
    tm = TaskManager()

    task_id = tm.create_task("simulation_run", metadata={"simulation_id": sim_id})
    tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=45, message="Running round 3 of 10")

    # Poll via task ID endpoint
    resp_task = client.get(f"/api/simulation/task/{task_id}/status")
    assert resp_task.status_code == 200
    task_data = resp_task.get_json()
    assert task_data["success"] is True
    assert task_data["data"]["task_id"] == task_id
    assert task_data["data"]["status"] == "processing"
    assert task_data["data"]["progress"] == 45

    # Poll via simulation ID endpoint
    resp_sim = client.get(f"/api/simulation/{sim_id}/status")
    assert resp_sim.status_code == 200
    sim_data = resp_sim.get_json()
    assert sim_data["success"] is True
    assert sim_data["simulation_id"] == sim_id
    assert sim_data["task_id"] == task_id
    assert sim_data["status"] == "processing"
    assert sim_data["progress"] == 45

    # Update task to completed
    tm.complete_task(task_id, result={"summary": "Simulation completed successfully"})
    resp_completed = client.get(f"/api/simulation/task/{task_id}/status")
    assert resp_completed.status_code == 200
    completed_data = resp_completed.get_json()
    assert completed_data["data"]["status"] == "completed"
    assert completed_data["data"]["progress"] == 100


def test_durable_injection_is_claimed_once_across_workers(
    client,
    isolate_simulation_storage,
    monkeypatch,
):
    sim_id = "sim_durable_inject_tick_456"
    sim_dir = isolate_simulation_storage / sim_id
    sim_dir.mkdir()
    attempt = RunAttemptStore().acquire(
        str(sim_dir),
        sim_id,
        "worker-owner",
        30,
    )
    simulation = SimpleNamespace(simulation_id=sim_id, status="running")
    run_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.RUNNING,
        twitter_running=True,
        active_platforms=["twitter"],
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
    )
    monkeypatch.setattr(
        execution_routes.SimulationManager,
        "get_simulation",
        lambda _self, requested_id: simulation if requested_id == sim_id else None,
    )
    monkeypatch.setattr(
        SimulationRunner,
        "get_run_state",
        lambda requested_id: run_state if requested_id == sim_id else None,
    )

    response = client.post(
        f"/api/simulation/{sim_id}/inject",
        json={
            "event_type": "breaking_news",
            "payload": {"headline": "Policy revision announced"},
            "platforms": ["twitter"],
        },
    )

    assert response.status_code == 202
    control_id = response.get_json()["data"]["control_id"]
    stores = [
        RuntimeControlStore(
            str(sim_dir),
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
        )
        for _ in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as executor:
        claimed = list(executor.map(lambda store: store.claim_next("twitter"), stores))

    commands = [command for command in claimed if command is not None]
    assert len(commands) == 1
    assert commands[0]["control_id"] == control_id
    stores[0].write_platform_state(
        "twitter",
        {"status": "running", "last_control_id": control_id},
    )
    stores[0].complete(
        "twitter",
        commands[0],
        {"applied_count": 1, "round_num": 0},
    )

    status_response = client.get(
        f"/api/simulation/{sim_id}/control/{control_id}"
    )
    assert status_response.status_code == 200
    assert status_response.get_json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_persistent_observation_store_wal_mode_post_completion(isolate_simulation_storage):
    """Verify isolated per-simulation SQLite store operates in WAL mode and persists data post-completion."""
    sim_dir = str(isolate_simulation_storage / "sim_wal_persistence_test")

    # Initialize store
    db_path = ensure_observation_store(sim_dir)
    assert os.path.exists(db_path)

    # Confirm WAL mode on initialization, via the production helper
    assert get_observation_db_journal_mode(sim_dir) == "wal"

    # Populate canonical agents and simulation artifacts
    agents_file = os.path.join(sim_dir, "agent_profiles.canonical.json")
    canonical_agents = [
        {
            "agent_id": 0,
            "display_name": "Citizen_Alpha",
            "source_entity_uuid": "uuid-001",
            "source_entity_type_normalized": "citizen",
            "activity_seed": {"platform_preference": "both"},
        },
        {
            "agent_id": 1,
            "display_name": "Citizen_Beta",
            "source_entity_uuid": "uuid-002",
            "source_entity_type_normalized": "official",
            "activity_seed": {"platform_preference": "twitter"},
        },
    ]
    with open(agents_file, "w", encoding="utf-8") as f:
        json.dump(canonical_agents, f)

    # Record actions and injected events
    actions_dir = os.path.join(sim_dir, "twitter")
    os.makedirs(actions_dir, exist_ok=True)
    actions_file = os.path.join(actions_dir, "actions.jsonl")
    with open(actions_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "event_type": "round_start",
            "round": 1,
            "simulated_hour": 10,
            "timestamp": "2026-07-29T10:00:00Z"
        }) + "\n")
        f.write(json.dumps({
            "round": 1,
            "agent_id": 0,
            "agent_name": "Citizen_Alpha",
            "action_type": "CREATE_POST",
            "action_args": {"content": "First post in WAL test"},
            "timestamp": "2026-07-29T10:05:00Z"
        }) + "\n")

    record_injected_event(
        simulation_dir=sim_dir,
        platform="twitter",
        round_num=1,
        event_type="breaking_news",
        payload={"content": "Event recorded in WAL mode"},
        timestamp="2026-07-29T10:06:00Z"
    )

    # Sync observation store upon simulation completion
    run_state_dict = {
        "simulation_id": "sim_wal_persistence_test",
        "status": "completed",
        "rounds": [{"round_num": 1, "summary": "Round 1 finished cleanly"}],
    }
    synced_db_path = sync_observation_store(sim_dir, run_state=run_state_dict)
    assert synced_db_path == db_path

    # Verify persistent SQLite data in WAL mode post-completion
    assert get_observation_db_journal_mode(sim_dir) == "wal"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM agent_index;")
    assert cursor.fetchone()[0] == 2

    cursor.execute("SELECT agent_name, action_type, action_args_json FROM actions WHERE platform='twitter';")
    action_rows = cursor.fetchall()
    assert len(action_rows) == 1
    assert action_rows[0][0] == "Citizen_Alpha"
    assert action_rows[0][1] == "CREATE_POST"
    assert "First post in WAL test" in action_rows[0][2]

    cursor.execute("SELECT event_type, payload_json FROM injected_events;")
    injected_rows = cursor.fetchall()
    assert len(injected_rows) == 1
    assert injected_rows[0][0] == "breaking_news"
    assert "Event recorded in WAL mode" in injected_rows[0][1]

    cursor.execute("SELECT payload_json FROM round_summaries WHERE round_num=1;")
    summary_rows = cursor.fetchall()
    assert len(summary_rows) == 1
    assert "Round 1 finished cleanly" in summary_rows[0][0]

    conn.close()

    # Search helper verification
    search_res = search_observations(sim_dir, query="First post")
    assert search_res["count"] >= 1
    assert search_res["results"][0]["agent_name"] == "Citizen_Alpha"


def test_multi_worker_e2e_simulation_lifecycle(client, isolate_simulation_storage, monkeypatch):
    """Full end-to-end multi-worker integration test covering start -> status polling -> injection -> WAL persistence."""
    sim_id = "sim_e2e_multi_worker_lifecycle"
    sim_dir = str(isolate_simulation_storage / sim_id)

    # Pre-create simulation dir and canonical agents
    os.makedirs(sim_dir, exist_ok=True)
    canonical_agents = [{
        "agent_id": 0,
        "display_name": "E2E_Agent",
        "source_entity_uuid": "uuid-e2e",
        "source_entity_type_normalized": "resident",
        "activity_seed": {"platform_preference": "both"},
    }]
    with open(canonical_agents_path(sim_dir), "w", encoding="utf-8") as f:
        json.dump(canonical_agents, f)

    state = SimpleNamespace(
        simulation_id=sim_id,
        status=SimulationStatus.READY,
        graph_id="e2e-graph",
        config={"name": "E2E Integration Test"},
    )

    class E2EManager:
        def get_simulation(self, sid):
            return state if sid == sim_id else None

        def _save_simulation_state(self, saved_state):
            pass

    completed_run_state = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.COMPLETED,
        total_rounds=1,
        current_round=1,
    )
    current_run_state = {"value": completed_run_state}

    monkeypatch.setattr(execution_routes, "SimulationManager", E2EManager)
    monkeypatch.setattr(execution_routes, "_check_simulation_prepared", lambda sid: (True, {}))
    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: completed_run_state)
    monkeypatch.setattr(
        SimulationRunner,
        "get_run_state",
        lambda sid: current_run_state["value"],
    )

    # Step 1: Start simulation asynchronously -> 202 Accepted
    start_resp = client.post("/api/simulation/start", json={"simulation_id": sim_id, "platform": "parallel"})
    assert start_resp.status_code == 202
    start_json = start_resp.get_json()
    task_id = start_json["task_id"]

    # Step 2: Poll status via TaskManager / status endpoint
    poll_resp = client.get(f"/api/simulation/task/{task_id}/status")
    assert poll_resp.status_code == 200
    assert poll_resp.get_json()["data"]["status"] in ("pending", "processing", "completed")

    # Step 3: Durable scenario injection during an owned active attempt
    attempt = RunAttemptStore().acquire(
        sim_dir,
        sim_id,
        "worker-e2e",
        30,
    )
    current_run_state["value"] = SimulationRunState(
        simulation_id=sim_id,
        runner_status=RunnerStatus.RUNNING,
        twitter_running=True,
        active_platforms=["twitter"],
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
    )
    inject_resp = client.post(f"/api/simulation/{sim_id}/inject", json={
        "event_type": "media_breaking_news",
        "payload": {"summary": "E2E injection verified"},
        "platforms": ["twitter"],
    })
    assert inject_resp.status_code == 202
    control_id = inject_resp.get_json()["data"]["control_id"]
    durable_status = RuntimeControlStore(sim_dir).get_status(control_id)
    assert durable_status["status"] == "queued"
    assert durable_status["args"]["payload"]["summary"] == "E2E injection verified"

    # Step 4: Verify post-completion SQLite WAL store persistence
    synced_db = sync_observation_store(sim_dir, run_state={"simulation_id": sim_id, "status": "completed"})
    assert get_observation_db_journal_mode(sim_dir) == "wal"
    conn = sqlite3.connect(synced_db)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM agent_index;")
    assert cursor.fetchone()[0] == 1
    conn.close()


FILE_ACCESS_ENDPOINTS = [
    "/api/simulation/{id}/posts",
    "/api/simulation/{id}/comments",
    "/api/simulation/{id}/config/download",
]


def test_path_traversal_defense_on_file_access_endpoints(client):
    """Traversal ids that reach the handler must be rejected by safe_join, specifically.

    `status != 200` is not an adequate assertion here: a routing 404 or an
    unhandled 500 would both satisfy it while proving nothing about the
    defense. These ids survive URL routing as a single path segment, so the
    handler runs and safe_join is what produces the 400.
    """
    handler_reaching_ids = [
        "..%252F..%252Fetc",
        r"C:\Windows\System32",
        "..",
    ]

    for bad_id in handler_reaching_ids:
        for endpoint_template in FILE_ACCESS_ENDPOINTS:
            url = endpoint_template.format(id=bad_id)
            response = client.get(url)
            assert response.status_code == 400, (
                f"{url} returned {response.status_code}, expected 400 from the "
                f"safe_join rejection for id {bad_id!r}"
            )
            data = response.get_json()
            assert data["success"] is False
            assert data["error"] == "invalid_id"


def test_traversal_rejection_is_the_defense_not_a_blanket_4xx(client):
    """A well-formed id must reach the database lookup rather than being rejected.

    Without this, the assertions above would still pass if the endpoints
    rejected every request. This is what makes the 400 above attributable to
    safe_join: same endpoint, same absent database, different id, different
    status.
    """
    for endpoint_template in FILE_ACCESS_ENDPOINTS:
        url = endpoint_template.format(id="sim_well_formed_but_absent")
        response = client.get(url)
        assert response.status_code != 400, (
            f"{url} rejected a legitimate simulation id; the traversal test "
            f"above would then pass for the wrong reason"
        )


def test_multi_segment_traversal_ids_are_stopped_by_routing(client):
    """Ids containing separators never reach the handler; document that.

    These produce paths that match no URL rule, so Werkzeug answers 404 before
    any application code runs. They are worth keeping as a regression guard on
    the URL map, but they exercise routing, not safe_join.
    """
    # Note the last one: a single-encoded %2F decodes to a separator before
    # routing, so it becomes a multi-segment path too. Only the
    # double-encoded %252F survives as one segment (covered above).
    routing_stopped_ids = [
        "../evil_sim",
        "../../etc/passwd",
        "/etc/passwd",
        "sim..%2F..%2Fetc",
    ]

    for bad_id in routing_stopped_ids:
        for endpoint_template in FILE_ACCESS_ENDPOINTS:
            url = endpoint_template.format(id=bad_id)
            response = client.get(url)
            assert response.status_code == 404, (
                f"{url} returned {response.status_code}; expected a routing 404"
            )


def test_safe_join_rejects_path_traversal_attempts():
    """Direct test of safe_join() / app.utils.safe_path rejecting invalid traversal inputs."""
    with tempfile.TemporaryDirectory(prefix="safe_join_test_") as base_dir:
        # Legitimate subpath succeeds
        valid_res = safe_join(base_dir, "valid_sim_123")
        assert valid_res == os.path.realpath(os.path.join(base_dir, "valid_sim_123"))

        # Invalid traversal inputs raise SafePathError
        invalid_inputs = [
            "../outside",
            "../../etc/passwd",
            "/etc/passwd",
            r"C:\Windows\System32",
            "",
            None,
            "sim\x00null",
            "folder/subfolder",
            "..",
        ]
        for invalid_input in invalid_inputs:
            with pytest.raises(SafePathError):
                safe_join(base_dir, invalid_input)


def _config_values_under_env(env_overrides):
    """Import app.config in a clean subprocess and read back two paths.

    Module-level env reads can only be re-exercised by a fresh interpreter.
    importlib.reload() in-process would rebind app.config.Config to a new class
    that no already-imported service holds a reference to, so asserting on it
    would only prove that os.environ.get works.
    """
    env = dict(os.environ, **env_overrides)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.config as c;"
            "print(c.Config.UPLOAD_FOLDER);"
            "print(c.Config.OASIS_SIMULATION_DATA_DIR)",
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    upload, sim_data = result.stdout.strip().splitlines()[-2:]
    return upload, sim_data


def test_storage_env_vars_are_read_and_simulation_dir_follows_upload_folder(tmp_path):
    """UPLOAD_FOLDER alone must relocate simulation state; the specific var still wins."""
    custom_upload = str(tmp_path / "custom_uploads_dir")
    custom_sim_data = str(tmp_path / "custom_simulations_dir")

    # UPLOAD_FOLDER alone relocates simulation run-state with it. Without this,
    # an operator moving uploads to a persistent volume silently leaves every
    # simulation directory on the ephemeral default.
    upload, sim_data = _config_values_under_env({"UPLOAD_FOLDER": custom_upload})
    assert upload == custom_upload
    assert sim_data == os.path.join(custom_upload, "simulations")

    # The specific variable still overrides the derived default.
    upload, sim_data = _config_values_under_env(
        {"UPLOAD_FOLDER": custom_upload, "OASIS_SIMULATION_DATA_DIR": custom_sim_data}
    )
    assert upload == custom_upload
    assert sim_data == custom_sim_data


def test_every_storage_resolver_honours_the_configured_directory(monkeypatch, tmp_path):
    """Each independent path resolver must read Config, not a hardcoded default."""
    from app.api.simulation import _safe_sim_dir

    custom = tmp_path / "relocated_simulations"
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(custom))
    expected_root = os.path.realpath(str(custom))

    assert SimulationRunner._get_run_state_dir("sim_x").startswith(expected_root)
    assert _safe_sim_dir("sim_x").startswith(expected_root)

    # Constructing the manager must create the *configured* root, not a
    # repo-relative one — on a read-only image the latter raises OSError and
    # takes every simulation route down with it.
    manager = SimulationManager()
    assert os.path.isdir(str(custom))
    assert manager._get_simulation_dir("sim_x").startswith(expected_root)

