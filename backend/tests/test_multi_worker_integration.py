"""
Multi-worker integration test suite verifying end-to-end simulation lifecycle:
1. Async simulation start (POST /api/simulation/start) returning HTTP 202 Accepted with task metadata.
2. Redis-backed task status polling (GET /api/simulation/<id>/status and /api/simulation/task/<task_id>/status).
3. Live Redis Pub/Sub scenario injection (POST /api/simulation/<id>/inject) consumed during tick execution.
4. Persistent per-simulation observation SQLite store operating in WAL mode post-completion.
5. Path traversal defense enforcement on file access endpoints.
6. Direct safe_join path containment verification rejecting invalid traversal inputs.
7. Configurable persistent storage path environment variable resolution.
8. Full end-to-end multi-worker simulation lifecycle integration.
"""

import importlib
import json
import os
import sqlite3
import tempfile
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
    observation_db_path,
    pop_in_memory_events,
    push_in_memory_event,
    record_injected_event,
    search_observations,
    sync_observation_store,
)
from app.services.simulation_runner import RunnerStatus, SimulationRunner, SimulationRunState
from app.services.simulation_runtime_contract import apply_injected_events
from app.tasks.simulation_tasks import run_simulation_task
from app.utils.safe_path import safe_join, SafePathError
from scripts.run_parallel_simulation import RedisEventConsumer


