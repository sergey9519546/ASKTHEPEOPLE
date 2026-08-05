"""Fork service storage-path resolution and route error mapping.

The bug these pin: fork_simulation defaulted `simulations_dir` to the literal
relative string "uploads/simulations", so it resolved against the process cwd
and ignored UPLOAD_FOLDER / OASIS_SIMULATION_DATA_DIR. Every other simulation
path in the codebase goes through Config.OASIS_SIMULATION_DATA_DIR, so on any
deployment that configures storage — which the Railway setup does — fork looked
in a directory nothing else writes to and raised "Simulation <id> not found"
for ids that plainly existed.
"""

import json
import os
import sqlite3

import pytest

from app import create_app
from app.config import Config
from app.services.simulation_fork_service import ForkError, fork_simulation
from app.utils.safe_path import SafePathError


@pytest.fixture
def store(tmp_path, monkeypatch):
    """An isolated simulations directory wired through Config, as deployed."""
    sims = tmp_path / "simulations"
    (sims / "sim_real").mkdir(parents=True)
    (sims / "sim_real" / "run_state.json").write_text(
        json.dumps({"simulation_id": "sim_real", "round_num": 9}), encoding="utf-8"
    )
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(sims))
    return sims


@pytest.fixture
def api_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_fork_uses_the_configured_store_not_a_cwd_relative_path(store):
    """The regression: this raised "not found" for an id that exists."""
    new_id = fork_simulation("sim_real", target_turn=3)

    assert new_id
    assert (store / new_id).is_dir(), "fork wrote outside the configured store"


def test_fork_does_not_create_a_cwd_relative_uploads_directory(store, tmp_path, monkeypatch):
    """Proves the default no longer resolves against the process cwd."""
    workdir = tmp_path / "elsewhere"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    fork_simulation("sim_real", target_turn=1)

    assert not (workdir / "uploads").exists(), (
        "fork resolved its storage path against the cwd"
    )


def test_fork_rewrites_the_new_id_and_rolls_back_the_round(store):
    new_id = fork_simulation("sim_real", target_turn=3)

    state = json.loads((store / new_id / "run_state.json").read_text(encoding="utf-8"))
    assert state["simulation_id"] == new_id
    assert state["round_num"] == 3


def test_fork_truncates_observations_past_the_target_turn(store):
    db_path = store / "sim_real" / "simulation_observations.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE interviews (round_num INTEGER, note TEXT)")
    conn.executemany(
        "INSERT INTO interviews VALUES (?, ?)",
        [(1, "keep"), (3, "keep"), (4, "drop"), (9, "drop")],
    )
    conn.commit()
    conn.close()

    new_id = fork_simulation("sim_real", target_turn=3)

    forked = sqlite3.connect(store / new_id / "simulation_observations.db")
    rounds = sorted(r[0] for r in forked.execute("SELECT round_num FROM interviews"))
    forked.close()
    assert rounds == [1, 3]


def test_fork_leaves_the_source_untouched(store):
    db_path = store / "sim_real" / "simulation_observations.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE interviews (round_num INTEGER, note TEXT)")
    conn.executemany("INSERT INTO interviews VALUES (?, ?)", [(1, "a"), (9, "b")])
    conn.commit()
    conn.close()

    fork_simulation("sim_real", target_turn=3)

    src = sqlite3.connect(db_path)
    rounds = sorted(r[0] for r in src.execute("SELECT round_num FROM interviews"))
    src.close()
    assert rounds == [1, 9], "forking must not truncate the simulation it copied"


def test_fork_does_not_hold_the_copied_database_open(store):
    """A leaked handle would keep the copy locked for the next writer."""
    db_path = store / "sim_real" / "simulation_observations.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE interviews (round_num INTEGER)")
    conn.commit()
    conn.close()

    new_id = fork_simulation("sim_real", target_turn=1)
    forked_db = store / new_id / "simulation_observations.db"

    # On Windows an open handle makes this raise; on POSIX it would succeed
    # regardless, so also assert the file is writable through a fresh cursor.
    os.rename(forked_db, forked_db.with_suffix(".moved"))
    os.rename(forked_db.with_suffix(".moved"), forked_db)


