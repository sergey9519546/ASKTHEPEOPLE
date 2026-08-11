"""Pure domain kernel for first-class paths, typed dependencies, and the brief gate.

Task 6 — the path aggregate that a durable run produces, reviews, and hands to
the decision brief. Every model is Pydantic v2 frozen, strict, ``extra="forbid"``.
Tuples are used for immutable ordered collections. No Flask, SQLAlchemy,
filesystem, clock singleton, or provider import lives here.

The kernel defines:

- ``PathArtifactStatus`` / ``PathReviewDisposition`` — closed vocabularies.
- ``BranchBasisRef``, ``StartingConditionRef``, ``DecisionLensRef``,
  ``ScenarioRuleRef`` — typed dependency references to reviewed inputs.
- ``PathStep`` — ordered synthetic action with bounded rationale.
- ``Consideration``, ``PathConflict``, ``MissingInformation``,
  ``DisconfirmingCondition``, ``ValidationQuestion`` — per-path methodology.
- ``PossiblePath`` — the complete, immutable path record.
- ``PathSetArtifact`` — the 4–8 path set with artifact status + content hash.
- ``PathReviewItem``, ``PathSetReview``, ``PathBriefGate`` — review + gate.

Per the Task 6 brief: "There is no probability, likelihood, confidence,
prevalence, public support, sample size, rank, score, winner, recommendation,
hidden reasoning, or unbounded rationale field."
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Shared constraints --- #

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_DISPLAY_CODE_PATTERN = r"^P-\d{2}$"
_BOUNDED_TEXT = Field(min_length=1, max_length=1200)
_BOUNDED_RATIONALE = Field(min_length=1, max_length=500)


# --- Closed vocabularies --- #

class PathArtifactStatus(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    FAILED = "FAILED"


class PathReviewDisposition(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IRRELEVANT = "IRRELEVANT"


# --- Typed dependency references --- #

class BranchBasisRef(BaseModel):
    """Canonical assertion reference restricted to reviewed ASSUMPTION or
    UNCERTAINTY_STATE roles."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    assertion_id: UUID
    role: Literal["ASSUMPTION", "UNCERTAINTY_STATE"]
    display_label: str = Field(min_length=1, max_length=255)


class StartingConditionRef(BaseModel):
    """Reference to a reviewed starting condition derived from source material."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    condition_id: UUID
    display_label: str = Field(min_length=1, max_length=255)


class DecisionLensRef(BaseModel):
    """Reference to a reviewed decision lens applied during path construction."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    lens_id: UUID
    display_label: str = Field(min_length=1, max_length=255)


class ScenarioRuleRef(BaseModel):
    """Reference to a reviewed scenario rule governing the path's behavior."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    rule_id: UUID
    display_label: str = Field(min_length=1, max_length=255)


# --- Per-path methodology types --- #

class PathStep(BaseModel):
    """Ordered synthetic action with bounded user-visible rationale."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    sequence: int = Field(ge=1)
    statement: str = _BOUNDED_TEXT
    bounded_rationale: str = _BOUNDED_RATIONALE
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"


class Consideration(BaseModel):
    """A statement with an approved methodology category."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    statement: str = _BOUNDED_TEXT
    category: str = Field(min_length=1, max_length=64)


class PathConflict(BaseModel):
    """An explicit conflict between paths or within a path."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    description: str = _BOUNDED_TEXT
    conflicting_path_display_code: str | None = Field(
        default=None, pattern=_DISPLAY_CODE_PATTERN
    )


class MissingInformation(BaseModel):
    """A known gap in the source material or assumptions."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    description: str = _BOUNDED_TEXT
    relevance: str = _BOUNDED_RATIONALE


class DisconfirmingCondition(BaseModel):
    """What real-world evidence would discriminate this path."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    description: str = _BOUNDED_TEXT
    evidence_type: str = Field(min_length=1, max_length=128)


