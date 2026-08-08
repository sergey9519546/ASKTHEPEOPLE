"""Decision-lens domain contracts and deterministic artifact identity."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64


def valid_reference(ref_id: str = "assumption-1") -> dict:
    return {
        "ref_id": ref_id,
        "role": "declared_assumption",
        "origin": "ASSUMPTION_DECLARED",
    }


def valid_lens(index: int) -> dict:
    return {
        "lens_id": f"lens_procurement_{index}",
        "title": f"Procurement review function {index}",
        "purpose": f"Evaluate implementation option {index} against approved criteria.",
        "context": f"This lens examines a distinct procurement condition for option {index}.",
        "goals": [f"Reduce implementation risk for option {index}"],
        "constraints": [f"Budget ceiling for option {index}"],
        "access_conditions": [f"Access to review record {index}"],
        "incentives": [f"Timely delivery for option {index}"],
        "switching_costs": [f"Migration cost for option {index}"],
        "information_conditions": [f"Uncertain supplier capacity {index}"],
        "decision_criteria": [f"Operational continuity criterion {index}"],
        "excluded_inferences": [f"Do not infer population support {index}"],
        "uncertainty_notes": [f"Supplier response remains unknown {index}"],
        "input_refs": [valid_reference(f"assumption-{index}")],
        "sensitive_attributes": [],
        "status": "pending",
    }


def valid_prompt_record() -> dict:
    return {
        "prompt_id": "decision_lens_generation",
        "prompt_version": "1.0.0",
        "prompt_sha256": HEX_A,
        "model": "test-model-snapshot",
        "system_prompt_sha256": HEX_B,
        "user_prompt_sha256": HEX_C,
        "context_prompt_sha256s": [HEX_D],
        "output_sha256": HEX_A,
        "temperature": 0.0,
        "max_tokens": 4096,
        "structured_output": True,
        "tools_bound": False,
    }


def valid_artifact() -> dict:
    refs = [valid_reference(f"assumption-{index}") for index in range(1, 5)]
    return {
        "schema_version": "decision-lens/v1",
        "artifact_id": f"dla_{'1' * 32}",
        "simulation_id": "sim-test-1",
        "revision": 1,
        "created_at": datetime(2026, 8, 8, tzinfo=UTC).isoformat(),
        "prompt_record": valid_prompt_record(),
        "input_refs": refs,
        "lenses": [valid_lens(index) for index in range(1, 5)],
        "truth_fields": {
            "output_origin": "synthetic",
            "human_respondent_count": 0,
            "is_forecast": False,
            "is_public_opinion_measure": False,
            "is_causal_evidence": False,
            "source_role": "starting_conditions_only",
            "human_validation_scope": "external_to_synthetic_run",
        },
        "artifact_sha256": None,
    }


def valid_review() -> dict:
    return {
        "schema_version": "decision-lens-review/v1",
        "review_id": f"dlr_{'2' * 32}",
        "simulation_id": "sim-test-1",
        "lens_artifact_id": f"dla_{'1' * 32}",
        "lens_artifact_sha256": HEX_A,
        "reviewed_at": datetime(2026, 8, 8, tzinfo=UTC).isoformat(),
        "reviewer_assertion": "Scenario review lead",
        "authentication_strength": ("application_bearer_self_attested_reviewer"),
        "dispositions": [
            {
                "lens_id": f"lens_procurement_{index}",
                "disposition": "approved",
                "note": "Approved for this scenario boundary.",
                "sensitive_attribute_dispositions": [],
            }
            for index in range(1, 5)
        ],
        "overall_status": "approved",
        "review_sha256": None,
    }


def test_decision_lens_forbids_identity_fields() -> None:
    from app.domain.decision_lens import DecisionLensV1

    payload = valid_lens(1)
    payload["age"] = 42

    with pytest.raises(ValidationError):
        DecisionLensV1.model_validate(payload)


def test_artifact_hash_is_stable_across_mapping_order() -> None:
    from app.domain.decision_lens import (
        DecisionLensArtifactV1,
        canonical_payload_sha256,
    )

    left = DecisionLensArtifactV1.model_validate(valid_artifact())
    right = DecisionLensArtifactV1.model_validate(
        json.loads(json.dumps(valid_artifact(), sort_keys=True))
    )

    assert canonical_payload_sha256(left) == canonical_payload_sha256(right)


def test_artifact_hash_ignores_attached_hash_field() -> None:
    from app.domain.decision_lens import (
        DecisionLensArtifactV1,
        canonical_payload_sha256,
    )

    artifact = DecisionLensArtifactV1.model_validate(valid_artifact())
    digest = canonical_payload_sha256(artifact)
    with_digest = artifact.model_copy(update={"artifact_sha256": digest})

    assert canonical_payload_sha256(with_digest) == digest


def test_artifact_requires_four_to_eight_lenses() -> None:
    from app.domain.decision_lens import DecisionLensArtifactV1

    payload = valid_artifact()
    payload["lenses"] = payload["lenses"][:3]

    with pytest.raises(ValidationError):
        DecisionLensArtifactV1.model_validate(payload)


def test_artifact_rejects_materially_duplicate_lenses() -> None:
    from app.domain.decision_lens import DecisionLensArtifactV1

    payload = valid_artifact()
    duplicate = dict(payload["lenses"][0])
    duplicate["lens_id"] = "lens_duplicate"
    duplicate["title"] = "Alternate wording for the same function"
    payload["lenses"][1] = duplicate

    with pytest.raises(ValidationError, match="material_duplicate"):
        DecisionLensArtifactV1.model_validate(payload)


@pytest.mark.parametrize("title", ["Jane Smith", "Marcus A. Rivera"])
def test_lens_rejects_identity_like_person_names(title: str) -> None:
    from app.domain.decision_lens import DecisionLensV1

    payload = valid_lens(1)
    payload["title"] = title

    with pytest.raises(ValidationError, match="identity_like_title"):
        DecisionLensV1.model_validate(payload)


@pytest.mark.parametrize(
    "context",
    [
        "I am a procurement officer with a long personal history.",
        "I work in procurement and I prefer familiar suppliers.",
        "My role is to approve each purchasing decision.",
    ],
)
def test_lens_rejects_first_person_identity_narrative(context: str) -> None:
    from app.domain.decision_lens import DecisionLensV1

    payload = valid_lens(1)
    payload["context"] = context

    with pytest.raises(ValidationError, match="first_person_identity"):
        DecisionLensV1.model_validate(payload)


def test_sensitive_attribute_requires_all_restrictions() -> None:
    from app.domain.decision_lens import DecisionLensV1

    payload = valid_lens(1)
    payload["sensitive_attributes"] = [
        {
            "attribute": "disability status",
            "decision_relevance": "Relevant to an explicitly reviewed access requirement.",
            "retention_restriction": "short",
            "export_restriction": "Do not export outside the reviewed workspace.",
        }
    ]

    with pytest.raises(ValidationError):
        DecisionLensV1.model_validate(payload)


def test_review_cannot_claim_verified_authentication() -> None:
    from app.domain.decision_lens import DecisionLensReviewV1

    payload = valid_review()
    payload["authentication_strength"] = "verified_user"

    with pytest.raises(ValidationError):
        DecisionLensReviewV1.model_validate(payload)


def test_review_overall_status_must_match_dispositions() -> None:
    from app.domain.decision_lens import DecisionLensReviewV1

    payload = valid_review()
    payload["dispositions"][0]["disposition"] = "rejected"

    with pytest.raises(ValidationError, match="review_overall_status_mismatch"):
        DecisionLensReviewV1.model_validate(payload)


def test_domain_models_are_frozen() -> None:
    from app.domain.decision_lens import DecisionLensV1

    lens = DecisionLensV1.model_validate(valid_lens(1))

    with pytest.raises(ValidationError):
        lens.title = "Changed after validation"


def test_sensitive_attribute_dispositions_are_deeply_immutable() -> None:
    from app.domain.decision_lens import LensDispositionV1

    disposition = LensDispositionV1.model_validate(
        {
            "lens_id": "lens_procurement_1",
            "disposition": "approved",
            "note": "Approved with a reviewed sensitive attribute.",
            "sensitive_attribute_dispositions": [
                {
                    "attribute": "disability status",
                    "disposition": "approved",
                    "justification": (
                        "Required to evaluate an explicitly approved access condition."
                    ),
                }
            ],
        }
    )

    with pytest.raises(TypeError):
        disposition.sensitive_attribute_dispositions[0] = (  # type: ignore[index]
            disposition.sensitive_attribute_dispositions[0]
        )
