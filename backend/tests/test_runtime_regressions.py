"""Regression coverage for runtime defects found during the July 2026 audit."""

import json
import os

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from flask import Flask

from app.api import graph as graph_api
from app.api import simulation as simulation_api
from app.api.routes import execution_routes
from app.services.graph_builder import GraphBuilderService
from app.services.oasis_profile_generator import OasisProfileGenerator
from app.services.simulation_config_generator import SimulationConfigGenerator
from app.services import simulation_runner as simulation_runner_module
from app.services.simulation_runner import (
    RunnerStatus,
    SimulationRunState,
    SimulationRunner,
)
from app.services.zep_entity_reader import EntityNode
from scripts.run_parallel_simulation import ParallelIPCHandler


def _entity(
    *,
    name: str = "Alice",
    entity_type: str = "Person",
    summary: str = "Community participant",
) -> EntityNode:
    return EntityNode(
        uuid=f"entity-{name.lower()}",
        name=name,
        labels=["Entity", entity_type],
        summary=summary,
        attributes={},
    )


def test_simulation_config_context_uses_restored_entity_summary():
    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)

    context = generator._build_context(
        "Understand public response",
        "Source document",
        [_entity()],
    )

    assert "### Person (1 total)" in context
    assert "- Alice: Community participant" in context


def test_simulation_config_llm_retry_forwards_prompts_and_parses_json():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"ok": true}'),
                    finish_reason="stop",
                )
            ]
        )

    def mock_chat_json(messages, temperature=None, complexity=None):
        calls.append({"messages": messages, "temperature": temperature, "complexity": complexity})
        return {"ok": True}

    generator = SimulationConfigGenerator.__new__(SimulationConfigGenerator)
    generator.model_name = "test-model"
    generator.client = SimpleNamespace(
        chat_json=mock_chat_json
    )

    result = generator._call_llm_with_retry("user prompt", "system prompt")

    assert result == {"ok": True}
    assert calls[0]["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]


def test_graph_wait_reports_elapsed_time_without_name_error():
    service = GraphBuilderService.__new__(GraphBuilderService)
    service.client = SimpleNamespace(
        graph=SimpleNamespace(
            episode=SimpleNamespace(
                get=lambda **_: SimpleNamespace(processed=True)
            )
        )
    )
    progress_messages = []

    service._wait_for_episodes(
        ["episode-1"],
        lambda message, progress: progress_messages.append((message, progress)),
    )

    assert any("Zep processing..." in message for message, _ in progress_messages)
    assert progress_messages[-1] == ("Processing complete: 1/1", 1.0)


def test_parallel_ipc_polls_oldest_command_and_removes_completed_command(tmp_path):
    handler = ParallelIPCHandler(str(tmp_path))
    older = tmp_path / "ipc_commands" / "older.json"
    newer = tmp_path / "ipc_commands" / "newer.json"
    older.write_text(json.dumps({"command_id": "older"}), encoding="utf-8")
    newer.write_text(json.dumps({"command_id": "newer"}), encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert handler.poll_command() == {"command_id": "older"}

    handler.send_response("older", "success", {"answer": 42})

    assert not older.exists()
    response = json.loads(
        (tmp_path / "ipc_responses" / "older.json").read_text(encoding="utf-8")
    )
    assert response["result"] == {"answer": 42}


def test_unknown_entity_type_gets_rule_based_fallback_profile():
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)
    generator.MBTI_TYPES = ["INTJ"]
    generator.COUNTRIES = ["United States"]

    profile = generator._generate_profile_rule_based(
        "Neighborhood Council",
        "CommunityGroup",
        "A local civic group.",
        {},
    )

    assert profile["bio"] == "Fictional scenario account based on the role: CommunityGroup."
    assert profile["profession"] == "CommunityGroup"


def test_task_list_route_accepts_task_manager_serialized_dtos(monkeypatch):
    class FakeTaskManager:
        def list_tasks(self):
            return [{"task_id": "task-1", "status": "pending"}]

    monkeypatch.setattr(graph_api, "TaskManager", FakeTaskManager)
    app = Flask(__name__)

    with app.app_context():
        response = graph_api.list_tasks()

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["data"][0]["task_id"] == "task-1"
    # Truth contract metadata (Gate 1)
    assert payload["human_respondent_count"] == 0
    assert payload["output_origin"] == "synthetic"
    assert payload["is_forecast"] is False
    assert "generated_at" in payload


def test_stop_simulation_terminates_runtime_and_releases_resources(
    monkeypatch,
    tmp_path,
):
    class FakeProcess:
        pid = 123

        def __init__(self):
            self.running = True
            self.returncode = None

        def poll(self):
            return None if self.running else self.returncode

    class FakeHandle:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    simulation_id = "sim-stop"
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        twitter_running=True,
        reddit_running=True,
    )
    process = FakeProcess()
    stdout = FakeHandle()
    persisted = []
    observed = []

    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: state})
    monkeypatch.setattr(SimulationRunner, "_processes", {simulation_id: process})
    monkeypatch.setattr(SimulationRunner, "_monitor_threads", {})
    monkeypatch.setattr(SimulationRunner, "_action_queues", {simulation_id: object()})
    monkeypatch.setattr(SimulationRunner, "_stdout_files", {simulation_id: stdout})
    monkeypatch.setattr(SimulationRunner, "_stderr_files", {})
    monkeypatch.setattr(SimulationRunner, "_graph_memory_enabled", {})
    monkeypatch.setattr(SimulationRunner, "_follower_engines", {})
    monkeypatch.setattr(SimulationRunner, "_follower_agents", {})
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        staticmethod(lambda _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "_save_run_state",
        staticmethod(lambda saved_state: persisted.append(saved_state.runner_status)),
    )

    def terminate(fake_process, _simulation_id):
        fake_process.running = False
        fake_process.returncode = -15

    monkeypatch.setattr(
        SimulationRunner,
        "_terminate_process",
        staticmethod(terminate),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda _path, run_state: observed.append(run_state["runner_status"]),
    )

    stopped = SimulationRunner.stop_simulation(simulation_id)

    assert stopped.runner_status == RunnerStatus.STOPPED
    assert stopped.twitter_running is False
    assert stopped.reddit_running is False
    assert stopped.completed_at
    assert persisted == [RunnerStatus.STOPPING, RunnerStatus.STOPPED]
    assert observed == [RunnerStatus.STOPPED.value]
    assert simulation_id not in SimulationRunner._processes
    assert simulation_id not in SimulationRunner._action_queues
    assert stdout.closed is True


