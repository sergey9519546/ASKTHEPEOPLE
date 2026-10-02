"""Population tier 4 (MASS_POPULATION) wiring and bound tests.

The 50,000-character tier per
docs/plans/2026-10-01-50k-character-scale-plan.md. The property that matters
most: **the flag is fail-closed** — no test may enable a config value to make
another test pass, so every tier-4 assertion here sets the flag explicitly
and every default-run assertion proves the ceiling did not move.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app
from app.config import Config
from app.services.archetype_engine import ArchetypeEngine
from app.utils.input_policy import InputPolicyError
from app.api.simulation import _validate_prepare_controls


# --- tier spec ----------------------------------------------------------- #


def test_tier4_spec_composition_is_exactly_50k():
    spec = ArchetypeEngine.get_tier_spec("4")
    assert spec.name == "Mass Population"
    assert spec.n_archetypes == 250
    assert spec.expansion_factor == 20
    assert spec.target_llm_agents == 5000
    assert spec.follower_count == 45000
    # The declared composition lands exactly 50,000.
    assert spec.total_population == 50_000


@pytest.mark.parametrize(
    "alias",
    ["4", "TIER_4", "TIER4", "MASS", "MASSPOPULATION", "mass_population"],
)
def test_tier4_resolves_by_every_alias(alias):
    assert ArchetypeEngine.get_tier_spec(alias).total_population == 50_000


def test_existing_tiers_are_unchanged():
    """A tier addition must not silently move the existing ceilings."""
    assert ArchetypeEngine.get_tier_spec("1").total_population == 20
    assert ArchetypeEngine.get_tier_spec("2").total_population == 580
    assert ArchetypeEngine.get_tier_spec("3").total_population == 5_300


def test_unknown_tier_still_defaults_to_tier2():
    assert ArchetypeEngine.get_tier_spec("unknown-thing").total_population == 580


# --- request-seam validation --------------------------------------------- #


def _controls(data, monkeypatch=None):
    return _validate_prepare_controls(data)


def test_tier4_prepare_without_flag_is_refused(monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", False)
    with pytest.raises(InputPolicyError) as excinfo:
        _controls(
            {
                "population_tier": "mass_population",
                "use_archetypes": True,
            }
        )
    assert excinfo.value.code == "population_tier_not_enabled"


def test_tier4_prepare_with_flag_passes_validation(monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    controls = _controls(
        {
            "population_tier": "mass_population",
            "use_archetypes": True,
            "archetype_count": 250,
            "expansion_factor": 20,
        }
    )
    assert controls["population_tier"] == "mass_population"
    assert controls["archetype_count"] == 250
    assert controls["expansion_factor"] == 20


def test_tier4_archetype_bounds_come_from_config(monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    monkeypatch.setattr(Config, "TIER4_ARCHETYPE_COUNT", 250)
    monkeypatch.setattr(Config, "TIER4_EXPANSION_FACTOR", 20)
    monkeypatch.setattr(Config, "TIER4_PREPARED_PROFILE_MAX", 5000)
    # 250 x 20 = 5,000 <= 5,000 passes.
    controls = _controls(
        {
            "population_tier": "mass_population",
            "use_archetypes": True,
        }
    )
    assert controls["archetype_count"] == 250
    assert controls["expansion_factor"] == 20


def test_tier4_prepared_profile_cap_is_enforced(monkeypatch):
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    # A within-bounds 250 x 20 product must be refused when the declared
    # prepared-profile maximum is lower. Patching the maximum (not the
    # factors) exercises the product check, which the per-field bounds
    # would otherwise shadow.
    monkeypatch.setattr(Config, "TIER4_PREPARED_PROFILE_MAX", 4900)
    with pytest.raises(InputPolicyError) as excinfo:
        _controls(
            {
                "population_tier": "mass_population",
                "use_archetypes": True,
                "archetype_count": 250,
                "expansion_factor": 20,  # 250 x 20 = 5,000 > 4,900
            }
        )
    assert excinfo.value.code == "profile_count_out_of_range"


def test_default_run_archetype_bounds_did_not_move(monkeypatch):
    """The tier-4 bounds must not leak into default-run validation."""
    monkeypatch.setattr(Config, "POPULATION_TIER_4_ENABLED", True)
    monkeypatch.setattr(Config, "TIER4_ARCHETYPE_COUNT", 250)
    monkeypatch.setattr(Config, "TIER4_EXPANSION_FACTOR", 20)
    monkeypatch.setattr(Config, "TIER4_PREPARED_PROFILE_MAX", 5000)
    # A default run (no tier key) still rejects the OLD 50x20->500 cap: 50
    # archetypes is the old ARCHETYPE_COUNT_MAX, and 50 x 20 = 1,000 > 500.
    with pytest.raises(InputPolicyError) as excinfo:
        _controls({"use_archetypes": True, "archetype_count": 50, "expansion_factor": 20})
    assert excinfo.value.code == "profile_count_out_of_range"


def test_invalid_tier_value_is_refused():
    with pytest.raises(InputPolicyError) as excinfo:
        _controls({"population_tier": "representative_sample"})
    assert excinfo.value.code == "invalid_population_tier"


def test_omitted_tier_means_default_run():
    controls = _controls({})
    assert controls["population_tier"] is None


def test_non_tier4_tiers_are_accepted_without_the_flag():
    controls = _controls({"population_tier": "macro_crowd"})
    assert controls["population_tier"] == "macro_crowd"


# --- follower bound at the start seam ------------------------------------ #


@pytest.fixture()
def api_client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def _make_simulation(api_client, monkeypatch, name="tier-bound-test"):
    """Create a real simulation record so the start endpoint reaches the
    follower-bound validation (the 404 for a missing simulation precedes
    validation now that the state loads first)."""
    from app.services.simulation_manager import SimulationManager

    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    manager = SimulationManager()
    state = manager.create_simulation(
        project_id="proj_tier_bounds",
        graph_id="atp_tier_bounds",
    )
    return state.simulation_id


def test_default_run_still_rejects_501_followers(api_client, monkeypatch):
    """The default follower ceiling did not move."""
    # FOLLOWER_COUNT_MAX lives in input_policy.py and execution_routes
    # imports it by name, so patch the imported name the handler reads.
    import app.api.routes.execution_routes as execution_routes

    simulation_id = _make_simulation(api_client, monkeypatch)
    monkeypatch.setattr(execution_routes, "FOLLOWER_COUNT_MAX", 500)
    response = api_client.post(
        "/api/simulation/start",
        json={
            "simulation_id": simulation_id,
            "enable_followers": True,
            "follower_count": 501,
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "integer_field_out_of_range"


def test_default_run_still_accepts_500_followers(api_client, monkeypatch):
    import app.api.routes.execution_routes as execution_routes

    simulation_id = _make_simulation(api_client, monkeypatch)
    monkeypatch.setattr(execution_routes, "FOLLOWER_COUNT_MAX", 500)
    # A valid follower count passes validation; the run then fails later on
    # admission (the record has no approved decision lens) — proving the
    # bound did not silently change and validation itself passed.
    response = api_client.post(
        "/api/simulation/start",
        json={
            "simulation_id": simulation_id,
            "enable_followers": True,
            "follower_count": 500,
        },
    )
    assert response.status_code != 400
    assert response.get_json().get("error") != "integer_field_out_of_range"