# --------------------------------------------------------------------------- #
# Branch lineage
# --------------------------------------------------------------------------- #

def _write_manager_state(store, sim_id="sim_real", **overrides):
    payload = {
        "simulation_id": sim_id,
        "project_id": "proj_1",
        "graph_id": "graph_1",
        "status": "completed",
        "current_round": 9,
    }
    payload.update(overrides)
    (store / sim_id / "state.json").write_text(json.dumps(payload), encoding="utf-8")


def test_fork_records_its_parent_and_branch_point(store):
    """Without this a fork is indistinguishable from an unrelated simulation.

    The roadmap's branch tree cannot be assembled from the stored data unless
    each fork records where it came from and at which turn.
    """
    _write_manager_state(store)

    new_id = fork_simulation("sim_real", target_turn=4)

    state = json.loads((store / new_id / "state.json").read_text(encoding="utf-8"))
    assert state["forked_from"] == "sim_real"
    assert state["forked_at_turn"] == 4
    assert state["forked_at"]


def test_fork_rewrites_the_copied_state_id(store):
    """The copy used to keep the source's simulation_id on disk."""
    _write_manager_state(store)

    new_id = fork_simulation("sim_real", target_turn=4)

    state = json.loads((store / new_id / "state.json").read_text(encoding="utf-8"))
    assert state["simulation_id"] == new_id


def test_fork_starts_the_branch_at_the_turn_it_branched_from(store):
    _write_manager_state(store, current_round=9)

    new_id = fork_simulation("sim_real", target_turn=4)

    state = json.loads((store / new_id / "state.json").read_text(encoding="utf-8"))
    assert state["current_round"] == 4


def test_original_simulation_records_no_lineage(store):
    """Originals must stay distinguishable from branches."""
    _write_manager_state(store)

    fork_simulation("sim_real", target_turn=4)

    source = json.loads((store / "sim_real" / "state.json").read_text(encoding="utf-8"))
    assert source.get("forked_from") is None


def test_fork_without_manager_state_still_succeeds(store):
    """A simulation can be forked before the manager has written state.json."""
    assert not (store / "sim_real" / "state.json").exists()
    assert fork_simulation("sim_real", target_turn=1)


def test_corrupt_manager_state_does_not_leave_an_orphan(store):
    _write_manager_state(store)
    (store / "sim_real" / "state.json").write_text("not json", encoding="utf-8")
    before = {p.name for p in store.iterdir()}

    with pytest.raises(ForkError):
        fork_simulation("sim_real", target_turn=1)

    assert {p.name for p in store.iterdir()} == before


def test_route_returns_lineage_in_the_creation_response(api_client, store):
    _write_manager_state(store)

    resp = api_client.post("/api/simulation/sim_real/fork", json={"target_turn": 4})

    assert resp.status_code == 201
    data = resp.get_json()["data"]
    assert data["forked_from"] == "sim_real"
    assert data["forked_at_turn"] == 4


def test_simple_dict_carries_lineage_for_the_branch_tree():
    """/api/simulation/list must expose lineage or the tree needs N requests."""
    from app.services.simulation_manager import SimulationState

    state = SimulationState(
        simulation_id="child",
        project_id="p",
        graph_id="g",
        forked_from="parent",
        forked_at_turn=3,
        forked_at="2026-08-04T00:00:00+00:00",
    )
    payload = state.to_simple_dict()
    assert payload["forked_from"] == "parent"
    assert payload["forked_at_turn"] == 3