@pytest.fixture(autouse=True)
def configure_celery_eager(monkeypatch):
    """Enable Celery eager mode during integration tests."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


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


def test_live_pubsub_scenario_injection_during_tick(client, monkeypatch):
    """Verify scenario injection via Pub/Sub endpoint and consumption during tick execution."""
    sim_id = "sim_live_inject_tick_456"

    # Pin the transport. The /inject endpoint only falls back to the in-memory
    # queue when the Redis publish fails, and Config.REDIS_URL defaults to
    # redis://localhost:6379/0 -- so on a host with a reachable Redis this test
    # would publish to the real broker and the memory-transport consumer below
    # would see nothing.
    monkeypatch.setattr(Config, "REDIS_URL", "memory://")

    mock_state = MagicMock()
    mock_state.simulation_id = sim_id
    mock_state.status = "running"
    mock_state.config = {"name": "PubSub Simulation"}

    with patch("app.api.routes.execution_routes.SimulationManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.get_simulation.return_value = mock_state
        mock_mgr_cls.return_value = mock_mgr

        injection_payload = {
            "event_type": "breaking_news",
            "payload": {
                "headline": "Policy Revision Announced",
                "content": "Regulatory update impacts economic scenario parameters."
            }
        }

        # 1. Post live scenario injection to endpoint
        response = client.post(
            f"/api/simulation/{sim_id}/inject",
            json=injection_payload,
        )

        assert response.status_code == 200
        res_data = response.get_json()
        assert res_data["success"] is True
        assert res_data["channel"] == f"simulation:{sim_id}:events"
        assert res_data["event"]["event_type"] == "breaking_news"

        # 2. RedisEventConsumer consumes event during tick execution
        consumer = RedisEventConsumer(simulation_id=sim_id, redis_url="memory://")
        events = consumer.consume_events()

        assert len(events) >= 1
        matched = [e for e in events if e.get("event_type") == "breaking_news"]
        assert len(matched) == 1
        assert matched[0]["payload"]["headline"] == "Policy Revision Announced"


@pytest.mark.asyncio
async def test_persistent_observation_store_wal_mode_post_completion(tmp_path, monkeypatch):
    """Verify isolated per-simulation SQLite store operates in WAL mode and persists data post-completion."""
    sim_dir = str(tmp_path / "sim_wal_persistence_test")
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))

    # Initialize store
    db_path = ensure_observation_store(sim_dir)
    assert os.path.exists(db_path)

    # Confirm WAL mode on initialization
    conn_init = sqlite3.connect(db_path)
    cursor_init = conn_init.cursor()
    cursor_init.execute("PRAGMA journal_mode;")
    journal_mode_init = cursor_init.fetchone()[0]
    conn_init.close()
    assert journal_mode_init.lower() == "wal"

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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode;")
    mode_post = cursor.fetchone()[0]
    assert mode_post.lower() == "wal"

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


def test_multi_worker_e2e_simulation_lifecycle(client, tmp_path, monkeypatch):
    """Full end-to-end multi-worker integration test covering start -> status polling -> injection -> WAL persistence."""
    sim_id = "sim_e2e_multi_worker_lifecycle"
    sim_dir = str(tmp_path / sim_id)
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    # Force the in-memory event transport; see the note in
    # test_live_pubsub_scenario_injection_during_tick.
    monkeypatch.setattr(Config, "REDIS_URL", "memory://")

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

    monkeypatch.setattr(execution_routes, "SimulationManager", E2EManager)
    monkeypatch.setattr(execution_routes, "_check_simulation_prepared", lambda sid: (True, {}))
    monkeypatch.setattr(SimulationRunner, "start_simulation", lambda **kwargs: completed_run_state)
    monkeypatch.setattr(SimulationRunner, "get_run_state", lambda sid: completed_run_state)

    # Step 1: Start simulation asynchronously -> 202 Accepted
    start_resp = client.post("/api/simulation/start", json={"simulation_id": sim_id, "platform": "parallel"})
    assert start_resp.status_code == 202
    start_json = start_resp.get_json()
    task_id = start_json["task_id"]

    # Step 2: Poll status via TaskManager / status endpoint
    poll_resp = client.get(f"/api/simulation/task/{task_id}/status")
    assert poll_resp.status_code == 200
    assert poll_resp.get_json()["data"]["status"] in ("pending", "processing", "completed")

    # Step 3: Live scenario injection during tick
    inject_resp = client.post(f"/api/simulation/{sim_id}/inject", json={
        "event_type": "scenario_update",
        "payload": {"announcement": "E2E Injection Verified"}
    })
    assert inject_resp.status_code == 200
    assert pop_in_memory_events(sim_id)[0]["payload"]["announcement"] == "E2E Injection Verified"

    # Step 4: Verify post-completion SQLite WAL store persistence
    synced_db = sync_observation_store(sim_dir, run_state={"simulation_id": sim_id, "status": "completed"})
    conn = sqlite3.connect(synced_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    assert cursor.fetchone()[0].lower() == "wal"
    cursor.execute("SELECT count(*) FROM agent_index;")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_path_traversal_defense_on_file_access_endpoints(client):
    """Verify path traversal attempts return HTTP 400 or block traversal safely on file access endpoints."""
    traversal_attempts = [
        "../evil_sim",
        "../../etc/passwd",
        "..%252F..%252Fetc",
        "/etc/passwd",
        r"C:\Windows\System32",
    ]
    endpoints = [
        "/api/simulation/{id}/posts",
        "/api/simulation/{id}/comments",
        "/api/simulation/{id}/config/download",
    ]

    for bad_id in traversal_attempts:
        for endpoint_template in endpoints:
            url = endpoint_template.format(id=bad_id)
            response = client.get(url)
            # Response must NOT be 200 OK and must block traversal
            assert response.status_code != 200, f"Endpoint {url} returned HTTP 200 for traversal attempt '{bad_id}'"
            if response.status_code == 400:
                data = response.get_json()
                if data and isinstance(data, dict):
                    assert data.get("success") is False
                    assert data.get("error") in ("invalid_id", "invalid_path") or "error" in data


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


def test_configurable_persistent_storage_paths(monkeypatch, tmp_path):
    """Test environment variable overrides for UPLOAD_FOLDER and OASIS_SIMULATION_DATA_DIR in Config."""
    import app.config

    custom_upload = str(tmp_path / "custom_uploads_dir")
    custom_sim_data = str(tmp_path / "custom_simulations_dir")

    # 1. Test environment variable overrides via importlib reload
    monkeypatch.setenv("UPLOAD_FOLDER", custom_upload)
    monkeypatch.setenv("OASIS_SIMULATION_DATA_DIR", custom_sim_data)
    importlib.reload(app.config)

    assert app.config.Config.UPLOAD_FOLDER == custom_upload
    assert app.config.Config.OASIS_SIMULATION_DATA_DIR == custom_sim_data

    # 2. Test monkeypatch.setattr directly on Config
    override_upload = str(tmp_path / "override_upload")
    override_sim = str(tmp_path / "override_sim")
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", override_upload)
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", override_sim)

    assert Config.UPLOAD_FOLDER == override_upload
    assert Config.OASIS_SIMULATION_DATA_DIR == override_sim

    # 3. Clean up environment overrides and restore default config state
    monkeypatch.delenv("UPLOAD_FOLDER", raising=False)
    monkeypatch.delenv("OASIS_SIMULATION_DATA_DIR", raising=False)
    importlib.reload(app.config)

