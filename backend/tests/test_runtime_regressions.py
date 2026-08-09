"""Regression coverage for runtime defects found during the July 2026 audit."""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

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
from app.services.run_attempt_store import RunAttemptHeld, RunAttemptStore
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


def test_load_run_state_is_pure_for_active_persisted_state(monkeypatch, tmp_path):
    simulation_id = "sim-pure-load"
    simulation_dir = tmp_path / simulation_id
    simulation_dir.mkdir()
    state_path = simulation_dir / "run_state.json"
    persisted = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id="attempt-1",
        owner_id="worker-1",
        fencing_token=7,
        heartbeat_at="2026-08-08T00:00:00+00:00",
    ).to_detail_dict()
    state_path.write_text(json.dumps(persisted, indent=2), encoding="utf-8")
    before = state_path.read_bytes()
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        classmethod(lambda _cls, _simulation_id: str(simulation_dir)),
    )

    loaded = SimulationRunner._load_run_state(simulation_id)

    assert loaded.runner_status == RunnerStatus.RUNNING
    assert loaded.attempt_id == "attempt-1"
    assert loaded.owner_id == "worker-1"
    assert loaded.fencing_token == 7
    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    ("platform", "platform_args"),
    [
        ("twitter", ["--twitter-only"]),
        ("reddit", ["--reddit-only"]),
        ("parallel", []),
    ],
)
def test_runtime_command_builder_uses_one_production_engine(
    tmp_path,
    platform,
    platform_args,
):
    script_path = str(tmp_path / "run_parallel_simulation.py")
    config_path = str(tmp_path / "simulation_config.json")

    command = SimulationRunner.build_runtime_command(
        script_path,
        config_path,
        platform,
        max_rounds=7,
    )

    assert command == [
        sys.executable,
        script_path,
        "--config",
        config_path,
        *platform_args,
        "--max-rounds",
        "7",
    ]
    assert "--no-wait" not in command


def test_runtime_command_builder_rejects_invalid_platform_and_legacy_script(tmp_path):
    config_path = str(tmp_path / "simulation_config.json")
    parallel_script = str(tmp_path / "run_parallel_simulation.py")

    with pytest.raises(ValueError, match="Unsupported simulation platform"):
        SimulationRunner.build_runtime_command(
            parallel_script,
            config_path,
            "mastodon",
            max_rounds=None,
        )

    with pytest.raises(ValueError, match="run_parallel_simulation.py"):
        SimulationRunner.build_runtime_command(
            str(tmp_path / "run_twitter_simulation.py"),
            config_path,
            "twitter",
            max_rounds=None,
        )


@pytest.mark.parametrize("platform", ["twitter", "reddit", "parallel"])
def test_start_simulation_selects_parallel_runtime_for_every_platform(
    monkeypatch,
    tmp_path,
    platform,
):
    simulation_id = f"sim-runtime-{platform}"
    (tmp_path / "simulation_config.json").write_text(
        json.dumps(
            {
                "time_config": {
                    "total_simulation_hours": 1,
                    "minutes_per_round": 40,
                }
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def capture_command(script_path, config_path, selected_platform, max_rounds):
        captured.update(
            script_path=script_path,
            config_path=config_path,
            platform=selected_platform,
            max_rounds=max_rounds,
        )
        raise RuntimeError("runtime command captured")

    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", RunAttemptStore())
    monkeypatch.setattr(SimulationRunner, "_run_states", {})
    monkeypatch.setattr(SimulationRunner, "_processes", {})
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "build_runtime_command",
        staticmethod(capture_command),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: None,
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "run_preflight",
        lambda _simulation_dir: {"status": "passed"},
    )

    with pytest.raises(RuntimeError, match="runtime command captured"):
        SimulationRunner.start_simulation(
            simulation_id,
            platform=platform,
            max_rounds=None,
            owner_id=f"worker-{platform}",
        )

    assert os.path.basename(captured["script_path"]) == "run_parallel_simulation.py"
    assert captured["config_path"] == str(tmp_path / "simulation_config.json")
    assert captured["platform"] == platform
    assert captured["max_rounds"] is None
    assert SimulationRunner._run_states[simulation_id].total_rounds == 2


def test_get_run_state_always_prefers_durable_state_over_cached_reference(
    monkeypatch, tmp_path
):
    simulation_id = "sim-durable-first"
    durable = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.COMPLETED,
        current_round=4,
        total_rounds=4,
    )
    cached = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        current_round=1,
        total_rounds=4,
    )
    (tmp_path / "run_state.json").write_text(
        json.dumps(durable.to_detail_dict()), encoding="utf-8"
    )
    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: cached})
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )

    loaded = SimulationRunner.get_run_state(simulation_id)

    assert loaded.runner_status == RunnerStatus.COMPLETED
    assert loaded.current_round == 4
    assert SimulationRunner._run_states[simulation_id] is cached


