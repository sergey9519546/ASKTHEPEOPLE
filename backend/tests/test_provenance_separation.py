import json
from types import SimpleNamespace

import pytest
from flask import Flask

from app.api.routes import execution_routes
from app.api.simulation import _resolve_graph_memory_request
from app.config import Config
from app.services.report_agent import ReportAgent
from app.services.simulation_manager import SimulationStatus
from app.services.simulation_runner import SimulationRunner
from app.services.zep_graph_memory_updater import (
    AgentActivity,
    ZepGraphMemoryManager,
)
from app.services.zep_tools import InsightForgeResult, PanoramaResult, SearchResult


def test_graph_memory_request_is_off_and_requires_a_json_boolean():
    assert _resolve_graph_memory_request({}, source_graph_id="source-graph") == (
        False,
        None,
    )
    assert _resolve_graph_memory_request(
        {"enable_graph_memory_update": False},
        source_graph_id="source-graph",
    ) == (False, None)

    with pytest.raises(ValueError, match="JSON boolean"):
        _resolve_graph_memory_request(
            {"enable_graph_memory_update": "false"},
            source_graph_id="source-graph",
        )


def test_graph_memory_request_is_always_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        _resolve_graph_memory_request(
            {
                "enable_graph_memory_update": True,
                "synthetic_graph_id": "source-graph",
            },
            source_graph_id="source-graph",
        )

    with pytest.raises(ValueError, match="observation store"):
        _resolve_graph_memory_request(
            {
                "enable_graph_memory_update": True,
                "synthetic_graph_id": "separate-synthetic-graph",
            },
            source_graph_id=None,
        )


def test_graph_memory_request_cannot_be_enabled_with_a_separate_target():
    with pytest.raises(ValueError, match="observation store"):
        _resolve_graph_memory_request(
            {
                "enable_graph_memory_update": True,
                "synthetic_graph_id": "separate-synthetic-graph",
            },
            source_graph_id="source-graph",
        )


def test_start_route_defaults_to_observation_store_without_graph_write(monkeypatch):
    captured = {}
    state = SimpleNamespace(
        status=SimulationStatus.READY,
        graph_id="source-graph",
        project_id="project-1",
    )

    class FakeManager:
        def get_simulation(self, simulation_id):
            assert simulation_id == "sim-1"
            return state

        def _save_simulation_state(self, saved_state):
            assert saved_state is state

    class FakeTaskManager:
        def create_task(self, **_kwargs):
            return "task-1"

    def capture_dispatch(**kwargs):
        captured.update(kwargs)

    # execution_routes owns the registered /start handler. api/simulation.py
    # still carries an undecorated copy of the same body; asserting against
    # that one would prove nothing about what the API actually serves.
    monkeypatch.setattr(execution_routes, "SimulationManager", FakeManager)
    monkeypatch.setattr(
        execution_routes,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: {},
    )
    monkeypatch.setattr("app.models.task.TaskManager", FakeTaskManager)
    monkeypatch.setattr(
        "app.tasks.simulation_tasks.run_simulation_task.apply_async",
        capture_dispatch,
    )
    app = Flask(__name__)

    with app.test_request_context(
        json={"simulation_id": "sim-1", "platform": "parallel"}
    ):
        response = execution_routes.start_simulation()

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["graph_memory_update_enabled"] is False
    assert payload["data"]["observation_storage"] == "simulation_observation_store"
    assert payload["data"]["source_graph_mutated"] is False
    assert captured["task_id"] == "task-1"
    assert captured["kwargs"]["task_id"] == "task-1"
    assert captured["kwargs"]["enable_graph_memory_update"] is False
    assert captured["kwargs"]["graph_id"] is None
    assert captured["kwargs"]["source_graph_id"] == "source-graph"


def test_invalid_graph_write_request_has_no_force_restart_side_effects(monkeypatch):
    state = SimpleNamespace(
        status=SimulationStatus.RUNNING,
        graph_id="source-graph",
        project_id="project-1",
    )

    class FakeManager:
        def get_simulation(self, _simulation_id):
            return state

    class NoSideEffectRunner:
        @staticmethod
        def get_run_state(_simulation_id):
            raise AssertionError("run state must not be inspected")

        @staticmethod
        def stop_simulation(_simulation_id):
            raise AssertionError("simulation must not be stopped")

        @staticmethod
        def cleanup_simulation_logs(_simulation_id):
            raise AssertionError("logs must not be removed")

    monkeypatch.setattr(execution_routes, "SimulationManager", FakeManager)
    monkeypatch.setattr(execution_routes, "SimulationRunner", NoSideEffectRunner)
    monkeypatch.setattr(
        execution_routes,
        "assert_decision_lens_execution_admission",
        lambda _simulation_dir: {},
    )
    app = Flask(__name__)

    with app.test_request_context(
        json={
            "simulation_id": "sim-1",
            "platform": "parallel",
            "force": True,
            "enable_graph_memory_update": True,
            "synthetic_graph_id": "separate-synthetic-graph",
        }
    ):
        response, status = execution_routes.start_simulation()

    assert status == 400
    assert "observation store" in response.get_json()["error"]