def test_monitor_preserves_intentional_stop_for_nonzero_exit(
    monkeypatch,
    tmp_path,
):
    simulation_id = "sim-monitor-stop"
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.STOPPING,
        twitter_running=True,
    )
    process = SimpleNamespace(poll=lambda: -15, returncode=-15)

    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: state})
    monkeypatch.setattr(SimulationRunner, "_processes", {simulation_id: process})
    monkeypatch.setattr(SimulationRunner, "_monitor_threads", {})
    monkeypatch.setattr(SimulationRunner, "_action_queues", {})
    monkeypatch.setattr(SimulationRunner, "_stdout_files", {})
    monkeypatch.setattr(SimulationRunner, "_stderr_files", {})
    monkeypatch.setattr(SimulationRunner, "_graph_memory_enabled", {})
    monkeypatch.setattr(SimulationRunner, "_follower_engines", {})
    monkeypatch.setattr(SimulationRunner, "_follower_agents", {})
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        staticmethod(lambda _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "_save_run_state",
        staticmethod(lambda _state: None),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda _path, run_state: None,
    )

    monitored = SimulationRunner._monitor_simulation(simulation_id)

    assert monitored.runner_status == RunnerStatus.STOPPED
    assert monitored.error is None
    assert monitored.twitter_running is False
    assert monitored.completed_at


