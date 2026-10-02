"""Preflight enforcement of the tier-4 (mass_population) composition.

The composition is a declaration: 250 archetypes x 20 profiles = 5,000
prepared LLM-tier characters plus a 45,000-strong rule-based crowd generated
at run start. These tests pin the two gates that keep that declaration
honest:

1. `population_tier_gate` — a mass_population run cannot pass preflight
   while POPULATION_TIER_4_ENABLED is off, regardless of which entry point
   (prepare, run, report) invokes preflight.
2. `population_composition` — the tier-4 ceilings (archetype count,
   prepared profiles, crowd size) are checked against the artifacts on disk
   and the declared totals, with the declaration explicitly labelled as
   "not a measured or sampled size".
"""

import json

import pytest

from app.config import Config
from app.services import simulation_preflight as preflight_module
from app.services.simulation_artifacts import write_exports_from_canonical, write_json
from app.utils.input_policy import PREPARED_PROFILE_MAX


def _canonical_agents(count: int):
    return [
        {
            "agent_id": i,
            "source_entity_uuid": f"u{i}",
            "source_entity_type_raw": "Resident",
            "source_entity_type_normalized": "resident",
            "display_name": f"Agent {i}",
            "username": f"a{i}",
            "public_bio": f"Fictional bio {i}",
            "internal_persona": f"Fictional persona {i}",
            "profession": "resident",
            "age": 30,
            "gender": "unspecified",
            "mbti": "INTJ",
            "country": "United States",
            "interested_topics": ["policy"],
            "stance_seed": "neutral",
            "activity_seed": {"platform_preference": "both"},
            "platform_overrides": {"twitter": {}, "reddit": {}},
            "source_facts": [{"kind": "summary", "text": "bio", "ref": f"entity:u{i}"}],
        }
        for i in range(count)
    ]


def _config(agent_count: int):
    return {
        "simulation_id": "sim_tier4",
        "project_id": "proj_tier4",
        "graph_id": "graph_tier4",
        "time_config": {"total_simulation_hours": 24, "minutes_per_round": 30},
        "agent_configs": [
            {"agent_id": i, "entity_uuid": f"u{i}", "entity_name": f"A{i}"}
            for i in range(agent_count)
        ],
        "context_profile": {"language": "en"},
        "network_bootstrap": {"enable_follow_bootstrap": True},
        "event_schedule": [],
        "bootstrap_posts": [],
        "platform_profiles": {"twitter": {"enabled": True}, "reddit": {"enabled": True}},
    }


@pytest.fixture
def sim_dir(tmp_path, monkeypatch):
    """A minimal prepared simulation directory with the noisy checks stubbed."""
    canonical_agents = _canonical_agents(20)
    write_json(tmp_path / "agent_profiles.canonical.json", canonical_agents)
    write_exports_from_canonical(str(tmp_path), canonical_agents)
    write_json(tmp_path / "simulation_config.json", _config(20))
    monkeypatch.setattr(
        preflight_module,
        "write_model_resolution",
        lambda simulation_dir, **kwargs: {"actor": {"ok": True}},
    )
    monkeypatch.setattr(preflight_module, "validate_required_model_env", lambda role, **kwargs: [])
    monkeypatch.setattr(preflight_module, "validate_camel_runtime_imports", lambda: [])
    monkeypatch.setattr(preflight_module.Config, "validate", lambda: [])
    # No admission stub: the decision-lens admission check fails legitimately
    # on a bare directory, and preflight then walks the canonical path the
    # composition checks read (canonical_agents / profile counts).
    return tmp_path


def _checks(result):
    return {c["name"]: c for c in result["checks"]}


def test_tier4_blocked_when_flag_off(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", False)
    write_json(sim_dir / "state.json", {"population_tier": "mass_population"})
    result = preflight_module.run_preflight(str(sim_dir))
    gate = _checks(result)["population_tier_gate"]
    assert gate["status"] == "failed"
    assert gate["details"]["flag_enabled"] is False
    assert result["status"] == "failed"


def test_tier4_passes_when_flag_on_and_composition_within_bounds(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    write_json(sim_dir / "state.json", {"population_tier": "mass_population"})
    write_json(
        sim_dir / "archetypes.json",
        [{"archetype_id": i, "name": f"arch{i}"} for i in range(250)],
    )
    result = preflight_module.run_preflight(str(sim_dir))
    gate = _checks(result)["population_tier_gate"]
    assert gate["status"] == "passed"
    composition = _checks(result)["population_composition"]
    assert composition["status"] == "passed"
    assert composition["details"]["crowd_characters"] == Config.TIER4_FOLLOWER_COUNT
    assert "declaration" in composition["details"]
    # The tier-resolved capacity must be the tier-4 bound, not the default.
    capacity = _checks(result)["profile_capacity"]
    assert capacity["details"]["maximum"] == Config.TIER4_PREPARED_PROFILE_MAX


def test_default_runs_keep_the_default_capacity(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", False)
    result = preflight_module.run_preflight(str(sim_dir))
    gate = _checks(result)["population_tier_gate"]
    assert gate["status"] == "passed"
    assert gate["details"]["population_tier"] == "default"
    capacity = _checks(result)["profile_capacity"]
    assert capacity["details"]["maximum"] == PREPARED_PROFILE_MAX
    assert "population_composition" not in _checks(result)


def test_explicit_tier_parameter_beats_state_file(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    # state says tier 4, caller says default — the explicit parameter wins.
    write_json(sim_dir / "state.json", {"population_tier": "mass_population"})
    result = preflight_module.run_preflight(str(sim_dir), population_tier="default")
    gate = _checks(result)["population_tier_gate"]
    assert gate["details"]["population_tier"] == "default"
    assert "population_composition" not in _checks(result)


def test_tier4_composition_fails_without_archetypes(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    write_json(sim_dir / "state.json", {"population_tier": "mass_population"})
    result = preflight_module.run_preflight(str(sim_dir))
    composition = _checks(result)["population_composition"]
    assert composition["status"] == "failed"
    assert any("archetypes.json" in e for e in composition["details"])
    assert result["status"] == "failed"


def test_tier4_composition_fails_when_crowd_exceeds_ceiling(sim_dir, monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    monkeypatch.setattr(
        Config, "TIER4_FOLLOWER_COUNT", Config.TIER4_FOLLOWER_COUNT_MAX + 1
    )
    write_json(sim_dir / "state.json", {"population_tier": "mass_population"})
    write_json(sim_dir / "archetypes.json", [{"archetype_id": 0, "name": "a0"}])
    result = preflight_module.run_preflight(str(sim_dir))
    composition = _checks(result)["population_composition"]
    assert composition["status"] == "failed"
    assert any("ceiling" in e for e in composition["details"])
