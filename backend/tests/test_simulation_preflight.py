import json
import hashlib

from app.services import simulation_preflight as preflight_module
from app.services.simulation_artifacts import write_exports_from_canonical, write_json
from app.utils.input_policy import PREPARED_PROFILE_MAX


def _canonical_agents():
    return [
        {
            "agent_id": 0,
            "source_entity_uuid": "u1",
            "source_entity_type_raw": "Student",
            "source_entity_type_normalized": "student",
            "display_name": "Alice",
            "username": "alice_001",
            "public_bio": "bio",
            "internal_persona": "persona",
            "profession": "student",
            "age": 28,
            "gender": "female",
            "mbti": "INTJ",
            "country": "United States",
            "interested_topics": ["policy"],
            "stance_seed": "neutral",
            "activity_seed": {"platform_preference": "both"},
            "platform_overrides": {"twitter": {}, "reddit": {}},
            "source_facts": [{"kind": "summary", "text": "bio", "ref": "entity:u1"}],
        }
    ]


def _config():
    return {
        "simulation_id": "sim_test",
        "project_id": "proj_test",
        "graph_id": "graph_test",
        "time_config": {"total_simulation_hours": 24, "minutes_per_round": 30},
        "agent_configs": [
            {
                "agent_id": 0,
                "entity_uuid": "u1",
                "entity_name": "Alice",
                "entity_type": "Student",
                "normalized_role": "student",
                "reaction_style": "reactive",
                "conflict_tolerance": 0.6,
                "authority_sensitivity": 0.2,
                "novelty_seeking": 0.7,
                "platform_preference": "both",
            }
        ],
        "context_profile": {"language": "en"},
        "network_bootstrap": {"enable_follow_bootstrap": True},
        "event_schedule": [],
        "bootstrap_posts": [{"poster_agent_id": 0, "content": "hello"}],
        "platform_profiles": {"twitter": {"enabled": True}, "reddit": {"enabled": True}},
    }


def test_preflight_passes_when_contracts_are_valid(tmp_path, monkeypatch):
    canonical_agents = _canonical_agents()
    write_json(tmp_path / "agent_profiles.canonical.json", canonical_agents)
    write_exports_from_canonical(str(tmp_path), canonical_agents)
    write_json(tmp_path / "simulation_config.json", _config())

    monkeypatch.setattr(
        preflight_module,
        "write_model_resolution",
        lambda simulation_dir, **kwargs: {"actor": {"ok": True}},
    )
    monkeypatch.setattr(preflight_module, "validate_required_model_env", lambda role, **kwargs: [])
    monkeypatch.setattr(preflight_module, "validate_camel_runtime_imports", lambda: [])
    monkeypatch.setattr(preflight_module.Config, "validate", lambda: [])

    result = preflight_module.run_preflight(str(tmp_path))
    assert result["status"] == "passed"
    assert result["failed_checks"] == []

    with open(tmp_path / "preflight.json", "r", encoding="utf-8") as handle:
        persisted = json.load(handle)
    assert persisted["status"] == "passed"

    with open(tmp_path / "run_manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert manifest["truth_status"] == {
        "human_respondents": 0,
        "external_validation": False,
        "calibration": "not_calibrated",
        "interpretation": "synthetic_scenario_exploration",
    }
    assert manifest["reproducibility"]["deterministic"] is False
    expected_hash = hashlib.sha256(
        (tmp_path / "simulation_config.json").read_bytes()
    ).hexdigest()
    assert (
        manifest["artifacts"]["simulation_config.json"]["sha256"]
        == expected_hash
    )


def test_preflight_rejects_invalid_bootstrap_publisher(tmp_path, monkeypatch):
    canonical_agents = _canonical_agents()
    write_json(tmp_path / "agent_profiles.canonical.json", canonical_agents)
    write_exports_from_canonical(str(tmp_path), canonical_agents)
    config = _config()
    config["bootstrap_posts"][0]["poster_agent_id"] = 99
    write_json(tmp_path / "simulation_config.json", config)

    monkeypatch.setattr(
        preflight_module,
        "write_model_resolution",
        lambda simulation_dir, **kwargs: {"actor": {"ok": True}},
    )
    monkeypatch.setattr(preflight_module, "validate_required_model_env", lambda role, **kwargs: [])
    monkeypatch.setattr(preflight_module, "validate_camel_runtime_imports", lambda: [])
    monkeypatch.setattr(preflight_module.Config, "validate", lambda: [])

    result = preflight_module.run_preflight(str(tmp_path))
    assert result["status"] == "failed"
    assert "poster_assignment" in result["failed_checks"]


def test_preflight_rejects_profile_artifacts_above_runtime_capacity(
    tmp_path,
    monkeypatch,
):
    canonical_agents = []
    agent_configs = []
    for index in range(PREPARED_PROFILE_MAX + 1):
        canonical = dict(_canonical_agents()[0])
        canonical["agent_id"] = index
        canonical["source_entity_uuid"] = f"u{index}"
        canonical_agents.append(canonical)

        agent = dict(_config()["agent_configs"][0])
        agent["agent_id"] = index
        agent["entity_uuid"] = f"u{index}"
        agent_configs.append(agent)

    write_json(tmp_path / "agent_profiles.canonical.json", canonical_agents)
    write_exports_from_canonical(str(tmp_path), canonical_agents)
    config = _config()
    config["agent_configs"] = agent_configs
    config["bootstrap_posts"] = []
    write_json(tmp_path / "simulation_config.json", config)

    monkeypatch.setattr(
        preflight_module,
        "write_model_resolution",
        lambda simulation_dir, **kwargs: {"actor": {"ok": True}},
    )
    monkeypatch.setattr(
        preflight_module,
        "validate_required_model_env",
        lambda role, **kwargs: [],
    )
    monkeypatch.setattr(
        preflight_module,
        "validate_camel_runtime_imports",
        lambda: [],
    )
    monkeypatch.setattr(preflight_module.Config, "validate", lambda: [])

    result = preflight_module.run_preflight(str(tmp_path))

    assert result["status"] == "failed"
    assert "profile_capacity" in result["failed_checks"]
