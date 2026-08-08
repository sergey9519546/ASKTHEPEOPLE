"""Decision-lens review API and asynchronous finalization dispatch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.decision_lens import DecisionLensArtifactV1
from app.models.task import TaskManager, TaskStatus
from app.services.decision_lens_repository import DecisionLensRepository
from app.services.simulation_manager import SimulationStatus
from tests.domain.test_decision_lens import valid_artifact, valid_review

APP_TOKEN = "review-secret-0123456789-abcdef-xyz"


def editable_lens_body(artifact: DecisionLensArtifactV1, index: int = 0) -> dict:
    lens = artifact.lenses[index]
    payload = lens.model_dump(mode="json")
    payload.pop("lens_id")
    payload.pop("status")
    payload["input_ref_ids"] = [ref["ref_id"] for ref in payload.pop("input_refs")]
    return payload


def review_body(*, approved: bool = True) -> dict:
    payload = valid_review()
    dispositions = payload["dispositions"]
    if not approved:
        dispositions[0]["disposition"] = "rejected"
        dispositions[0]["note"] = "Rejected pending a functional correction."
    return {
        "reviewer_assertion": payload["reviewer_assertion"],
        "dispositions": dispositions,
    }


@pytest.fixture
def review_api(tmp_path, monkeypatch):
    from app import create_app
    from app.config import Config
    from app.services.simulation_manager import SimulationManager

    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "APP_TOKEN", APP_TOKEN)
    monkeypatch.setattr(Config, "REQUIRE_APP_AUTH", True)
    app = create_app()
    app.config.update(
        TESTING=True,
        APP_TOKEN=APP_TOKEN,
        REQUIRE_APP_AUTH=True,
    )
    manager = SimulationManager()
    state = manager.create_simulation("project-review", "graph-review")
    state.status = SimulationStatus.NEEDS_REVIEW
    manager._save_simulation_state(state)
    repository = DecisionLensRepository(manager._get_simulation_dir(state.simulation_id))
    payload = valid_artifact()
    payload["simulation_id"] = state.simulation_id
    artifact = repository.save_artifact(
        DecisionLensArtifactV1.model_validate(payload)
    )
    return SimpleNamespace(
        app=app,
        client=app.test_client(),
        manager=manager,
        state=state,
        repository=repository,
        artifact=artifact,
        headers={"Authorization": f"Bearer {APP_TOKEN}"},
    )


def test_route_map_registers_decision_lens_endpoints(review_api) -> None:
    rules = {rule.rule for rule in review_api.app.url_map.iter_rules()}
    assert "/api/simulation/<simulation_id>/decision-lenses" in rules
    assert "/api/simulation/<simulation_id>/decision-lenses/<lens_id>" in rules
    assert "/api/simulation/<simulation_id>/decision-lens-review" in rules


def test_get_returns_current_artifact_and_review_status(review_api) -> None:
    response = review_api.client.get(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lenses",
        headers=review_api.headers,
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["artifact"]["artifact_id"] == review_api.artifact.artifact_id
    assert data["review"] is None
    assert data["review_status"]["code"] == "decision_lens_review_required"


def test_review_schema_forbids_authentication_strength(review_api) -> None:
    response = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json={
            **review_body(),
            "authentication_strength": "verified",
        },
        headers=review_api.headers,
    )

    assert response.status_code == 422


def test_patch_creates_revision_and_stales_prior_review(review_api, monkeypatch) -> None:
    from app.tasks.simulation_tasks import finalize_decision_lens_preparation_task

    monkeypatch.setattr(
        finalize_decision_lens_preparation_task,
        "delay",
        lambda **_kwargs: SimpleNamespace(id="finalize-first"),
    )
    approved = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json=review_body(),
        headers=review_api.headers,
    )
    assert approved.status_code == 202
    body = editable_lens_body(review_api.artifact)
    body["purpose"] = "Evaluate an explicitly revised implementation boundary."

    response = review_api.client.patch(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lenses/"
        f"{review_api.artifact.lenses[0].lens_id}",
        json=body,
        headers=review_api.headers,
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["artifact"]["revision"] == 2
    assert data["review_status"]["code"] == "decision_lens_review_stale"
    state = review_api.manager.get_simulation(review_api.state.simulation_id)
    assert state.status == SimulationStatus.NEEDS_REVIEW


def test_rejected_review_remains_needs_review_without_dispatch(review_api) -> None:
    response = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json=review_body(approved=False),
        headers=review_api.headers,
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["review_status"]["approved"] is False
    assert data["review_status"]["code"] == "decision_lens_review_rejected"
    assert data["review"]["overall_status"] == "rejected"


def test_approved_review_enqueues_finalization(review_api, monkeypatch) -> None:
    from app.tasks.simulation_tasks import finalize_decision_lens_preparation_task

    captured: dict = {}
    dispatches: list[dict] = []

    def fake_delay(**kwargs):
        captured.update(kwargs)
        dispatches.append(dict(kwargs))
        return SimpleNamespace(id="celery-finalize")

    monkeypatch.setattr(
        finalize_decision_lens_preparation_task,
        "delay",
        fake_delay,
    )
    response = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json=review_body(),
        headers=review_api.headers,
    )

    assert response.status_code == 202
    data = response.get_json()["data"]
    assert data["review_status"]["approved"] is True
    assert data["task_id"]
    assert response.headers["Location"] == f"/api/jobs/{data['task_id']}"
    assert captured == {
        "simulation_id": review_api.state.simulation_id,
        "task_id": data["task_id"],
    }

    duplicate = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json=review_body(),
        headers=review_api.headers,
    )
    assert duplicate.status_code == 202
    assert duplicate.get_json()["data"]["task_id"] == data["task_id"]
    assert len(dispatches) == 1


def test_broker_failure_fails_task_and_returns_503(review_api, monkeypatch) -> None:
    from app.tasks.simulation_tasks import finalize_decision_lens_preparation_task

    monkeypatch.setattr(
        finalize_decision_lens_preparation_task,
        "delay",
        lambda **_kwargs: (_ for _ in ()).throw(ConnectionError("broker down")),
    )
    response = review_api.client.put(
        f"/api/simulation/{review_api.state.simulation_id}/decision-lens-review",
        json=review_body(),
        headers=review_api.headers,
    )

    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == "decision_lens_finalization_dispatch_unavailable"
    task = TaskManager().get_task(data["task_id"])
    assert task is not None
    assert task.status == TaskStatus.FAILED
    assert task.public_error == "decision_lens_finalization_dispatch_unavailable"
