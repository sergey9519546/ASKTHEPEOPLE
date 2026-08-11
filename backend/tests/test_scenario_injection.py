import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

import pytest

from app import create_app
from app.services.simulation_observation_store import (
    ensure_observation_store,
)
from app.services.simulation_runtime_contract import (
    apply_injected_events,
    apply_runtime_control,
)
from app.services.simulation_runner import RunnerStatus


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_inject_endpoint_returns_202_and_enqueues_durable_control(client):
    """The compatibility endpoint delegates to the durable control queue."""
    simulation_id = "sim_test_inject_200"

    mock_state = MagicMock()
    mock_state.simulation_id = simulation_id
    mock_state.status = "running"
    mock_state.config = {"name": "Test Simulation"}

    active_run = MagicMock()
    active_run.runner_status = RunnerStatus.RUNNING
    active_run.twitter_running = True
    active_run.reddit_running = True
    active_run.active_platforms = ["twitter", "reddit"]
    active_run.attempt_id = "attempt-current"
    active_run.fencing_token = 7

    with (
        patch("app.api.routes.execution_routes.SimulationManager") as mock_mgr_cls,
        patch(
            "app.api.routes.execution_routes.SimulationRunner.get_run_state",
            return_value=active_run,
        ),
        patch(
            "app.services.simulation_observation_store.push_in_memory_event",
            side_effect=AssertionError("in-memory fallback must not be used"),
        ),
        patch("app.api.routes.execution_routes.RuntimeControlStore", create=True) as store_cls,
    ):
        mock_mgr = MagicMock()
        mock_mgr.get_simulation.return_value = mock_state
        mock_mgr_cls.return_value = mock_mgr
        store_cls.return_value.enqueue.return_value = {
            "control_id": "control-123",
            "command_type": "inject_event",
            "status": "queued",
            "platforms": ["twitter", "reddit"],
        }

        payload = {
            "event_type": "breaking_news",
            "payload": {
                "content": "Major announcement alters current simulation topic dynamics."
            }
        }

        response = client.post(
            f"/api/simulation/{simulation_id}/inject",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 202, response.get_data(as_text=True)
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["control_id"] == "control-123"
        assert data["data"]["status"] == "queued"
        store_cls.return_value.enqueue.assert_called_once_with(
            "inject_event",
            {
                "event_type": "media_breaking_news",
                "payload": {
                    "content": "Major announcement alters current simulation topic dynamics.",
                },
                "targeting": {},
                "reason": None,
            },
            ["twitter", "reddit"],
            idempotency_key=None,
        )


def test_inject_endpoint_returns_404_for_missing_simulation(client):
    """Test that POST /api/simulation/<id>/inject returns HTTP 404 for non-existent simulation."""
    simulation_id = "sim_non_existent"

    with patch("app.api.routes.execution_routes.SimulationManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.get_simulation.return_value = None
        mock_mgr_cls.return_value = mock_mgr

        response = client.post(
            f"/api/simulation/{simulation_id}/inject",
            data=json.dumps({
                "event_type": "breaking_news",
                "payload": {"content": "A valid event"},
            }),
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Simulation does not exist" in data["error"]


@pytest.mark.parametrize(
    "event_type",
    [
        "persona_modification",
        "persona_change",
        "dynamic_instruction",
        "inject_post",
    ],
)
def test_compatibility_inject_rejects_instruction_and_command_variants(
    client,
    event_type,
):
    response = client.post(
        "/api/simulation/sim-reject-event/inject",
        json={
            "event_type": event_type,
            "payload": {"content": "Untrusted event content"},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_apply_injected_events_record_and_execute():
    """Test apply_injected_events writes to jsonl, records in DB, and applies OASIS actions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation_dir = tmp_dir
        platform = "twitter"
        current_round = 3

        db_path = ensure_observation_store(simulation_dir)

        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_agent.system_message = MagicMock()
        mock_agent.system_message.content = "Base system prompt."
        mock_env.agent_graph.get_agents.return_value = [(1, mock_agent)]
        mock_env.agent_graph.get_agent.return_value = mock_agent
        mock_env.step = AsyncMock()

        config = {"agents": [{"agent_id": 1}], "time_config": {}}
        agent_names = {1: "Agent_1"}

        injected_events = [
            {
                "event_type": "breaking_news",
                "payload": {"content": "Breaking: Market surges by 10%!"},
                "timestamp": "2026-07-29T16:10:00Z"
            },
            {
                "event_type": "persona_modification",
                "payload": {"agent_id": 1, "instruction": "Focus on high-growth technology stocks."},
                "timestamp": "2026-07-29T16:11:00Z"
            }
        ]

        with patch("app.services.simulation_runtime_contract._apply_specs") as mock_apply_specs:
            mock_apply_specs.return_value = 1

            applied_count = await apply_injected_events(
                env=mock_env,
                simulation_dir=simulation_dir,
                config=config,
                platform=platform,
                current_round=current_round,
                events=injected_events,
                agent_names=agent_names,
                manual_action_cls=MagicMock(),
                action_type_cls=MagicMock(),
                action_logger=None,
            )

            assert applied_count == 2
            assert mock_apply_specs.call_count == 1
            assert mock_agent.system_message.content == "Base system prompt."
            mock_agent.set_round_context_overlay.assert_called_once()
            overlay = mock_agent.set_round_context_overlay.call_args.args[0]
            assert "Focus on high-growth technology stocks." in overlay
            mock_env.step.assert_awaited_once()
            actions = mock_env.step.await_args.args[0]
            assert list(actions) == [mock_agent]
            assert actions[mock_agent].__class__.__name__ == "LLMAction"

        injected_jsonl = os.path.join(simulation_dir, "injected_events.jsonl")
        assert os.path.exists(injected_jsonl)
        with open(injected_jsonl, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 2
        assert lines[0]["event_type"] == "breaking_news"
        assert lines[1]["event_type"] == "persona_modification"

        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT round_num, event_type, payload_json FROM injected_events ORDER BY id ASC")
        db_rows = cursor.fetchall()
        conn.close()

        assert len(db_rows) == 2
        assert db_rows[0][0] == 3
        assert db_rows[0][1] == "breaking_news"
        assert "Market surges" in db_rows[0][2]
        assert db_rows[1][1] == "persona_modification"

        intervention_payload = json.loads(db_rows[1][2])
        assert intervention_payload["_intervention"]["status"] == "applied"
        assert intervention_payload["_intervention"]["requested_agent_ids"] == [1]
        assert intervention_payload["_intervention"]["resolved_agent_ids"] == [1]
        assert intervention_payload["_intervention"]["applied_agent_ids"] == [1]
        assert intervention_payload["_intervention"]["applied_target_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command_type", "args"),
    [
        (
            "inject_post",
            {"content": "Targeted notice", "agent_id": 999},
        ),
        (
            "inject_event",
            {
                "event_type": "seed_post",
                "payload": {"content": "Targeted event"},
                "targeting": {"poster_agent_id": 999},
            },
        ),
    ],
)
async def test_runtime_control_explicit_unknown_id_never_falls_back(
    tmp_path,
    command_type,
    args,
):
    agent = MagicMock()
    env = MagicMock()
    env.agent_graph.get_agent.side_effect = lambda agent_id: {
        4: agent,
    }[agent_id]
    env.step = AsyncMock()

    result = await apply_runtime_control(
        env=env,
        simulation_dir=str(tmp_path),
        config={
            "agent_configs": [
                {
                    "agent_id": 4,
                    "platform_preference": "twitter",
                    "influence_weight": 1.0,
                }
            ]
        },
        platform="twitter",
        command_type=command_type,
        args=args,
        agent_names={4: "Agent_4"},
        manual_action_cls=MagicMock(),
        action_type_cls=SimpleNamespace(CREATE_POST="CREATE_POST"),
        round_num=0,
    )

    assert result["applied_count"] == 0
    env.step.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_type",
    ["persona_modification", "persona_change", "dynamic_instruction"],
)
async def test_apply_injected_events_applies_supported_persona_variants(event_type):
    """Variant persona events should trigger one-shot model actions for targets."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation_dir = tmp_dir
        platform = "twitter"
        current_round = 5

        ensure_observation_store(simulation_dir)

        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_agent.system_message = MagicMock()
        mock_env.agent_graph.get_agents.return_value = [(7, mock_agent)]
        mock_env.agent_graph.get_agent.return_value = mock_agent
        mock_env.step = AsyncMock()

        config = {
            "agents": [{"agent_id": 7, "platform_preference": "twitter", "normalized_role": "student"}],
            "time_config": {},
        }
        agent_names = {7: "Agent_7"}

        injected_events = [
            {
                "event_type": event_type,
                "payload": {
                    "agent_id": 7,
                    "instruction": "Use a more conversational tone for this simulation phase.",
                },
                "timestamp": "2026-07-29T16:15:00Z",
            }
        ]

        with patch("app.services.simulation_runtime_contract._apply_specs") as mock_apply_specs:
            mock_apply_specs.return_value = 1

            applied_count = await apply_injected_events(
                env=mock_env,
                simulation_dir=simulation_dir,
                config=config,
                platform=platform,
                current_round=current_round,
                events=injected_events,
                agent_names=agent_names,
                manual_action_cls=MagicMock(),
                action_type_cls=MagicMock(),
                action_logger=None,
            )

            assert applied_count == 1
            assert mock_apply_specs.call_count == 0
            mock_agent.set_round_context_overlay.assert_called_once()
            mock_env.step.assert_awaited_once()
            actions = mock_env.step.await_args.args[0]
            assert list(actions) == [mock_agent]
            assert actions[mock_agent].__class__.__name__ == "LLMAction"


@pytest.mark.asyncio
async def test_apply_injected_events_rejects_blank_persona_instruction():
    """Blank persona instructions should be rejected without a model action."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation_dir = tmp_dir
        platform = "twitter"
        current_round = 2

        ensure_observation_store(simulation_dir)

        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_env.agent_graph.get_agents.return_value = [(3, mock_agent)]
        mock_env.agent_graph.get_agent.return_value = mock_agent

        config = {
            "agents": [{"agent_id": 3, "platform_preference": "twitter", "normalized_role": "student"}],
            "time_config": {},
        }
        agent_names = {3: "Agent_3"}

        injected_events = [
            {
                "event_type": "persona_change",
                "payload": {"agent_id": 3, "instruction": "   "},
                "timestamp": "2026-07-29T16:16:00Z",
            }
        ]

        with patch("app.services.simulation_runtime_contract._apply_specs") as mock_apply_specs:
            applied_count = await apply_injected_events(
                env=mock_env,
                simulation_dir=simulation_dir,
                config=config,
                platform=platform,
                current_round=current_round,
                events=injected_events,
                agent_names=agent_names,
                manual_action_cls=MagicMock(),
                action_type_cls=MagicMock(),
                action_logger=None,
            )

            assert applied_count == 1
            assert mock_apply_specs.call_count == 0

        import sqlite3

        conn = sqlite3.connect(os.path.join(simulation_dir, "simulation_observations.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT payload_json FROM injected_events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        payload = json.loads(row[0])
        assert payload["_intervention"]["status"] == "rejected"
        assert payload["_intervention"]["reason"] == "No instruction content provided."


@pytest.mark.asyncio
async def test_apply_injected_events_rejects_agent_without_runtime_overlay_support():
    """Resolved legacy agents must not be reported as behaviorally modified."""
    with tempfile.TemporaryDirectory() as simulation_dir:
        ensure_observation_store(simulation_dir)
        legacy_agent = object()
        env = MagicMock()
        env.agent_graph.get_agents.return_value = [(4, legacy_agent)]
        env.agent_graph.get_agent.return_value = legacy_agent
        env.step = AsyncMock()

        consumed_count = await apply_injected_events(
            env=env,
            simulation_dir=simulation_dir,
            config={"agents": [{"agent_id": 4, "platform_preference": "twitter"}]},
            platform="twitter",
            current_round=6,
            events=[
                {
                    "event_type": "dynamic_instruction",
                    "payload": {"agent_id": 4, "instruction": "Prefer concise posts."},
                }
            ],
            agent_names={4: "Agent_4"},
            manual_action_cls=MagicMock(),
            action_type_cls=MagicMock(),
            action_logger=MagicMock(),
        )

        assert consumed_count == 1
        env.step.assert_not_awaited()

        import sqlite3

        conn = sqlite3.connect(os.path.join(simulation_dir, "simulation_observations.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT payload_json FROM injected_events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        intervention = json.loads(row[0])["_intervention"]
        assert intervention["status"] == "rejected"
        assert intervention["applied_agent_ids"] == []
        assert intervention["applied_target_count"] == 0
        assert intervention["unavailable_agent_ids"] == [4]


@pytest.mark.asyncio
async def test_apply_injected_events_preserves_resolution_and_execution_outcomes():
    """Final intervention records must retain targets missing during resolution."""
    with tempfile.TemporaryDirectory() as simulation_dir:
        ensure_observation_store(simulation_dir)
        available_agent = MagicMock()
        env = MagicMock()
        env.agent_graph.get_agents.return_value = [(1, available_agent)]
        env.agent_graph.get_agent.side_effect = [
            available_agent,
            KeyError(2),
            available_agent,
        ]
        env.step = AsyncMock()

        consumed_count = await apply_injected_events(
            env=env,
            simulation_dir=simulation_dir,
            config={
                "agents": [
                    {"agent_id": 1, "platform_preference": "twitter"},
                    {"agent_id": 2, "platform_preference": "twitter"},
                ]
            },
            platform="twitter",
            current_round=7,
            events=[
                {
                    "event_type": "persona_change",
                    "payload": {
                        "agent_ids": [1, 2],
                        "instruction": "Prefer concise posts.",
                    },
                }
            ],
            agent_names={1: "Agent_1", 2: "Agent_2"},
            manual_action_cls=MagicMock(),
            action_type_cls=MagicMock(),
        )

        assert consumed_count == 1
        env.step.assert_awaited_once()

        import sqlite3

        conn = sqlite3.connect(os.path.join(simulation_dir, "simulation_observations.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT payload_json FROM injected_events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        intervention = json.loads(row[0])["_intervention"]
        assert intervention["status"] == "applied"
        assert intervention["applied_agent_ids"] == [1]
        assert intervention["unavailable_agent_ids"] == [2]


@pytest.mark.asyncio
async def test_apply_injected_events_rejects_unknown_persona_target():
    """Test unknown persona targets are rejected but still recorded with clear outcome."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        simulation_dir = tmp_dir
        platform = "twitter"
        current_round = 1

        ensure_observation_store(simulation_dir)

        mock_env = MagicMock()
        mock_env.agent_graph.get_agent.side_effect = KeyError("agent missing")

        config = {"agents": [{"agent_id": 1, "platform_preference": "twitter"}], "time_config": {}}
        agent_names = {1: "Agent_1"}

        injected_events = [
            {
                "event_type": "persona_modification",
                "payload": {"agent_id": 99, "instruction": "Injecting synthetic correction"},
                "timestamp": "2026-07-29T16:12:00Z",
            }
        ]

        applied_count = await apply_injected_events(
            env=mock_env,
            simulation_dir=simulation_dir,
            config=config,
            platform=platform,
            current_round=current_round,
            events=injected_events,
            agent_names=agent_names,
            manual_action_cls=MagicMock(),
            action_type_cls=MagicMock(),
            action_logger=None,
        )

        assert applied_count == 1

        import sqlite3
        conn = sqlite3.connect(os.path.join(simulation_dir, "simulation_observations.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT payload_json FROM injected_events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        payload = json.loads(row[0])
        assert payload["_intervention"]["status"] == "rejected"
        assert payload["_intervention"]["requested_agent_ids"] == [99]
        assert payload["_intervention"]["resolved_agent_ids"] == []
