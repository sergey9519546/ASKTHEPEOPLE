"""Preparation stops at a reviewable decision-lens boundary."""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.domain.decision_lens import DecisionLensArtifactV1
from app.services.zep_entity_reader import EntityNode, FilteredEntities
from tests.domain.test_decision_lens import valid_artifact, valid_lens


def filtered_entities() -> FilteredEntities:
    entities = [
        EntityNode(
            uuid=f"node-{index}",
            name=f"Private-looking source label {index}",
            labels=["Entity", "ProcurementFunction"],
            summary=f"Source condition {index} for procurement review.",
            attributes={"capacity_band": f"band-{index}"},
        )
        for index in range(1, 5)
    ]
    return FilteredEntities(
        entities=entities,
        entity_types={"ProcurementFunction"},
        total_count=4,
        filtered_count=4,
    )


class FakeReader:
    def filter_defined_entities(self, **_kwargs) -> FilteredEntities:
        return filtered_entities()


class CapturingGenerator:
    calls: ClassVar[list[dict]] = []

    def generate(self, **kwargs) -> DecisionLensArtifactV1:
        type(self).calls.append(kwargs)
        references = list(kwargs["input_references"])
        payload = valid_artifact()
        payload["simulation_id"] = kwargs["simulation_id"]
        payload["revision"] = kwargs["revision"]
        payload["input_refs"] = [ref.model_dump(mode="json") for ref in references]
        payload["lenses"] = []
        for index, reference in enumerate(references[:4], start=1):
            lens = valid_lens(index)
            lens["input_refs"] = [reference.model_dump(mode="json")]
            payload["lenses"].append(lens)
        return DecisionLensArtifactV1.model_validate(payload)


@pytest.fixture
def configured_manager(tmp_path, monkeypatch):
    from app.config import Config
    from app.services import simulation_manager as manager_module

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", True, raising=False)
    monkeypatch.setattr(manager_module, "ZepEntityReader", FakeReader)
    monkeypatch.setattr(
        manager_module,
        "DecisionLensGenerator",
        CapturingGenerator,
        raising=False,
    )
    CapturingGenerator.calls = []

    manager = manager_module.SimulationManager()
    manager.create_simulation(
        project_id="project-1",
        graph_id="graph-1",
        enable_twitter=True,
        enable_reddit=True,
    )
    state = next(iter(manager._simulations.values()))
    return manager, state, tmp_path


def test_preparation_generates_lenses_and_stops_for_review(configured_manager) -> None:
    from app.services.decision_lens_repository import DecisionLensRepository
    from app.services.simulation_manager import SimulationStatus

    manager, state, root = configured_manager

    result = manager.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="Compare implementation paths.",
        document_text="Untrusted extracted source text.",
    )

    assert result.status == SimulationStatus.NEEDS_REVIEW
    assert result.profiles_count == 0
    assert result.decision_lenses_count == 4
    assert result.config_generated is False

    simulation_dir = root / state.simulation_id
    artifact = DecisionLensRepository(simulation_dir).get_current_artifact()
    assert artifact is not None
    assert len(artifact.lenses) == 4
    assert not (simulation_dir / "canonical_agents.json").exists()
    assert not (simulation_dir / "reddit_profiles.json").exists()
    assert not (simulation_dir / "twitter_profiles.csv").exists()
    assert not (simulation_dir / "simulation_config.json").exists()
    assert not (simulation_dir / "preflight.json").exists()

    call = CapturingGenerator.calls[0]
    assert call["allowed_reference_ids"] == {
        reference.ref_id for reference in call["input_references"]
    }
    assert all("name" not in record for record in call["context_records"])


def test_preparation_flag_fails_closed_without_reactivating_legacy_path(
    configured_manager,
    monkeypatch,
) -> None:
    from app.config import Config
    from app.services.simulation_manager import DecisionLensPreparationError

    manager, state, root = configured_manager
    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", False)

    with pytest.raises(
        DecisionLensPreparationError,
        match="decision_lens_preparation_unavailable",
    ):
        manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement="Compare implementation paths.",
            document_text="Source text.",
        )

    assert CapturingGenerator.calls == []
    simulation_dir = root / state.simulation_id
    assert not (simulation_dir / "canonical_agents.json").exists()


