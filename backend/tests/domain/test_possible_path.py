"""Tests for the first-class path domain kernel (Task 6).

Validates the invariants from the Task 6 brief:
- Truth contract (zero humans, not a forecast, synthetic origin).
- Contiguous step sequences (1..N in tuple order).
- 4–8 paths per set.
- Unique display codes (P-01..P-N in order).
- Unique content + distinctness hashes (no paraphrase-only duplicates).
- Brief gate requires approval before sealing.
- No probability/likelihood/confidence fields exist on the model.
"""

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.possible_path import (
    BranchBasisRef,
    Consideration,
    DisconfirmingCondition,
    MissingInformation,
    PathArtifactStatus,
    PathBriefGate,
    PathConflict,
    PathReviewDisposition,
    PathReviewItem,
    PathSetArtifact,
    PathSetReview,
    PathStep,
    PossiblePath,
    ValidationQuestion,
    compute_path_content_sha256,
    compute_path_distinctness_sha256,
)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _make_path(display_code="P-01", title="Path A", content_seed="a", distinct_seed="x"):
    uid = uuid4()
    return PossiblePath(
        id=uid,
        public_id=f"path_{uid.hex[:32]}",
        semantic_id=f"path_sem_{uid.hex[:32]}",
        run_id=uuid4(),
        path_set_id=uuid4(),
        display_code=display_code,
        title=title,
        branch_bases=(BranchBasisRef(assertion_id=uuid4(), role="ASSUMPTION", display_label="A1"),),
        branch_trigger=f"Trigger {content_seed}",
        bounded_rationale=f"Rationale {content_seed}",
        scenario_frame=f"Frame {content_seed}",
        steps=(PathStep(sequence=1, statement=f"Step {content_seed}", bounded_rationale="r"),),
        considerations=(Consideration(statement="Consider X", category="stakeholder"),),
        missing_information=(MissingInformation(description="Missing Y", relevance="Needed"),),
        disconfirming_conditions=(DisconfirmingCondition(description="If W", evidence_type="survey"),),
        validation_questions=(ValidationQuestion(question="Is Q valid?", intended_check_type="expert"),),
        content_sha256=_hash(content_seed),
        distinctness_sha256=_hash(distinct_seed),
    )


# --- Truth contract invariants --- #


def test_truth_bundle_is_immutable_zero_humans():
    p = _make_path()
    assert p.truth_human_respondents == 0
    assert p.truth_is_forecast is False
    assert p.truth_output_origin == "synthetic"


def test_truth_human_respondents_cannot_be_nonzero():
    """The le=0 field constraint rejects non-zero at the field level."""
    data = _make_path().model_dump()
    data["truth_human_respondents"] = 1
    data = _lists_to_tuples(data)
    with pytest.raises(ValidationError):
        PossiblePath(**data)


def test_truth_is_forecast_cannot_be_true():
    data = _make_path().model_dump()
    data["truth_is_forecast"] = True
    data = _lists_to_tuples(data)
    with pytest.raises(ValidationError, match="truth_is_forecast_must_be_false"):
        PossiblePath(**data)


# --- Step sequence invariants --- #


def _lists_to_tuples(d):
    """Pydantic model_dump returns lists; tuple fields need tuples."""
    for key in ("steps", "branch_bases", "starting_conditions", "decision_lenses",
                "scenario_rules", "considerations", "missing_information",
                "disconfirming_conditions", "validation_questions", "conflicts"):
        if key in d and isinstance(d[key], list):
            d[key] = tuple(d[key])
    return d


def test_step_sequence_must_be_contiguous():
    data = _make_path().model_dump()
    data = _lists_to_tuples(data)
    data["steps"] = (
        PathStep(sequence=1, statement="A", bounded_rationale="r"),
        PathStep(sequence=3, statement="B", bounded_rationale="r"),
    )
    with pytest.raises(ValidationError, match="path_steps_must_be_contiguous"):
        PossiblePath(**data)


# --- No forbidden quantitative fields --- #


def test_no_probability_or_likelihood_field():
    """The model must not carry probability, likelihood, confidence, score,
    rank, winner, or recommendation fields (Task 6 brief)."""
    fields = set(PossiblePath.model_fields.keys())
    forbidden = {
        "probability", "likelihood", "confidence", "prevalence",
        "public_support", "sample_size", "rank", "score", "winner",
        "recommendation", "hidden_reasoning",
    }
    assert not (fields & forbidden), f"forbidden fields present: {fields & forbidden}"