def test_live_injection_returns_pubsub_contract(monkeypatch):
    app = Flask(__name__)

    mock_state = SimpleNamespace(simulation_id="sim-1", status="running", config={})
    mock_mgr = MagicMock()
    mock_mgr.get_simulation.return_value = mock_state
    # execution_routes owns the registered /<id>/inject handler; the copy in
    # api/simulation.py is undecorated and never serves a request.
    monkeypatch.setattr(execution_routes, "SimulationManager", lambda: mock_mgr)

    with app.test_request_context(
        json={"content": "Breaking update", "platform": "parallel"}
    ):
        response = execution_routes.inject_simulation_event("sim-1")

    body, status = response
    assert status == 200
    payload = body.get_json()
    assert payload["success"] is True
    assert payload["simulation_id"] == "sim-1"
    assert payload["channel"] == "simulation:sim-1:events"


def test_saved_run_summary_exposes_resume_contract(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="sim-1",
        project_id="project-1",
        to_dict=lambda: {
            "simulation_id": "sim-1",
            "project_id": "project-1",
            "status": "completed",
            "created_at": "2026-07-20T10:00:00",
            "updated_at": "2026-07-20T11:00:00",
        },
    )
    manager = SimpleNamespace(
        get_simulation_config=lambda _simulation_id: {
            "simulation_requirement": "What could change if service is reduced?",
            "time_config": {
                "total_simulation_hours": 4,
                "minutes_per_round": 30,
            },
        }
    )
    project = SimpleNamespace(
        name="Weekend service",
        simulation_requirement="Fallback requirement",
        files=[{"filename": "brief.pdf"}, {"filename": "notes.md"}],
    )
    run_state = SimpleNamespace(
        current_round=8,
        total_rounds=8,
        runner_status=SimpleNamespace(value="completed"),
    )

    monkeypatch.setattr(
        simulation_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_run_state",
        lambda _simulation_id: run_state,
    )
    monkeypatch.setattr(
        simulation_api,
        "_get_report_summary_for_simulation",
        lambda _simulation_id: {
            "report_id": "report-1",
            "status": "completed",
        },
    )

    summary = simulation_api._enrich_simulation_summary(simulation, manager)

    assert summary["simulation_requirement"] == (
        "What could change if service is reduced?"
    )
    assert summary["runner_status"] == "completed"
    assert summary["report_id"] == "report-1"
    assert summary["report_status"] == "completed"
    assert summary["workflow_step"] == 4
    assert summary["resume_target"] == "report"
    assert summary["total_rounds"] == 8


def test_running_saved_run_summary_resumes_run_without_report(monkeypatch):
    simulation = SimpleNamespace(
        simulation_id="sim-2",
        project_id="project-2",
        to_dict=lambda: {
            "simulation_id": "sim-2",
            "project_id": "project-2",
            "status": "running",
            "created_at": "2026-07-20T10:00:00",
            "updated_at": "2026-07-20T11:00:00",
        },
    )
    manager = SimpleNamespace(get_simulation_config=lambda _simulation_id: {})
    project = SimpleNamespace(
        name="Open run",
        simulation_requirement="Trace this running scenario",
        files=[],
    )
    run_state = SimpleNamespace(
        current_round=3,
        total_rounds=12,
        runner_status=SimpleNamespace(value="running"),
    )

    monkeypatch.setattr(
        simulation_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_run_state",
        lambda _simulation_id: run_state,
    )
    monkeypatch.setattr(
        simulation_api,
        "_get_report_summary_for_simulation",
        lambda _simulation_id: None,
    )

    summary = simulation_api._enrich_simulation_summary(simulation, manager)

    assert summary["simulation_requirement"] == "Trace this running scenario"
    assert summary["runner_status"] == "running"
    assert summary["report_id"] is None
    assert summary["workflow_step"] == 3
    assert summary["resume_target"] == "run"


# --------------------------------------------------------------------------- #
# P1 state-semantics regression: stop and close-env must persist a status that
# agrees with the runner result (audit §5 P1 "Contradictory lifecycle
# semantics"). The bugs: /stop set PAUSED while the runner reported STOPPED;
# /close-env set COMPLETED even when the close failed.
# --------------------------------------------------------------------------- #


