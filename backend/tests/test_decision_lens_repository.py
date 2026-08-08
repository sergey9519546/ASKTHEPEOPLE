"""Immutable decision-lens artifact and review repository behavior."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.decision_lens import (
    DecisionLensArtifactV1,
    DecisionLensReviewV1,
    canonical_payload_sha256,
)
from tests.domain.test_decision_lens import valid_artifact, valid_review


def make_artifact(revision: int = 1, marker: str = "1") -> DecisionLensArtifactV1:
    payload = valid_artifact()
    payload["artifact_id"] = f"dla_{marker * 32}"
    payload["revision"] = revision
    payload["artifact_sha256"] = None
    for index, lens in enumerate(payload["lenses"], start=1):
        lens["purpose"] = (
            f"Evaluate implementation option {index} for artifact revision {revision}."
        )
    return DecisionLensArtifactV1.model_validate(payload)


def make_review(
    artifact: DecisionLensArtifactV1,
    *,
    marker: str = "2",
    authentication_strength: str = (
        "application_bearer_self_attested_reviewer"
    ),
    approved: bool = True,
) -> DecisionLensReviewV1:
    payload = valid_review()
    payload["review_id"] = f"dlr_{marker * 32}"
    payload["simulation_id"] = artifact.simulation_id
    payload["lens_artifact_id"] = artifact.artifact_id
    payload["lens_artifact_sha256"] = canonical_payload_sha256(artifact)
    payload["authentication_strength"] = authentication_strength
    payload["reviewed_at"] = datetime(2026, 8, 8, tzinfo=UTC).isoformat()
    payload["dispositions"] = [
        {
            "lens_id": lens.lens_id,
            "disposition": "approved" if approved else "rejected",
            "note": "Approved for this scenario boundary."
            if approved
            else "Rejected pending revision.",
            "sensitive_attribute_dispositions": [],
        }
        for lens in artifact.lenses
    ]
    payload["overall_status"] = "approved" if approved else "rejected"
    payload["review_sha256"] = None
    return DecisionLensReviewV1.model_validate(payload)


def test_repository_preserves_immutable_artifact_revisions(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import DecisionLensRepository

    repository = DecisionLensRepository(tmp_path)
    first = repository.save_artifact(make_artifact(revision=1, marker="1"))
    second = repository.save_artifact(make_artifact(revision=2, marker="3"))

    assert first.artifact_sha256
    assert second.artifact_sha256
    assert repository.get_artifact(first.artifact_id) == first
    assert repository.get_current_artifact() == second
    assert (tmp_path / "decision_lens_artifacts" / f"{first.artifact_id}.json").is_file()


def test_repository_rejects_artifact_id_collision(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import (
        DecisionLensRepository,
        DecisionLensRepositoryError,
    )

    repository = DecisionLensRepository(tmp_path)
    repository.save_artifact(make_artifact(revision=1, marker="1"))
    conflicting = make_artifact(revision=2, marker="1")

    with pytest.raises(DecisionLensRepositoryError, match="artifact_id_conflict"):
        repository.save_artifact(conflicting)


def test_changed_artifact_makes_review_stale(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import DecisionLensRepository

    repository = DecisionLensRepository(tmp_path)
    first = repository.save_artifact(make_artifact(revision=1, marker="1"))
    repository.save_review(make_review(first))
    repository.save_artifact(make_artifact(revision=2, marker="3"))

    status = repository.review_status()
    assert status.approved is False
    assert status.code == "decision_lens_review_stale"
    assert status.remediation == "review_current_decision_lenses"


def test_approved_review_authorizes_execution(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import DecisionLensRepository

    repository = DecisionLensRepository(tmp_path, production=True)
    artifact = repository.save_artifact(make_artifact())
    review = repository.save_review(make_review(artifact))

    status = repository.assert_execution_approved()
    assert status.approved is True
    assert status.code == "decision_lens_review_approved"
    assert status.artifact_id == artifact.artifact_id
    assert status.review_id == review.review_id


def test_rejected_review_does_not_authorize_execution(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import (
        DecisionLensAdmissionError,
        DecisionLensRepository,
    )

    repository = DecisionLensRepository(tmp_path)
    artifact = repository.save_artifact(make_artifact())
    repository.save_review(make_review(artifact, approved=False))

    with pytest.raises(DecisionLensAdmissionError) as exc:
        repository.assert_execution_approved()
    assert exc.value.code == "decision_lens_review_rejected"


def test_no_auth_review_cannot_authorize_production(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import (
        DecisionLensAdmissionError,
        DecisionLensRepository,
    )

    repository = DecisionLensRepository(tmp_path, production=True)
    artifact = repository.save_artifact(make_artifact())
    repository.save_review(
        make_review(
            artifact,
            authentication_strength="development_no_auth_self_attested_reviewer",
        )
    )

    with pytest.raises(DecisionLensAdmissionError) as exc:
        repository.assert_execution_approved()
    assert exc.value.code == "decision_lens_review_required"
    assert exc.value.remediation == "authenticate_and_review_decision_lenses"


def test_review_must_cover_exact_current_lens_set(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import (
        DecisionLensRepository,
        DecisionLensRepositoryError,
    )

    repository = DecisionLensRepository(tmp_path)
    artifact = repository.save_artifact(make_artifact())
    payload = make_review(artifact).model_dump(mode="json")
    payload["dispositions"][-1]["lens_id"] = "lens_unknown"
    payload["review_sha256"] = None

    with pytest.raises(DecisionLensRepositoryError, match="review_lens_set_mismatch"):
        repository.save_review(DecisionLensReviewV1.model_validate(payload))


def test_identical_review_write_is_idempotent(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import DecisionLensRepository

    repository = DecisionLensRepository(tmp_path)
    artifact = repository.save_artifact(make_artifact())
    review = make_review(artifact)

    first = repository.save_review(review)
    second = repository.save_review(review)
    assert first == second
    assert len(list((tmp_path / "decision_lens_reviews").glob("*.json"))) == 1


def test_atomic_pointer_never_exposes_partial_json(tmp_path: Path) -> None:
    from app.services.decision_lens_repository import (
        DecisionLensRepository,
        DecisionLensRepositoryError,
    )

    repository = DecisionLensRepository(tmp_path)
    repository.save_artifact(make_artifact(revision=1, marker="1"))
    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def reader() -> None:
        barrier.wait()
        for _ in range(200):
            try:
                current = repository.get_current_artifact()
                assert current is not None
            except (
                AssertionError,
                DecisionLensRepositoryError,
            ) as exc:  # pragma: no cover - assertion captures details
                errors.append(exc)
                return

    thread = threading.Thread(target=reader)
    thread.start()
    barrier.wait()
    for revision, marker in enumerate("3456789abcdef", start=2):
        repository.save_artifact(make_artifact(revision=revision, marker=marker))
    thread.join(timeout=5)

    assert thread.is_alive() is False
    assert errors == []
    pointer = json.loads((tmp_path / "decision_lenses.current.json").read_text())
    assert pointer["artifact_id"] == repository.get_current_artifact().artifact_id