def test_extra_fields_rejected():
    data = _make_path().model_dump()
    data["probability"] = 0.8
    with pytest.raises(ValidationError, match="extra"):
        PossiblePath(**data)


def test_semantic_lineage_id_uses_path_sem_namespace():
    """The semantic lineage ID namespace is ``path_sem_`` (Task 6 brief
    §"Semantic lineage identity"), not the ``path_set_`` public-ID namespace."""
    data = _make_path().model_dump()
    data["semantic_id"] = f"path_sem_{uuid4().hex[:32]}"
    PossiblePath(**data)  # accepted

    data["semantic_id"] = f"path_set_{uuid4().hex[:32]}"
    with pytest.raises(ValidationError, match="semantic_id"):
        PossiblePath(**data)


# --- Path set artifact invariants --- #


def _make_path_set(n_paths=4):
    paths = tuple(
        _make_path(display_code=f"P-{i+1:02d}", title=f"Path {chr(65+i)}",
                   content_seed=chr(97+i), distinct_seed=chr(120+i))
        for i in range(n_paths)
    )
    return PathSetArtifact(
        id=uuid4(),
        public_id=f"path_set_{uuid4().hex[:32]}",
        run_id=uuid4(),
        status=PathArtifactStatus.NEEDS_REVIEW,
        paths=paths,
        content_sha256=_hash("set"),
        created_at=datetime.now(timezone.utc),
    )


def test_path_set_requires_minimum_four_paths():
    with pytest.raises(ValidationError):
        _make_path_set(n_paths=3)


def test_path_set_allows_maximum_eight_paths():
    ps = _make_path_set(n_paths=8)
    assert len(ps.paths) == 8


def test_path_set_rejects_nine_paths():
    with pytest.raises(ValidationError):
        _make_path_set(n_paths=9)


def test_display_codes_must_be_sequential_P01_through_PN():
    paths = tuple(
        _make_path(display_code=f"P-{i+1:02d}", content_seed=chr(97+i), distinct_seed=chr(120+i))
        for i in range(4)
    )
    # Swap two codes — should fail.
    bad_paths = paths[:2] + (paths[2].model_copy(update={"display_code": "P-01"}),) + paths[3:]
    with pytest.raises(ValidationError, match="display_codes_must_be"):
        PathSetArtifact(
            id=uuid4(), public_id=f"path_set_{uuid4().hex[:32]}",
            run_id=uuid4(), status=PathArtifactStatus.NEEDS_REVIEW,
            paths=bad_paths, content_sha256=_hash("s"),
            created_at=datetime.now(timezone.utc),
        )


def test_duplicate_content_hashes_rejected():
    """Two paths with identical content hashes are paraphrase-only duplicates."""
    paths = tuple(
        _make_path(display_code=f"P-{i+1:02d}", content_seed="same", distinct_seed=chr(120+i))
        for i in range(4)
    )
    with pytest.raises(ValidationError, match="paraphrase_only_rejected"):
        PathSetArtifact(
            id=uuid4(), public_id=f"path_set_{uuid4().hex[:32]}",
            run_id=uuid4(), status=PathArtifactStatus.NEEDS_REVIEW,
            paths=paths, content_sha256=_hash("s"),
            created_at=datetime.now(timezone.utc),
        )


# --- Brief gate --- #


def test_brief_gate_requires_pass_to_seal():
    with pytest.raises(ValidationError, match="brief_gate_must_pass"):
        PathBriefGate(
            path_set_id=uuid4(),
            path_set_content_sha256=_hash("ps"),
            review_content_sha256=_hash("rv"),
            gate_passed=False,
            sealed_at=datetime.now(timezone.utc),
        )


def test_brief_gate_seals_when_passed():
    gate = PathBriefGate(
        path_set_id=uuid4(),
        path_set_content_sha256=_hash("ps"),
        review_content_sha256=_hash("rv"),
        gate_passed=True,
        sealed_at=datetime.now(timezone.utc),
    )
    assert gate.gate_passed is True


# --- Hash helpers --- #


def test_content_hash_is_deterministic():
    p = _make_path()
    h1 = compute_path_content_sha256(p)
    h2 = compute_path_content_sha256(p)
    assert h1 == h2
    assert len(h1) == 64


def test_distinctness_hash_differs_for_different_content():
    p1 = _make_path(title="Alpha path", content_seed="a")
    p2 = _make_path(title="Beta path", content_seed="b")
    h1 = compute_path_distinctness_sha256(p1)
    h2 = compute_path_distinctness_sha256(p2)
    assert h1 != h2