def test_get_run_state_does_not_create_process_local_control_reference(
    monkeypatch, tmp_path
):
    simulation_id = "sim-durable-read-only"
    durable = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
    )
    (tmp_path / "run_state.json").write_text(
        json.dumps(durable.to_detail_dict()), encoding="utf-8"
    )
    control_references = {}
    monkeypatch.setattr(SimulationRunner, "_run_states", control_references)
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )

    loaded = SimulationRunner.get_run_state(simulation_id)

    assert loaded.runner_status == RunnerStatus.RUNNING
    assert control_references == {}


def test_get_run_state_preserves_control_reference_used_by_stop(monkeypatch, tmp_path):
    simulation_id = "sim-durable-stop-reference"
    durable = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        current_round=7,
    )
    control = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        current_round=1,
    )

    class LiveProcess:
        pid = 123
        returncode = None

        def __init__(self):
            self.running = True

        def poll(self):
            return None if self.running else self.returncode

    process = LiveProcess()
    (tmp_path / "run_state.json").write_text(
        json.dumps(durable.to_detail_dict()), encoding="utf-8"
    )
    saved_statuses = []
    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: control})
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "_save_run_state",
        classmethod(
            lambda _cls, state: saved_statuses.append(state.runner_status)
        ),
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
        lambda _path, run_state: None,
    )

    snapshot = SimulationRunner.get_run_state(simulation_id)
    stopped = SimulationRunner.stop_simulation(simulation_id)

    assert snapshot.current_round == 7
    assert stopped is control
    assert control.runner_status == RunnerStatus.STOPPED
    assert process.poll() == -15
    assert saved_statuses == [RunnerStatus.STOPPING, RunnerStatus.STOPPED]


def test_get_run_state_preserves_control_reference_used_by_monitor(
    monkeypatch, tmp_path
):
    simulation_id = "sim-durable-monitor-reference"
    durable = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        current_round=7,
    )
    control = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.STOPPING,
        current_round=1,
    )
    process = SimpleNamespace(poll=lambda: -15, returncode=-15)
    (tmp_path / "run_state.json").write_text(
        json.dumps(durable.to_detail_dict()), encoding="utf-8"
    )
    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: control})
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "_save_run_state",
        classmethod(lambda _cls, _state: None),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda _path, run_state: None,
    )

    snapshot = SimulationRunner.get_run_state(simulation_id)
    monitored = SimulationRunner._monitor_simulation(simulation_id)

    assert snapshot.current_round == 7
    assert monitored is control
    assert control.runner_status == RunnerStatus.STOPPED
    assert control.error is None


def test_reconcile_stale_run_interrupts_without_inspecting_processes(
    monkeypatch, tmp_path
):
    simulation_id = "sim-stale-reconcile"
    simulation_dir = tmp_path / simulation_id
    simulation_dir.mkdir()
    store = RunAttemptStore()
    attempt = store.acquire(str(simulation_dir), simulation_id, "worker-1", 30)
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id=attempt.attempt_id,
        owner_id=attempt.owner_id,
        fencing_token=attempt.fencing_token,
        heartbeat_at=attempt.heartbeat_at,
    )
    (simulation_dir / "run_state.json").write_text(
        json.dumps(state.to_detail_dict()), encoding="utf-8"
    )
    attempt_path = simulation_dir / "run_attempt.json"
    attempt_data = json.loads(attempt_path.read_text("utf-8"))
    attempt_data["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    attempt_path.write_text(json.dumps(attempt_data), encoding="utf-8")

    class ProcessAccessForbidden(dict):
        def get(self, *_args, **_kwargs):
            raise AssertionError("reconciliation inspected process-local state")

    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", store)
    monkeypatch.setattr(SimulationRunner, "_processes", ProcessAccessForbidden())
    monkeypatch.setattr(
        SimulationRunner,
        "_get_run_state_dir",
        classmethod(lambda _cls, _simulation_id: str(simulation_dir)),
    )

    reconciled = SimulationRunner.reconcile_stale_run(simulation_id)

    assert reconciled.runner_status == RunnerStatus.INTERRUPTED
    assert reconciled.error == "run-attempt heartbeat expired"
    persisted = json.loads((simulation_dir / "run_state.json").read_text("utf-8"))
    assert persisted["runner_status"] == RunnerStatus.INTERRUPTED.value


def test_monitor_heartbeats_state_then_releases_terminal_attempt(
    monkeypatch, tmp_path
):
    simulation_id = "sim-monitor-lease"
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), simulation_id, "worker-1", 30)
    initial_heartbeat = attempt.heartbeat_at
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id=attempt.attempt_id,
        owner_id=attempt.owner_id,
        fencing_token=attempt.fencing_token,
        heartbeat_at=attempt.heartbeat_at,
    )

    class FakeProcess:
        returncode = 0

        def __init__(self):
            self.poll_count = 0

        def poll(self):
            self.poll_count += 1
            return None if self.poll_count == 1 else 0

    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", store)
    monkeypatch.setattr(SimulationRunner, "_run_states", {simulation_id: state})
    monkeypatch.setattr(
        SimulationRunner, "_processes", {simulation_id: FakeProcess()}
    )
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(simulation_runner_module.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda _path, run_state: None,
    )

    monitored = SimulationRunner._monitor_simulation(simulation_id)

    terminal_attempt = store.read(str(tmp_path))
    assert monitored.runner_status == RunnerStatus.COMPLETED
    assert monitored.heartbeat_at >= initial_heartbeat
    assert terminal_attempt.status == RunnerStatus.COMPLETED.value