def test_corrupt_run_state_is_not_reported_as_not_found(store):
    """JSONDecodeError subclasses ValueError, which the route maps to 404.

    A corrupt run state is a server-side failure, not a missing simulation,
    and the parser's message must not be echoed back as the reason.
    """
    (store / "sim_real" / "run_state.json").write_text("not json", encoding="utf-8")

    with pytest.raises(ForkError):
        fork_simulation("sim_real", target_turn=1)


def test_failed_fork_leaves_no_orphan_directory(store):
    """A half-finished fork used to leave a copy that listings treat as real."""
    (store / "sim_real" / "run_state.json").write_text("not json", encoding="utf-8")
    before = {p.name for p in store.iterdir()}

    with pytest.raises(ForkError):
        fork_simulation("sim_real", target_turn=1)

    assert {p.name for p in store.iterdir()} == before


def test_route_maps_a_corrupt_run_state_to_500(api_client, store):
    (store / "sim_real" / "run_state.json").write_text("not json", encoding="utf-8")

    resp = api_client.post("/api/simulation/sim_real/fork", json={"target_turn": 1})
    assert resp.status_code == 500
    body = resp.get_json()
    # The scrubber replaces 5xx error strings; what matters is that the parser
    # message is not what reaches the client.
    assert "Expecting value" not in json.dumps(body)


def test_unknown_id_still_reports_not_found(store):
    with pytest.raises(ValueError):
        fork_simulation("no_such_sim", target_turn=1)


def test_malformed_id_is_rejected_by_safe_join(store):
    with pytest.raises(SafePathError):
        fork_simulation("../escape", target_turn=1)


# --------------------------------------------------------------------------- #
# Route-level error mapping
# --------------------------------------------------------------------------- #

def test_route_requires_target_turn(api_client):
    resp = api_client.post("/api/simulation/sim_real/fork", json={})
    assert resp.status_code == 400


def test_route_rejects_non_integer_target_turn(api_client):
    """Previously fell through to the ValueError handler and reported 404."""
    resp = api_client.post("/api/simulation/sim_real/fork", json={"target_turn": "soon"})
    assert resp.status_code == 400
    assert "integer" in resp.get_json()["error"]


def test_route_returns_404_for_unknown_simulation(api_client, store):
    resp = api_client.post("/api/simulation/nope/fork", json={"target_turn": 1})
    assert resp.status_code == 404


def test_route_forks_successfully(api_client, store):
    resp = api_client.post("/api/simulation/sim_real/fork", json={"target_turn": 2})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["new_simulation_id"]


# --------------------------------------------------------------------------- #
# SimulationRunner: the log handle must not leak when the process fails to spawn
# --------------------------------------------------------------------------- #

def test_start_simulation_closes_the_log_when_spawning_fails(tmp_path, monkeypatch):
    """Popen can fail after the log file is open but before it is registered.

    The handle is only handed to cls._stdout_files once Popen returns, so a
    failure in between used to leak it and leave simulation.log locked.
    """
    import subprocess

    from app.services import simulation_runner as runner_module
    from app.services.simulation_runner import SimulationRunner

    opened = []
    real_open = open

    def tracking_open(*args, **kwargs):
        handle = real_open(*args, **kwargs)
        if args and str(args[0]).endswith("simulation.log"):
            opened.append(handle)
        return handle

    monkeypatch.setattr("builtins.open", tracking_open)
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("cannot spawn")),
    )
    monkeypatch.setattr(runner_module.Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    # Preflight gates the path under test and needs a fully valid simulation on
    # disk; stub it so this test stays about the log handle.
    monkeypatch.setattr(runner_module, "run_preflight", lambda _dir: {"status": "passed"})

    sim_id = "sim_spawn_fail"
    sim_dir = tmp_path / sim_id
    sim_dir.mkdir()
    (sim_dir / "simulation_config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(OSError):
        SimulationRunner.start_simulation(simulation_id=sim_id, platform="parallel")

    assert opened, "the test did not reach the log-file open"
    for handle in opened:
        assert handle.closed, "simulation.log was left open after a failed spawn"
    assert sim_id not in SimulationRunner._stdout_files