class ValidationQuestion(BaseModel):
    """A non-leading question for external human validation."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    question: str = _BOUNDED_TEXT
    intended_check_type: str = Field(min_length=1, max_length=128)


# --- The path aggregate --- #

class PossiblePath(BaseModel):
    """A complete, immutable, first-class path.

    Per the Task 6 brief: no probability, likelihood, confidence, prevalence,
    public support, sample size, rank, score, winner, recommendation, hidden
    reasoning, or unbounded rationale field.
    """
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    # Identity
    id: UUID
    public_id: str = Field(pattern=r"^path_[0-9a-f]{32}$")
    semantic_id: str = Field(pattern=r"^path_set_[0-9a-f]{32}$")
    run_id: UUID
    path_set_id: UUID

    # Display
    display_code: str = Field(pattern=_DISPLAY_CODE_PATTERN)
    title: str = Field(min_length=1, max_length=255)

    # Reviewed dependency references (at least one branch basis required)
    branch_bases: tuple[BranchBasisRef, ...] = Field(min_length=1)
    starting_conditions: tuple[StartingConditionRef, ...] = Field(default_factory=tuple)
    decision_lenses: tuple[DecisionLensRef, ...] = Field(default_factory=tuple)
    scenario_rules: tuple[ScenarioRuleRef, ...] = Field(default_factory=tuple)

    # Content
    branch_trigger: str = _BOUNDED_TEXT
    bounded_rationale: str = _BOUNDED_RATIONALE
    scenario_frame: str = _BOUNDED_TEXT

    # Ordered methodology content (all required, min 1 each)
    steps: tuple[PathStep, ...] = Field(min_length=1)
    considerations: tuple[Consideration, ...] = Field(min_length=1)
    missing_information: tuple[MissingInformation, ...] = Field(min_length=1)
    disconfirming_conditions: tuple[DisconfirmingCondition, ...] = Field(min_length=1)
    validation_questions: tuple[ValidationQuestion, ...] = Field(min_length=1)

    # Optional explicit conflicts
    conflicts: tuple[PathConflict, ...] = Field(default_factory=tuple)

    # Immutable truth bundle (shared definition from decision_workspace)
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    truth_human_respondents: int = Field(default=0, ge=0, le=0)
    truth_is_forecast: bool = False
    truth_output_origin: str = Field(default="synthetic")

    # Content + distinctness hashes
    content_sha256: str = Field(pattern=_SHA256_PATTERN)
    distinctness_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def require_contiguous_step_sequence(self) -> Self:
        actual = tuple(step.sequence for step in self.steps)
        expected = tuple(range(1, len(self.steps) + 1))
        if actual != expected:
            raise ValueError("path_steps_must_be_contiguous_in_tuple_order")
        return self

    @model_validator(mode="after")
    def require_truth_invariants(self) -> Self:
        """The truth bundle is immutable and non-overridable: zero human
        respondents, not a forecast, synthetic origin."""
        if self.truth_human_respondents != 0:
            raise ValueError("truth_human_respondents_must_be_zero")
        if self.truth_is_forecast is not False:
            raise ValueError("truth_is_forecast_must_be_false")
        if self.truth_output_origin != "synthetic":
            raise ValueError("truth_output_origin_must_be_synthetic")
        return self


# --- Path set artifact (the 4–8 path collection) --- #

class PathSetArtifact(BaseModel):
    """A reviewable set of 4–8 materially distinct paths.

    Invariants (validated):
    - 4 to 8 paths.
    - Unique display codes (P-01..P-N in tuple order).
    - Unique content hashes (no paraphrase-only paths).
    - Unique public IDs.
    """
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: UUID
    public_id: str = Field(pattern=r"^path_set_[0-9a-f]{32}$")
    run_id: UUID
    status: PathArtifactStatus
    paths: tuple[PossiblePath, ...] = Field(min_length=4, max_length=8)
    content_sha256: str = Field(pattern=_SHA256_PATTERN)
    created_at: datetime

    @model_validator(mode="after")
    def require_sequential_display_codes(self) -> Self:
        actual = tuple(p.display_code for p in self.paths)
        expected = tuple(f"P-{i:02d}" for i in range(1, len(self.paths) + 1))
        if actual != expected:
            raise ValueError("display_codes_must_be_P01_through_PN_in_tuple_order")
        return self

    @model_validator(mode="after")
    def require_unique_content_hashes(self) -> Self:
        hashes = [p.content_sha256 for p in self.paths]
        if len(set(hashes)) != len(hashes):
            raise ValueError("path_content_hashes_must_be_unique_paraphrase_only_rejected")
        return self

    @model_validator(mode="after")
    def require_unique_distinctness_hashes(self) -> Self:
        hashes = [p.distinctness_sha256 for p in self.paths]
        if len(set(hashes)) != len(hashes):
            raise ValueError("path_distinctness_hashes_must_be_unique")
        return self

    @model_validator(mode="after")
    def require_unique_public_ids(self) -> Self:
        ids = [p.public_id for p in self.paths]
        if len(set(ids)) != len(ids):
            raise ValueError("path_public_ids_must_be_unique")
        return self


# --- Review + brief gate --- #

class PathReviewItem(BaseModel):
    """One path's review disposition."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    path_public_id: str = Field(pattern=r"^path_[0-9a-f]{32}$")
    disposition: PathReviewDisposition
    reviewer_note: str | None = Field(default=None, max_length=500)


class PathSetReview(BaseModel):
    """The human review of a path set artifact."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    path_set_public_id: str = Field(pattern=r"^path_set_[0-9a-f]{32}$")
    reviewed_at: datetime
    reviewer_actor_id: UUID
    items: tuple[PathReviewItem, ...] = Field(min_length=1)
    content_sha256: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def require_all_paths_reviewed(self) -> Self:
        if len(self.items) < 4:
            raise ValueError("all_paths_must_be_reviewed_minimum_four")
        return self


class PathBriefGate(BaseModel):
    """The brief gate: binds the approved path set + review hashes before the
    brief can be generated or the run completed."""
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    path_set_id: UUID
    path_set_content_sha256: str = Field(pattern=_SHA256_PATTERN)
    review_content_sha256: str = Field(pattern=_SHA256_PATTERN)
    gate_passed: bool
    sealed_at: datetime

    @model_validator(mode="after")
    def require_gate_passed_to_seal(self) -> Self:
        if not self.gate_passed:
            raise ValueError("brief_gate_must_pass_before_sealing")
        return self


# --- Hash helpers --- #

def compute_path_content_sha256(path: PossiblePath) -> str:
    """Deterministic SHA-256 of the path's reviewable content (excluding
    identity fields — only the substantive content is hashed)."""
    payload = {
        "display_code": path.display_code,
        "title": path.title,
        "branch_trigger": path.branch_trigger,
        "bounded_rationale": path.bounded_rationale,
        "scenario_frame": path.scenario_frame,
        "steps": [
            {"s": s.sequence, "stmt": s.statement, "rat": s.bounded_rationale}
            for s in path.steps
        ],
        "considerations": [c.statement for c in path.considerations],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def compute_path_distinctness_sha256(path: PossiblePath) -> str:
    """Deterministic SHA-256 of a reduced form used for paraphrase-distinctness
    checking. Two paths with the same distinctness hash are considered
    paraphrase-only duplicates."""
    payload = {
        "title": path.title.lower().strip(),
        "branch_trigger": path.branch_trigger.lower().strip(),
        "steps": [s.statement.lower().strip() for s in path.steps],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
