import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.services.simulation_observation_store import (
    ensure_observation_store,
    record_injected_event,
    push_in_memory_event,
    pop_in_memory_events,
    sync_observation_store,
)
from app.services.simulation_runtime_contract import apply_injected_events
from scripts.run_parallel_simulation import RedisEventConsumer


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_inject_endpoint_returns_200_and_publishes_event(client):
    """Test that POST /api/simulation/<id>/inject returns HTTP 200 and publishes event."""
    simulation_id = "sim_test_inject_200"

    mock_state = MagicMock()
    mock_state.simulation_id = simulation_id
    mock_state.status = "running"
    mock_state.config = {"name": "Test Simulation"}

    with patch("app.api.routes.execution_routes.SimulationManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.get_simulation.return_value = mock_state
        mock_mgr_cls.return_value = mock_mgr

        payload = {
            "event_type": "breaking_news",
            "payload": {
                "headline": "Breakthrough Announced!",
                "content": "Major announcement alters current simulation topic dynamics."
            }
        }

        response = client.post(
            f"/api/simulation/{simulation_id}/inject",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_data(as_text=True)}"
        data = response.get_json()
        assert data["success"] is True
        assert data["simulation_id"] == simulation_id
        assert data["channel"] == f"simulation:{simulation_id}:events"
        assert data["event"]["event_type"] == "breaking_news"
        assert data["event"]["payload"]["headline"] == "Breakthrough Announced!"

        events = pop_in_memory_events(simulation_id)
        assert len(events) >= 1
        assert events[0]["event_type"] == "breaking_news"


def test_inject_endpoint_returns_404_for_missing_simulation(client):
    """Test that POST /api/simulation/<id>/inject returns HTTP 404 for non-existent simulation."""
    simulation_id = "sim_non_existent"

    with patch("app.api.simulation.SimulationManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.get_simulation.return_value = None
        mock_mgr_cls.return_value = mock_mgr

        response = client.post(
            f"/api/simulation/{simulation_id}/inject",
            data=json.dumps({"event_type": "breaking_news"}),
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Simulation does not exist" in data["error"]


def test_redis_event_consumer_in_memory_fallback():
    """Test that RedisEventConsumer retrieves events pushed to in-memory fallback queue."""
    simulation_id = "sim_test_consumer_fallback"

    event_payload = {
        "simulation_id": simulation_id,
        "event_type": "persona_modification",
        "payload": {
            "agent_id": 42,
            "instruction": "Adopt an optimistic outlook on economic news."
        },
        "timestamp": "2026-07-29T16:00:00Z"
    }

    push_in_memory_event(simulation_id, event_payload)

    consumer = RedisEventConsumer(simulation_id=simulation_id, redis_url="memory://")
    events = consumer.consume_events()

    assert len(events) >= 1
    matched = [e for e in events if e.get("event_type") == "persona_modification"]
    assert len(matched) == 1
    assert matched[0]["payload"]["agent_id"] == 42
    assert matched[0]["payload"]["instruction"] == "Adopt an optimistic outlook on economic news."


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
            assert "Focus on high-growth technology stocks." in mock_agent.system_message.content

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
