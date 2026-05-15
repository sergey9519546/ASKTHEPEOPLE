import asyncio

from app.services.simulation_artifacts import write_json
from app.services.simulation_runtime_contract import (
    apply_bootstrap_actions,
    apply_scheduled_events,
    bootstrap_boost_agent_ids,
    scheduled_event_boost_agent_ids,
    select_active_agent_ids,
)


class FakeActionType:
    CREATE_POST = "CREATE_POST"
    FOLLOW = "FOLLOW"


class FakeManualAction:
    def __init__(self, action_type, action_args):
        self.action_type = action_type
        self.action_args = action_args


class FakeAgentGraph:
    def get_agent(self, agent_id):
        return f"agent:{agent_id}"


class FakeEnv:
    def __init__(self):
        self.agent_graph = FakeAgentGraph()
        self.steps = []

    async def step(self, actions):
        self.steps.append(actions)


def _config():
    return {
        "agent_configs": [
            {
                "agent_id": 0,
                "entity_name": "Alice",
                "entity_type": "Student",
                "normalized_role": "student",
                "activity_level": 0.8,
                "active_hours": list(range(24)),
                "platform_preference": "twitter",
                "reaction_style": "reactive",
                "conflict_tolerance": 0.7,
                "authority_sensitivity": 0.2,
                "novelty_seeking": 0.8,
                "influence_weight": 1.2,
            },
            {
                "agent_id": 1,
                "entity_name": "Bob",
                "entity_type": "Community",
                "normalized_role": "community",
                "activity_level": 0.7,
                "active_hours": list(range(24)),
                "platform_preference": "reddit",
                "reaction_style": "measured",
                "conflict_tolerance": 0.5,
                "authority_sensitivity": 0.3,
                "novelty_seeking": 0.5,
                "influence_weight": 1.0,
            },
            {
                "agent_id": 2,
                "entity_name": "Carol",
                "entity_type": "MediaOutlet",
                "normalized_role": "media",
                "activity_level": 0.6,
                "active_hours": list(range(24)),
                "platform_preference": "both",
                "reaction_style": "amplifying",
                "conflict_tolerance": 0.6,
                "authority_sensitivity": 0.4,
                "novelty_seeking": 0.7,
                "influence_weight": 2.5,
            },
        ],
        "time_config": {
            "agents_per_hour_min": 1,
            "agents_per_hour_max": 3,
            "peak_hours": [12],
            "off_peak_hours": [2],
            "peak_activity_multiplier": 1.0,
            "off_peak_activity_multiplier": 0.2,
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17],
        },
        "network_bootstrap": {
            "enable_follow_bootstrap": True,
            "follow_density": 0.7,
            "role_bias_rules": {"student": 0.8, "media": 0.75},
            "platforms": {"twitter": True, "reddit": True},
        },
        "bootstrap_posts": [
            {
                "poster_agent_id": 0,
                "content": "Initial seed post",
                "poster_assignment_confidence": 0.9,
                "poster_assignment_reason": "matched",
            }
        ],
        "event_schedule": [
            {
                "trigger_round": 2,
                "platforms": ["twitter"],
                "event_type": "topic_spike",
                "payload": {"topics": ["housing", "policy"]},
                "targeting": {"roles": ["media", "student"]},
                "reasoning": "spike",
            }
        ],
    }


def test_select_active_agents_respects_platform_preference(monkeypatch):
    # We want to test that platform preference influences probability,
    # and that agent 1 is NOT selected while 0 and 2 ARE selected.
    # Agent 0 probability: 0.8 * 1.15 = 0.92
    # Agent 1 probability: 0.7 * 0.3 = 0.21
    # Agent 2 probability: 0.6 * 1.0 = 0.6
    # So we can set random.random() to return 0.5, which will select agents 0 and 2 but not 1.
    # Wait, the code sets random.uniform(a,b) to b, so target_count is 3 (max).
    # The problem is that random.random() returning 0.0 means ALL agents are selected!
    # Because 0.0 < 0.92, 0.0 < 0.21, and 0.0 < 0.6.
    # If random.random() returns 0.5:
    # 0.5 < 0.92 (True, agent 0 selected)
    # 0.5 < 0.21 (False, agent 1 NOT selected)
    # 0.5 < 0.6 (True, agent 2 selected)
    # Let's change random.random() to return 0.5.
    monkeypatch.setattr("app.services.simulation_runtime_contract.random.uniform", lambda a, b: 3)
    monkeypatch.setattr("app.services.simulation_runtime_contract.random.random", lambda: 0.5)

    selected = select_active_agent_ids(
        config=_config(),
        platform="twitter",
        current_hour=12,
        round_num=1,
    )

    assert 0 in selected
    assert 2 in selected
    assert 1 not in selected


def test_bootstrap_actions_persist_and_apply(tmp_path):
    config = _config()
    write_json(
        tmp_path / "agent_relationship_bootstrap.json",
        [
            {
                "source_agent_id": 0,
                "target_agent_id": 2,
                "relation_type": "supportive",
                "affinity_score": 0.8,
                "platforms": ["twitter"],
                "follow_seed": 0.8,
                "interaction_bias": 0.75,
                "source_edge_refs": ["edge:a"],
            }
        ],
    )

    env = FakeEnv()
    applied = asyncio.run(
        apply_bootstrap_actions(
            env=env,
            simulation_dir=str(tmp_path),
            config=config,
            platform="twitter",
            agent_names={0: "Alice", 2: "Carol"},
            manual_action_cls=FakeManualAction,
            action_type_cls=FakeActionType,
        )
    )

    assert applied == 2
    assert len(env.steps) == 1
    rows = (tmp_path / "bootstrap_actions.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 2
    assert bootstrap_boost_agent_ids(str(tmp_path), config, "twitter") == [0, 2]


def test_scheduled_events_apply_and_boost_ids(tmp_path):
    config = _config()
    write_json(tmp_path / "agent_relationship_bootstrap.json", [])

    env = FakeEnv()
    applied = asyncio.run(
        apply_scheduled_events(
            env=env,
            simulation_dir=str(tmp_path),
            config=config,
            platform="twitter",
            current_round=2,
            agent_names={0: "Alice", 2: "Carol"},
            manual_action_cls=FakeManualAction,
            action_type_cls=FakeActionType,
        )
    )

    assert applied >= 1
    assert len(env.steps) == 1
    rows = (tmp_path / "scheduled_events_applied.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == applied
    boosted = scheduled_event_boost_agent_ids(str(tmp_path), config, "twitter", 2)
    assert 0 in boosted or 2 in boosted
