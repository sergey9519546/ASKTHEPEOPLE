"""Decision-lens revision, review, and finalization service behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensV1,
    LensDispositionV1,
)
from app.services.decision_lens_repository import DecisionLensRepository
from app.services.simulation_manager import SimulationManager, SimulationStatus
from tests.domain.test_decision_lens import valid_artifact, valid_lens, valid_review


def seed_artifact(
    repository: DecisionLensRepository,
    simulation_id: str,
) -> DecisionLensArtifactV1:
    payload = valid_artifact()
    payload["simulation_id"] = simulation_id
    return repository.save_artifact(DecisionLensArtifactV1.model_validate(payload))


def dispositions() -> tuple[LensDispositionV1, ...]:
    return tuple(
        LensDispositionV1.model_validate(item)
        for item in valid_review()["dispositions"]
    )


def test_same_review_body_is_idempotent(tmp_path) -> None:
    from app.services.decision_lens_review_service import DecisionLensReviewService

    repository = DecisionLensRepository(tmp_path)
    seed_artifact(repository, "sim-review-service")
    service = DecisionLensReviewService(
        tmp_path,
        now=lambda: datetime(2026, 8, 8, tzinfo=UTC),
        review_id_factory=lambda: f"dlr_{'4' * 32}",
    )

    first, first_status = service.submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )
    second, second_status = service.submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )

    assert first == second
    assert first_status == second_status
    assert first_status.approved is True
    assert len(list((tmp_path / "decision_lens_reviews").glob("*.json"))) == 1


def test_revision_replaces_one_lens_and_stales_review(tmp_path) -> None:
    from app.services.decision_lens_review_service import DecisionLensReviewService

    repository = DecisionLensRepository(tmp_path)
    artifact = seed_artifact(repository, "sim-revise-service")
    service = DecisionLensReviewService(
        tmp_path,
        now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
        artifact_id_factory=lambda: f"dla_{'5' * 32}",
        review_id_factory=lambda: f"dlr_{'6' * 32}",
    )
    service.submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )
    payload = valid_lens(1)
    payload["purpose"] = "Evaluate an explicitly revised implementation boundary."
    replacement = DecisionLensV1.model_validate(payload)

    revised = service.revise_lens(artifact.lenses[0].lens_id, replacement)

    assert revised.revision == 2
    assert revised.lenses[0].purpose == payload["purpose"]
    assert revised.lenses[1:] == artifact.lenses[1:]
    assert repository.review_status().code == "decision_lens_review_stale"


def test_finalize_rechecks_hashes_before_pipeline(tmp_path, monkeypatch) -> None:
    from app.config import Config
    from app.services.decision_lens_review_service import (
        DecisionLensFinalizationError,
        DecisionLensReviewService,
        finalize_decision_lens_preparation,
    )

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    manager = SimulationManager()
    state = manager.create_simulation("project-1", "graph-1")
    state.status = SimulationStatus.NEEDS_REVIEW
    manager._save_simulation_state(state)
    sim_dir = manager._get_simulation_dir(state.simulation_id)
    repository = DecisionLensRepository(sim_dir)
    artifact = seed_artifact(repository, state.simulation_id)
    service = DecisionLensReviewService(
        sim_dir,
        artifact_id_factory=lambda: f"dla_{'7' * 32}",
        review_id_factory=lambda: f"dlr_{'8' * 32}",
    )
    service.submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )
    replacement_payload = artifact.lenses[0].model_dump(mode="json")
    replacement_payload["purpose"] = "Evaluate a changed implementation boundary."
    service.revise_lens(
        artifact.lenses[0].lens_id,
        DecisionLensV1.model_validate(replacement_payload),
    )
    calls: list[str] = []

    with pytest.raises(
        DecisionLensFinalizationError,
        match="decision_lens_review_stale",
    ):
        finalize_decision_lens_preparation(
            state.simulation_id,
            manager=manager,
            runtime_pipeline=lambda **_kwargs: calls.append("called"),
        )

    assert calls == []
    assert manager.get_simulation(state.simulation_id).status == (
        SimulationStatus.NEEDS_REVIEW
    )


def test_finalize_moves_ready_only_after_passing_pipeline(tmp_path, monkeypatch) -> None:
    from app.config import Config
    from app.services.decision_lens_review_service import (
        DecisionLensReviewService,
        finalize_decision_lens_preparation,
    )

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    manager = SimulationManager()
    state = manager.create_simulation("project-2", "graph-2")
    state.status = SimulationStatus.NEEDS_REVIEW
    manager._save_simulation_state(state)
    sim_dir = manager._get_simulation_dir(state.simulation_id)
    repository = DecisionLensRepository(sim_dir)
    seed_artifact(repository, state.simulation_id)
    DecisionLensReviewService(
        sim_dir,
        review_id_factory=lambda: f"dlr_{'9' * 32}",
    ).submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )

    result = finalize_decision_lens_preparation(
        state.simulation_id,
        manager=manager,
        runtime_pipeline=lambda **_kwargs: {
            "preflight": {"status": "passed"},
            "config_reasoning": "Functional adapter configuration.",
        },
    )

    assert result.status == SimulationStatus.READY
    assert result.config_generated is True
    assert result.config_reasoning == "Functional adapter configuration."


def test_finalize_task_completes_task_record(monkeypatch) -> None:
    from app.models.task import TaskManager, TaskStatus
    from app.services import decision_lens_review_service as review_module
    from app.tasks.simulation_tasks import finalize_decision_lens_preparation_task

    task_id = "task-finalize-review-service"
    state = type(
        "ReadyState",
        (),
        {
            "status": SimulationStatus.READY,
            "to_simple_dict": lambda self: {
                "simulation_id": "sim-finalize-task",
                "status": "ready",
            },
        },
    )()
    monkeypatch.setattr(
        review_module,
        "finalize_decision_lens_preparation",
        lambda _simulation_id: state,
    )
    task_manager = TaskManager()
    task_manager.create_task(
        "decision_lens_finalize",
        metadata={"simulation_id": "sim-finalize-task"},
        task_id=task_id,
    )

    result = finalize_decision_lens_preparation_task.apply(
        kwargs={
            "simulation_id": "sim-finalize-task",
            "task_id": task_id,
        }
    ).get()

    assert result["status"] == "ready"
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.COMPLETED


def test_default_finalization_writes_adapter_and_config(tmp_path, monkeypatch) -> None:
    import json

    from app.config import Config
    from app.services import simulation_preflight
    from app.services.decision_lens_review_service import (
        DecisionLensReviewService,
        finalize_decision_lens_preparation,
    )

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        simulation_preflight,
        "run_preflight",
        lambda _simulation_dir: {"status": "passed"},
    )
    manager = SimulationManager()
    state = manager.create_simulation("project-default", "graph-default")
    state.status = SimulationStatus.NEEDS_REVIEW
    manager._save_simulation_state(state)
    sim_dir = manager._get_simulation_dir(state.simulation_id)
    repository = DecisionLensRepository(sim_dir)
    seed_artifact(repository, state.simulation_id)
    DecisionLensReviewService(sim_dir).submit_review(
        reviewer_assertion="Scenario review lead",
        authentication_strength="application_bearer_self_attested_reviewer",
        dispositions=dispositions(),
    )

    result = finalize_decision_lens_preparation(
        state.simulation_id,
        manager=manager,
    )

    assert result.status == SimulationStatus.READY
    runtime = json.loads(
        (tmp_path / state.simulation_id / "decision_lens_runtime.v1.json")
        .read_text(encoding="utf-8")
    )
    assert runtime["schema_version"] == "decision-lens-runtime/v1"
    assert len(runtime["adapters"]) == 4
    assert (tmp_path / state.simulation_id / "simulation_config.json").exists()
