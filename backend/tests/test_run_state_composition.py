"""Run-state composition fields for tier-4 composite runs.

The run-status surface reports the *declared* composition of a composite
run — prepared LLM-tier profiles plus the declared crowd size — never a
measured or sampled population. These tests pin the round-trip of those
fields through SimulationRunState serialization.
"""

import json
import uuid

from app.config import Config
from app.services.simulation_runner import SimulationRunner, SimulationRunState


def test_run_state_defaults_carry_no_composition():
    state = SimulationRunState(simulation_id="sim_x")
    assert state.population_tier is None
    assert state.declared_population_total is None
    assert state.follower_actions_last_round == 0


def test_run_state_to_dict_exposes_composition_fields():
    state = SimulationRunState(
        simulation_id="sim_x",
        population_tier="mass_population",
        declared_population_total=50_000,
        follower_actions_last_round=2_000,
    )
    payload = state.to_dict()
    assert payload["population_tier"] == "mass_population"
    assert payload["declared_population_total"] == 50_000
    assert payload["follower_actions_last_round"] == 2_000


def test_run_state_load_round_trips_composition(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    sim_dir = tmp_path / sim_id
    sim_dir.mkdir()
    (sim_dir / "run_state.json").write_text(
        json.dumps(
            {
                "simulation_id": sim_id,
                "runner_status": "running",
                "population_tier": "mass_population",
                "declared_population_total": 50_000,
                "follower_actions_last_round": 2_000,
                "follower_twitter_count": 4_000,
                "follower_reddit_count": 3_500,
            }
        ),
        encoding="utf-8",
    )
    state = SimulationRunner._load_run_state(sim_id)
    assert state is not None
    assert state.population_tier == "mass_population"
    assert state.declared_population_total == 50_000
    assert state.follower_actions_last_round == 2_000
    # Pre-existing fields must survive the schema addition untouched.
    assert state.follower_twitter_count == 4_000
    assert state.follower_reddit_count == 3_500


def test_start_simulation_declares_tier4_composition(tmp_path, monkeypatch):
    """A mass_population start records the declared total on the run state."""
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    sim_dir = tmp_path / sim_id
    sim_dir.mkdir()
    # Minimal artifacts: canonical profiles + config.
    canonical = [{"agent_id": i} for i in range(10)]
    (sim_dir / "agent_profiles.canonical.json").write_text(
        json.dumps(canonical), encoding="utf-8"
    )
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
                "agent_configs": [{"agent_id": i} for i in range(10)],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "TIER4_FOLLOWER_COUNT", 45_000)
    # Start must not reach the actual runtime — short-circuit after the
    # checks the composition path depends on.
    monkeypatch.setattr(
        "app.services.simulation_runner.run_preflight",
        lambda sim_dir, **kwargs: {"status": "passed", "failed_checks": []},
    )
    monkeypatch.setattr(
        "app.services.simulation_runner.assert_decision_lens_execution_admission",
        lambda sim_dir: {"artifact_id": "a", "artifact_sha256": "x" * 64,
                         "review_id": "r", "review_sha256": "y" * 64,
                         "runtime_adapter": {"sha256": "z" * 64, "agent_count": 10}},
    )

    class _ImmediateExit(Exception):
        pass

    def _explode_before_launch(*args, **kwargs):
        # state has already recorded the composition by the time the OASIS
        # command is built; raising here captures that without spawning OASIS.
        raise _ImmediateExit()

    monkeypatch.setattr(SimulationRunner, "build_runtime_command", _explode_before_launch)

    from app.services.follower_engine import FollowerEngine

    captured = {}
    original_generate = FollowerEngine.generate_followers

    def _spy_generate(self, count, distribution=None):
        captured["count"] = count
        return original_generate(self, count, distribution)

    monkeypatch.setattr(FollowerEngine, "generate_followers", _spy_generate)

    try:
        SimulationRunner.start_simulation(
            sim_id,
            platform="twitter",
            enable_followers=True,
            population_tier="mass_population",
        )
        raised = False
    except _ImmediateExit:
        raised = True
    assert raised, "launch seam was not reached; composition write-up ordering changed"
    state = SimulationRunner._run_states.get(sim_id)
    assert state is not None
    assert state.population_tier == "mass_population"
    # The tier-4 crowd default engaged (signature default was not explicit),
    # and the declared total is prepared profiles + declared crowd. The
    # follower generation ran with the tier crowd size; startup-failure
    # cleanup then released the in-memory followers, so assert the request.
    assert captured["count"] == 45_000
    assert state.declared_population_total == 10 + 45_000