def test_runner_rejects_all_graph_writes_even_when_called_outside_api(
    monkeypatch, tmp_path
):
    simulation_dir = tmp_path / "sim-1"
    simulation_dir.mkdir()
    (simulation_dir / "simulation_config.json").write_text(
        "{}",
        encoding="utf-8",
    )
    # Run-state resolution reads Config, not a class attribute — patching
    # SimulationRunner.RUN_STATE_DIR here would leave the runner writing into
    # the real uploads directory if the guard below ever moved.
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    assert SimulationRunner._get_run_state_dir("sim-1").startswith(
        str(tmp_path.resolve())
    ), "test isolation is not in effect"

    with pytest.raises(ValueError, match="unsupported"):
        SimulationRunner.start_simulation(
            "sim-1",
            enable_graph_memory_update=True,
            graph_id="source-graph",
            source_graph_id="source-graph",
        )


def test_updater_is_unavailable_without_a_capability():
    with pytest.raises(PermissionError, match="unsupported"):
        ZepGraphMemoryManager.create_updater("sim-1", "synthetic-graph")


def test_updater_is_unavailable_even_with_legacy_capability():
    with pytest.raises(PermissionError, match="unsupported"):
        ZepGraphMemoryManager.create_updater(
            "sim-1",
            "source-graph",
            source_graph_id="source-graph",
            allow_graph_mutation=True,
        )


def test_experimental_episode_is_indelibly_labeled_synthetic():
    activity = AgentActivity(
        platform="twitter",
        agent_id=7,
        agent_name="Generated profile 7",
        action_type="CREATE_POST",
        action_args={"content": "A possible path"},
        round_num=3,
        timestamp="2026-07-29T00:00:00Z",
    )

    episode = activity.to_episode_text()

    assert episode.startswith("[GENERATED_SIMULATION_OBSERVATION;")
    assert "HUMAN_RESPONDENTS=0" in episode
    assert "A possible path" in episode


def test_report_retrieves_generated_activity_from_observation_store(
    monkeypatch, tmp_path
):
    simulation_dir = tmp_path / "sim-1" / "twitter"
    simulation_dir.mkdir(parents=True)
    (simulation_dir / "actions.jsonl").write_text(
        json.dumps(
            {
                "round": 1,
                "agent_id": 7,
                "agent_name": "Generated profile 7",
                "action_type": "CREATE_POST",
                "action_args": {"content": "Weekend service might shift trips."},
                "timestamp": "2026-07-29T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))

    agent = ReportAgent(
        graph_id="source-graph",
        simulation_id="sim-1",
        simulation_requirement="Explore weekend service paths",
        llm_client=SimpleNamespace(),
        zep_tools=SimpleNamespace(),
    )

    result = agent._execute_tool(
        "simulation_observations",
        {"query": "Weekend service", "limit": 10},
    )

    assert "PROVENANCE: GENERATED_OBSERVATION" in result
    assert '"evidence_class": "synthetic_observation"' in result
    assert '"human_respondents": 0' in result
    assert "Weekend service might shift trips." in result


def test_graph_retrieval_is_never_presented_as_verified_source():
    class GraphTools:
        def quick_search(self, **_kwargs):
            return SimpleNamespace(to_text=lambda: "Retrieved graph record")

    agent = ReportAgent(
        graph_id="possibly-mixed-graph",
        simulation_id="sim-1",
        simulation_requirement="Explore a path",
        llm_client=SimpleNamespace(),
        zep_tools=GraphTools(),
    )

    result = agent._execute_tool("quick_search", {"query": "record"})

    assert "GRAPH_RECORD_ORIGIN_UNVERIFIED" in result
    assert "supplied-source facts" in result
    assert "SOURCE_GRAPH_RECORD" not in result


def test_graph_tool_text_does_not_upgrade_records_to_facts():
    quick = SearchResult(
        facts=["A retrieved claim"],
        edges=[],
        nodes=[],
        query="claim",
        total_count=1,
    ).to_text()
    insight = InsightForgeResult(
        query="claim",
        simulation_requirement="scenario",
        sub_queries=[],
        semantic_facts=["A retrieved claim"],
        total_facts=1,
    ).to_text()
    panorama = PanoramaResult(
        query="claim",
        active_facts=["A retrieved claim"],
        historical_facts=["An older claim"],
        active_count=1,
        historical_count=1,
    ).to_text()

    combined = "\n".join((quick, insight, panorama))
    assert "Origin Unverified" in combined
    assert "Relevant Facts" not in combined
    assert "Key Facts" not in combined
    assert "Simulation Result Originals" not in combined
