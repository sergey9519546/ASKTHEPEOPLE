"""Regression tests for the audit §5 P1 "Contradictory lifecycle semantics"
sub-defects in `_check_simulation_prepared` (simulation.py).

Two bugs fixed:
1. `prepared_statuses` included "failed", letting /start re-launch a simulation
   whose run had failed.
2. The read-side check rewrote state.json from "preparing" -> "ready" as a side
   effect — a read must never mutate canonical state.
"""

import json
import os

import pytest

from app.api.simulation import _check_simulation_prepared
from app.config import Config

REQUIRED_FILES = [
    "simulation_config.json",
    "agent_profiles.canonical.json",
    "entity_type_registry.json",
    "reddit_profiles.json",
    "twitter_profiles.csv",
    "preflight.json",
]


def _seed_run(tmp_path, *, status, config_generated=True, profiles_count=5):
    """Build a complete simulation directory with the given state.json status."""
    sim_dir = tmp_path / "sim_test"
    sim_dir.mkdir(parents=True, exist_ok=True)
    # All required files present so the file-existence gate passes.
    for name in REQUIRED_FILES:
        (sim_dir / name).write_text("{}", encoding="utf-8")
    # A real profiles list so profiles_count is non-zero.
    (sim_dir / "reddit_profiles.json").write_text(
        json.dumps([{"id": i} for i in range(profiles_count)]), encoding="utf-8"
    )
    # preflight.json with status=passed
    (sim_dir / "preflight.json").write_text(
        json.dumps({"status": "passed"}), encoding="utf-8"
    )
    # state.json with the requested status
    (sim_dir / "state.json").write_text(
        json.dumps(
            {"status": status, "config_generated": config_generated, "entities_count": 5}
        ),
        encoding="utf-8",
    )
    return sim_dir


@pytest.fixture
def sim_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    return tmp_path


def test_failed_status_is_not_treated_as_prepared(sim_data_dir):
    """A simulation whose run FAILED must not be reported as prepared —
    'failed' means the run broke, not that preparation is complete and
    runnable (audit P1). Regression: 'failed' was in prepared_statuses."""
    _seed_run(sim_data_dir, status="failed")
    is_prepared, info = _check_simulation_prepared("sim_test")
    assert is_prepared is False


@pytest.mark.parametrize("good_status", ["ready", "running", "completed", "stopped", "interrupted"])
def test_genuine_prepared_or_post_run_statuses_are_prepared(sim_data_dir, good_status):
    """Positive control: genuinely-prepared and post-run-success statuses still
    report prepared (so the fix didn't over-tighten and break resumption)."""
    _seed_run(sim_data_dir, status=good_status)
    is_prepared, info = _check_simulation_prepared("sim_test")
    assert is_prepared is True


def test_preparing_with_config_generated_is_prepared_without_rewriting_state(sim_data_dir):
    """The prepare-task-finished-but-status-unflipped case: 'preparing' with
    config_generated=True + files + preflight is prepared (True), BUT the
    check must NOT rewrite state.json to 'ready' (audit P1: a read must not
    mutate canonical state)."""
    _seed_run(sim_data_dir, status="preparing")
    is_prepared, info = _check_simulation_prepared("sim_test")
    assert is_prepared is True

    # The canonical state.json must be UNCHANGED — still 'preparing'.
    state = json.loads((sim_data_dir / "sim_test" / "state.json").read_text())
    assert state["status"] == "preparing"


def test_preparing_without_config_generated_is_not_prepared(sim_data_dir):
    """'preparing' without config_generated is mid-preparation: not ready."""
    _seed_run(sim_data_dir, status="preparing", config_generated=False)
    is_prepared, info = _check_simulation_prepared("sim_test")
    assert is_prepared is False


def test_check_does_not_mutate_state_for_any_status(sim_data_dir):
    """The read-side check must never modify state.json, for any status
    (audit P1: 'a status read can rewrite state.json')."""
    for status in ["ready", "preparing", "running", "completed", "failed"]:
        _seed_run(sim_data_dir, status=status)
        before = (sim_data_dir / "sim_test" / "state.json").read_text()
        _check_simulation_prepared("sim_test")
        after = (sim_data_dir / "sim_test" / "state.json").read_text()
        assert before == after, f"state.json was mutated by the read for status={status!r}"