def test_monitor_does_not_release_attempt_when_terminal_state_save_fails(
    monkeypatch, tmp_path
):
    simulation_id = "sim-terminal-save-fails"
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id="attempt-1",
        owner_id="worker-1",
        fencing_token=1,
    )
    releases = []

    class FakeStore:
        def heartbeat(self, *_args):
            return SimpleNamespace(heartbeat_at="2026-08-08T00:00:00+00:00")

        def release(self, *args):
            releases.append(args)

    process = SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", FakeStore())
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner,
        "_save_run_state",
        classmethod(lambda _cls, _state: (_ for _ in ()).throw(OSError("disk full"))),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda *_args, **_kwargs: None,
    )

    SimulationRunner._monitor_simulation(simulation_id)

    assert releases == []


def test_monitor_releases_after_terminal_save_when_projection_fails(
    monkeypatch, tmp_path
):
    simulation_id = "sim-projection-fails"
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id="attempt-1",
        owner_id="worker-1",
        fencing_token=1,
    )
    releases = []

    class FakeStore:
        def heartbeat(self, *_args):
            return SimpleNamespace(heartbeat_at="2026-08-08T00:00:00+00:00")

        def release(self, *args):
            releases.append(args)

    process = SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", FakeStore())
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        SimulationRunner, "_save_run_state", classmethod(lambda _cls, _state: None)
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("projection failed")),
    )

    SimulationRunner._monitor_simulation(simulation_id)

    assert len(releases) == 1


def test_monitor_terminates_child_after_losing_heartbeat_ownership(
    monkeypatch, tmp_path
):
    simulation_id = "sim-monitor-stale-owner"
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), simulation_id, "worker-1", 30)
    attempt_path = tmp_path / "run_attempt.json"
    attempt_data = json.loads(attempt_path.read_text("utf-8"))
    attempt_data["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    attempt_path.write_text(json.dumps(attempt_data), encoding="utf-8")
    state = SimulationRunState(
        simulation_id=simulation_id,
        runner_status=RunnerStatus.RUNNING,
        attempt_id=attempt.attempt_id,
        owner_id=attempt.owner_id,
        fencing_token=attempt.fencing_token,
        heartbeat_at=attempt.heartbeat_at,
    )

    class FakeProcess:
        returncode = None
        terminated = False

        def poll(self):
            return -15 if self.terminated else None

    process = FakeProcess()
    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", store)
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "sync_observation_store",
        lambda _path, run_state: None,
    )

    def terminate(fake_process, _simulation_id, timeout=10):
        fake_process.terminated = True

    monkeypatch.setattr(
        SimulationRunner, "_terminate_process", staticmethod(terminate)
    )

    monitored = SimulationRunner._monitor_simulation(simulation_id)

    assert process.terminated is True
    assert monitored.runner_status == RunnerStatus.INTERRUPTED
    assert monitored.error == "run-attempt heartbeat expired"
    assert simulation_id not in SimulationRunner._processes


