"""The legacy filesystem lifecycle must not mirror rows into ``dw_runs``.

``SimulationManager`` previously dual-wrote each simulation state save into
the canonical ``dw_runs`` table with a ``uuid5`` physical id, a
``run_{simulation_id}`` public id, and fabricated ``default-org`` /
``default-workspace`` tenant ids. The canonical writer (``RunRepository``)
emits UUIDv7 physical ids and independent ``run_…`` aliases, and the domain
kernel (``ActorContext`` / ``RunSnapshot``) requires UUIDv7 — so mirror rows
were incompatible with every canonical read. This pins the fix: saving state
touches only the filesystem store.
"""

from __future__ import annotations

import json
import os

import pytest


@pytest.fixture
def manager_with_persistence_on(tmp_path, monkeypatch):
    from app.config import Config
    from app.services import simulation_manager as manager_module

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    # The removed mirror only fired when Supabase persistence was configured.
    # Keep the flag on so a regression that reintroduces a mirror would be
    # caught rather than silently skipping behind the flag.
    monkeypatch.setattr(Config, "USE_SUPABASE_PERSISTENCE", True)

    storage_checks = []

    def _is_storage_configured() -> bool:
        storage_checks.append(True)
        return True

    import app.services.supabase_client as supabase_client

    monkeypatch.setattr(
        supabase_client,
        "is_storage_configured",
        _is_storage_configured,
        raising=False,
    )

    manager = manager_module.SimulationManager()
    state = manager.create_simulation(
        project_id="project-1",
        graph_id="graph-1",
        enable_twitter=True,
        enable_reddit=True,
    )
    return manager, state, tmp_path, storage_checks


def test_simulation_save_writes_filesystem_state_only(
    manager_with_persistence_on,
):
    from app.services.simulation_manager import SimulationStatus

    manager, state, tmp_path, storage_checks = manager_with_persistence_on

    state.status = SimulationStatus.RUNNING
    manager._save_simulation_state(state)

    state_file = os.path.join(tmp_path, state.simulation_id, "state.json")
    assert os.path.exists(state_file)
    with open(state_file, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["status"] == "running"
    assert saved["simulation_id"] == state.simulation_id

    # The save path must never consult Supabase storage: the filesystem is the
    # only store for the legacy lifecycle.
    assert storage_checks == []


def test_simulation_manager_has_no_canonical_mirror(manager_with_persistence_on):
    manager, _state, _tmp_path, _storage_checks = manager_with_persistence_on
    assert not hasattr(manager, "_mirror_to_run_repository")
    assert not hasattr(manager, "_SIM_TO_RUN_STATE")