def test_non_neutral_archetype_control_is_rejected(configured_manager) -> None:
    from app.services.simulation_manager import DecisionLensPreparationError

    manager, state, _root = configured_manager

    with pytest.raises(
        DecisionLensPreparationError,
        match="deprecated_control_not_supported",
    ):
        manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement="Compare implementation paths.",
            document_text="Source text.",
            use_archetypes=True,
        )

    assert CapturingGenerator.calls == []


def test_state_round_trip_retains_review_boundary(configured_manager) -> None:
    from app.services.simulation_manager import SimulationManager, SimulationStatus

    manager, state, _root = configured_manager
    result = manager.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="Compare implementation paths.",
        document_text="Source text.",
    )
    manager._simulations.clear()

    reloaded = SimulationManager().get_simulation(result.simulation_id)

    assert reloaded is not None
    assert reloaded.status == SimulationStatus.NEEDS_REVIEW
    assert reloaded.decision_lenses_count == 4
    assert reloaded.to_simple_dict()["decision_lenses_count"] == 4


def test_prepare_task_completes_successfully_with_review_required(
    monkeypatch,
) -> None:
    from app.models.task import TaskManager, TaskStatus
    from app.services.simulation_manager import SimulationManager, SimulationStatus
    from app.tasks.simulation_tasks import prepare_simulation_task

    task_id = "task-decision-lens-review"
    state = type(
        "ReviewState",
        (),
        {
            "status": SimulationStatus.NEEDS_REVIEW,
            "to_simple_dict": lambda self: {
                "simulation_id": "sim-task-review",
                "status": "needs_review",
                "decision_lenses_count": 4,
            },
        },
    )()
    monkeypatch.setattr(
        SimulationManager,
        "prepare_simulation",
        lambda self, **_kwargs: state,
    )
    task_manager = TaskManager()
    task_manager.create_task(
        "simulation_prepare",
        metadata={"simulation_id": "sim-task-review"},
        task_id=task_id,
    )

    result = prepare_simulation_task.apply(
        kwargs={
            "simulation_id": "sim-task-review",
            "task_id": task_id,
            "entity_types": [],
            "use_llm_for_profiles": True,
            "parallel_profile_count": 3,
            "use_archetypes": False,
            "archetype_count": 10,
            "expansion_factor": 10,
            "simulation_requirement": "Compare implementation paths.",
            "document_text": "Source text.",
        }
    ).get()

    assert result["status"] == "needs_review"
    assert result["review_required"] is True
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    assert task.result["review_required"] is True


def test_prepare_route_fails_closed_when_boundary_disabled(monkeypatch) -> None:
    from app import create_app
    from app.config import Config

    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", False)
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)

    response = app.test_client().post(
        "/api/simulation/prepare",
        json={"simulation_id": "sim-disabled"},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "decision_lens_preparation_unavailable"


def test_prepare_route_rejects_archetype_control(monkeypatch) -> None:
    from app import create_app
    from app.config import Config

    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", True)
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)

    response = app.test_client().post(
        "/api/simulation/prepare",
        json={"simulation_id": "sim-deprecated", "use_archetypes": True},
    )

    assert response.status_code == 422
    assert response.get_json()["error"] == "deprecated_control_not_supported"


def test_prepare_route_reuses_existing_review_boundary(monkeypatch) -> None:
    from app import create_app
    from app.api.routes import prep_routes
    from app.config import Config
    from app.services.simulation_manager import SimulationStatus

    state = type(
        "ReviewState",
        (),
        {
            "simulation_id": "sim-review-existing",
            "project_id": "project-1",
            "status": SimulationStatus.NEEDS_REVIEW,
            "decision_lenses_count": 4,
        },
    )()

    class FakeManager:
        def get_simulation(self, _simulation_id):
            return state

    monkeypatch.setattr(Config, "DECISION_LENS_V1_ENABLED", True)
    monkeypatch.setattr(prep_routes, "SimulationManager", FakeManager)
    monkeypatch.setattr(
        prep_routes,
        "_check_simulation_prepared",
        lambda _simulation_id: (False, {}),
    )
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)

    response = app.test_client().post(
        "/api/simulation/prepare",
        json={"simulation_id": state.simulation_id},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["status"] == "needs_review"
    assert payload["review_required"] is True
    assert payload["decision_lenses_count"] == 4