def test_startup_failure_terminates_child_before_releasing_attempt(
    monkeypatch, tmp_path
):
    simulation_id = "sim-startup-failure"
    (tmp_path / "simulation_config.json").write_text(
        json.dumps(
            {
                "time_config": {
                    "total_simulation_hours": 1,
                    "minutes_per_round": 30,
                }
            }
        ),
        encoding="utf-8",
    )
    store = RunAttemptStore()

    class FakeProcess:
        pid = 4321
        terminated = False

        def poll(self):
            return -15 if self.terminated else None

    process = FakeProcess()

    class BrokenMonitorThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            raise RuntimeError("monitor thread failed to start")

    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", store)
    monkeypatch.setattr(SimulationRunner, "_run_states", {})
    monkeypatch.setattr(SimulationRunner, "_processes", {})
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: None,
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "run_preflight",
        lambda _simulation_dir: {"status": "passed"},
    )
    monkeypatch.setattr(simulation_runner_module.subprocess, "Popen", lambda *_a, **_k: process)
    monkeypatch.setattr(simulation_runner_module.threading, "Thread", BrokenMonitorThread)

    def terminate(fake_process, _simulation_id, timeout=10):
        fake_process.terminated = True

    monkeypatch.setattr(SimulationRunner, "_terminate_process", staticmethod(terminate))

    with pytest.raises(RuntimeError, match="monitor thread failed to start"):
        SimulationRunner.start_simulation(simulation_id, owner_id="worker-1")

    assert process.terminated is True
    assert store.read(str(tmp_path)).status == RunnerStatus.FAILED.value
    assert simulation_id not in SimulationRunner._processes


def test_startup_failure_heartbeats_ownership_until_child_exits(
    monkeypatch, tmp_path
):
    simulation_id = "sim-startup-child-alive"
    (tmp_path / "simulation_config.json").write_text(
        json.dumps(
            {
                "time_config": {
                    "total_simulation_hours": 1,
                    "minutes_per_round": 30,
                }
            }
        ),
        encoding="utf-8",
    )
    store = RunAttemptStore()

    spawned = threading.Event()

    class DelayedExitProcess:
        pid = 9876
        returncode = None

        def __init__(self):
            self.started_at = None

        def poll(self):
            if self.started_at is None:
                return None
            if time.monotonic() - self.started_at >= 0.8:
                self.returncode = -9
                return self.returncode
            return None

    process = DelayedExitProcess()

    class BrokenMonitorThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            raise RuntimeError("monitor thread failed to start")

    monkeypatch.setattr(SimulationRunner, "_run_attempt_store", store)
    monkeypatch.setattr(SimulationRunner, "_run_attempt_ttl_seconds", 0.2)
    monkeypatch.setattr(SimulationRunner, "_run_states", {})
    monkeypatch.setattr(SimulationRunner, "_processes", {})
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
        classmethod(lambda _cls, _simulation_id: str(tmp_path)),
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: None,
    )
    monkeypatch.setattr(
        simulation_runner_module,
        "run_preflight",
        lambda _simulation_dir: {"status": "passed"},
    )
    def spawn(*_args, **_kwargs):
        process.started_at = time.monotonic()
        spawned.set()
        return process

    monkeypatch.setattr(simulation_runner_module.subprocess, "Popen", spawn)
    monkeypatch.setattr(
        simulation_runner_module,
        "threading",
        SimpleNamespace(Thread=BrokenMonitorThread),
    )
    termination_calls = []

    def fail_termination(*_args, **_kwargs):
        termination_calls.append(time.monotonic())
        raise OSError("alive")

    monkeypatch.setattr(
        SimulationRunner,
        "_terminate_process",
        staticmethod(fail_termination),
    )

    errors = []

    def start():
        try:
            SimulationRunner.start_simulation(simulation_id, owner_id="worker-1")
        except BaseException as exc:
            errors.append(exc)

    starter = threading.Thread(target=start, daemon=True)
    starter.start()
    assert spawned.wait(timeout=1)

    try:
        time.sleep(0.45)
        assert process.poll() is None
        with pytest.raises(RunAttemptHeld):
            store.acquire(str(tmp_path), simulation_id, "worker-2", 0.2)
    finally:
        starter.join(timeout=2)
        handle = SimulationRunner._stdout_files.get(simulation_id)
        if handle:
            handle.close()

    assert not starter.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "monitor thread failed to start"
    assert termination_calls
    assert store.read(str(tmp_path)).status == RunnerStatus.FAILED.value
    assert simulation_id not in SimulationRunner._processes


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