@pytest.fixture
def execution_client(monkeypatch):
    """Minimal Flask app exposing the execution routes, with auth disabled."""
    from app import create_app
    from app.config import Config

    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _persisted_state_factory(status):
    """A mutable stand-in for a SimulationState that the route can mutate + save."""
    return SimpleNamespace(status=status)


def test_stop_route_persists_stopped_not_paused(execution_client, monkeypatch):
    """/stop must persist SimulationStatus.STOPPED when the runner reports
    STOPPED — not PAUSED (audit P1). Regression: the old code set PAUSED."""
    from app.services.simulation_manager import SimulationManager, SimulationStatus
    from app.services.simulation_runner import RunnerStatus

    stopped_run_state = SimpleNamespace(
        runner_status=RunnerStatus.STOPPED,
        to_dict=lambda: {"runner_status": "stopped"},
    )
    monkeypatch.setattr(
        execution_routes.SimulationRunner,
        "stop_simulation",
        lambda simulation_id: stopped_run_state,
    )

    persisted = {"status": None}
    fake_state = _persisted_state_factory(SimulationStatus.RUNNING)

    def fake_save(self, state):
        persisted["status"] = state.status

    monkeypatch.setattr(SimulationManager, "get_simulation", lambda self, sid: fake_state)
    monkeypatch.setattr(SimulationManager, "_save_simulation_state", fake_save)

    resp = execution_client.post(
        "/api/simulation/stop", json={"simulation_id": "sim_stop_p1"}
    )
    assert resp.status_code == 200
    assert persisted["status"] == SimulationStatus.STOPPED
    assert persisted["status"] != SimulationStatus.PAUSED


def test_close_env_route_does_not_mark_completed_on_failure(execution_client, monkeypatch):
    """/close-env must NOT set COMPLETED when close_simulation_env reports
    failure (audit P1). Regression: the old code set COMPLETED unconditionally."""
    from app.services.simulation_manager import SimulationManager, SimulationStatus

    monkeypatch.setattr(
        execution_routes.SimulationRunner,
        "close_simulation_env",
        lambda simulation_id, timeout: {"success": False, "error": "timeout"},
    )

    persisted = {"status": None}
    # The run was STOPPED before the close attempt; a failed close must leave it.
    fake_state = _persisted_state_factory(SimulationStatus.STOPPED)

    def fake_save(self, state):
        persisted["status"] = state.status

    monkeypatch.setattr(SimulationManager, "get_simulation", lambda self, sid: fake_state)
    monkeypatch.setattr(SimulationManager, "_save_simulation_state", fake_save)

    resp = execution_client.post(
        "/api/simulation/close-env", json={"simulation_id": "sim_close_fail"}
    )
    assert resp.status_code == 200
    # The persisted status was never upgraded to COMPLETED.
    assert persisted["status"] is None  # save was never called
    assert fake_state.status == SimulationStatus.STOPPED


def test_close_env_route_marks_completed_on_success(execution_client, monkeypatch):
    """Positive control: a successful close DOES set COMPLETED."""
    from app.services.simulation_manager import SimulationManager, SimulationStatus

    monkeypatch.setattr(
        execution_routes.SimulationRunner,
        "close_simulation_env",
        lambda simulation_id, timeout: {"success": True},
    )

    persisted = {"status": None}
    fake_state = _persisted_state_factory(SimulationStatus.RUNNING)

    def fake_save(self, state):
        persisted["status"] = state.status

    monkeypatch.setattr(SimulationManager, "get_simulation", lambda self, sid: fake_state)
    monkeypatch.setattr(SimulationManager, "_save_simulation_state", fake_save)

    resp = execution_client.post(
        "/api/simulation/close-env", json={"simulation_id": "sim_close_ok"}
    )
    assert resp.status_code == 200
    assert persisted["status"] == SimulationStatus.COMPLETED

