"""Functional runtime adapters are deterministic and non-anthropomorphic."""

from __future__ import annotations

from app.domain.decision_lens import DecisionLensArtifactV1, DecisionLensReviewV1
from app.services.decision_lens_repository import DecisionLensRepository
from tests.domain.test_decision_lens import valid_artifact, valid_review


def approved_pair(tmp_path) -> tuple[DecisionLensArtifactV1, DecisionLensReviewV1]:
    repository = DecisionLensRepository(tmp_path)
    artifact = repository.save_artifact(
        DecisionLensArtifactV1.model_validate(valid_artifact())
    )
    review_payload = valid_review()
    review_payload["lens_artifact_id"] = artifact.artifact_id
    review_payload["lens_artifact_sha256"] = artifact.artifact_sha256
    review = repository.save_review(
        DecisionLensReviewV1.model_validate(review_payload)
    )
    return artifact, review


def test_adapter_is_deterministic_and_excludes_identity_compatibility(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import (
        build_runtime_adapters,
        render_semantic_prompt,
    )

    artifact, review = approved_pair(tmp_path)
    first = build_runtime_adapters(artifact, review)
    second = build_runtime_adapters(artifact, review)

    assert first == second
    adapter = first[0]
    assert adapter.agent_id == 1
    assert adapter.platform_username == "decision_lens_01"
    assert adapter.platform_description.endswith("not a person.")
    prompt = render_semantic_prompt(adapter).lower()
    assert "age:" not in prompt
    assert "gender:" not in prompt
    assert "mbti" not in prompt
    assert "biography" not in prompt
    assert "not a person" in prompt
    assert artifact.lenses[0].goals[0].lower() in prompt
    assert artifact.lenses[0].constraints[0].lower() in prompt
    assert artifact.lenses[0].decision_criteria[0].lower() in prompt


def test_changed_goal_changes_semantic_prompt(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    original = build_runtime_adapters(artifact, review)[0].semantic_prompt
    payload = artifact.model_dump(mode="json")
    payload["artifact_sha256"] = None
    payload["lenses"][0]["goals"][0] = "Evaluate a materially changed delivery goal"
    changed = DecisionLensArtifactV1.model_validate(payload)
    review_payload = review.model_dump(mode="json")
    review_payload["review_sha256"] = None
    from app.domain.decision_lens import canonical_payload_sha256

    review_payload["lens_artifact_sha256"] = canonical_payload_sha256(changed)
    changed_review = DecisionLensReviewV1.model_validate(review_payload)

    updated = build_runtime_adapters(changed, changed_review)[0].semantic_prompt

    assert updated != original
    assert "materially changed delivery goal" in updated.lower()


def test_runtime_json_has_no_forbidden_identity_keys(tmp_path) -> None:
    from app.services.decision_lens_runtime_adapter import build_runtime_adapters

    artifact, review = approved_pair(tmp_path)
    payload = [
        adapter.model_dump(mode="json")
        for adapter in build_runtime_adapters(artifact, review)
    ]
    forbidden = {"age", "gender", "mbti", "persona", "bio", "profession"}

    assert all(forbidden.isdisjoint(item) for item in payload)
