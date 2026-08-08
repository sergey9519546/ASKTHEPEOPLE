"""Strict functional decision-lens contracts.

Decision lenses are reviewed scenario constraints. They are not people,
respondents, biographies, psychometric profiles, or population samples.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .decision_workspace import EpistemicOrigin, TruthBundle

_HASH_PATTERN = r"^[0-9a-f]{64}$"
_SERVER_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,159}$"
_LENS_ID_PATTERN = r"^lens_[a-z0-9_]{1,64}$"
_ARTIFACT_ID_PATTERN = r"^dla_[a-f0-9]{32}$"
_REVIEW_ID_PATTERN = r"^dlr_[a-f0-9]{32}$"
_PERSON_NAME_PATTERN = re.compile(
    r"^(?:[A-Z][a-z]+|[A-Z]\.)"
    r"(?:\s+(?:[A-Z][a-z]+|[A-Z]\.)){1,2}$"
)
_FIRST_PERSON_IDENTITY_PATTERN = re.compile(
    r"(?:\b(?:i|me|my|mine|myself)\b|\bi[\'’](?:m|ve|d|ll)\b)",
    re.IGNORECASE,
)
_FUNCTIONAL_TITLE_TERMS = frozenset(
    {
        "access",
        "advisory",
        "budget",
        "committee",
        "compliance",
        "delivery",
        "evaluation",
        "function",
        "governance",
        "implementation",
        "operations",
        "planning",
        "procurement",
        "review",
        "risk",
        "service",
        "strategy",
    }
)


BoundedItem = Annotated[str, Field(min_length=3, max_length=800)]


class DecisionLensValidationError(ValueError):
    """Raised when a lens violates the functional representation contract."""

    def __init__(self, code: str, details: Any | None = None):
        self.code = code
        self.details = details
        super().__init__(code)


class LensStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class InputReferenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    ref_id: str = Field(min_length=1, max_length=160, pattern=_SERVER_ID_PATTERN)
    role: Literal[
        "source_segment",
        "starting_condition",
        "declared_assumption",
        "critical_uncertainty",
        "graph_record",
    ]
    origin: EpistemicOrigin

    @model_validator(mode="after")
    def require_compatible_origin(self) -> Self:
        permitted = {
            "source_segment": {EpistemicOrigin.SOURCE_EXTRACTED},
            "starting_condition": {
                EpistemicOrigin.SOURCE_EXTRACTED,
                EpistemicOrigin.USER_STATED,
                EpistemicOrigin.ASSUMPTION_DECLARED,
            },
            "declared_assumption": {EpistemicOrigin.ASSUMPTION_DECLARED},
            "critical_uncertainty": {
                EpistemicOrigin.USER_STATED,
                EpistemicOrigin.ASSUMPTION_DECLARED,
            },
            "graph_record": {
                EpistemicOrigin.SOURCE_EXTRACTED,
                EpistemicOrigin.SYNTHETIC_GENERATED,
            },
        }
        if self.origin not in permitted[self.role]:
            raise DecisionLensValidationError("input_reference_origin_mismatch")
        return self


class SensitiveAttributeV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    attribute: str = Field(min_length=1, max_length=120)
    decision_relevance: str = Field(min_length=20, max_length=800)
    retention_restriction: str = Field(min_length=10, max_length=400)
    export_restriction: str = Field(min_length=10, max_length=400)


class PromptRecordV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    prompt_id: Literal["decision_lens_generation"]
    prompt_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    prompt_sha256: str = Field(pattern=_HASH_PATTERN)
    model: str = Field(min_length=1, max_length=240)
    system_prompt_sha256: str = Field(pattern=_HASH_PATTERN)
    user_prompt_sha256: str = Field(pattern=_HASH_PATTERN)
    context_prompt_sha256s: tuple[str, ...] = Field(default_factory=tuple)
    output_sha256: str = Field(pattern=_HASH_PATTERN)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(ge=1, le=32768)
    structured_output: Literal[True] = True
    tools_bound: Literal[False] = False

    @field_validator("context_prompt_sha256s")
    @classmethod
    def validate_context_hashes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(re.fullmatch(_HASH_PATTERN, value) is None for value in values):
            raise ValueError("invalid_context_prompt_sha256")
        return values


class DecisionLensV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    lens_id: str = Field(pattern=_LENS_ID_PATTERN)
    title: str = Field(min_length=3, max_length=120)
    purpose: str = Field(min_length=10, max_length=600)
    context: str = Field(min_length=10, max_length=1200)
    goals: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    constraints: tuple[BoundedItem, ...] = Field(min_length=1, max_length=12)
    access_conditions: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    incentives: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    switching_costs: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    information_conditions: tuple[BoundedItem, ...] = Field(min_length=1, max_length=12)
    decision_criteria: tuple[BoundedItem, ...] = Field(min_length=1, max_length=10)
    excluded_inferences: tuple[BoundedItem, ...] = Field(min_length=1, max_length=10)
    uncertainty_notes: tuple[BoundedItem, ...] = Field(min_length=1, max_length=10)
    input_refs: tuple[InputReferenceV1, ...] = Field(min_length=1, max_length=32)
    sensitive_attributes: tuple[SensitiveAttributeV1, ...] = Field(
        default_factory=tuple
    )
    status: Literal[LensStatus.PENDING] = LensStatus.PENDING

    @field_validator("title")
    @classmethod
    def require_functional_title(cls, value: str) -> str:
        normalized_terms = set(re.findall(r"[a-z]+", value.lower()))
        if _PERSON_NAME_PATTERN.fullmatch(value) and not (
            normalized_terms & _FUNCTIONAL_TITLE_TERMS
        ):
            raise DecisionLensValidationError("identity_like_title")
        return value

    @model_validator(mode="after")
    def reject_first_person_identity(self) -> Self:
        values: list[str] = [self.title, self.purpose, self.context]
        for field_name in (
            "goals",
            "constraints",
            "access_conditions",
            "incentives",
            "switching_costs",
            "information_conditions",
            "decision_criteria",
            "excluded_inferences",
            "uncertainty_notes",
        ):
            values.extend(getattr(self, field_name))
        if any(_FIRST_PERSON_IDENTITY_PATTERN.search(value) for value in values):
            raise DecisionLensValidationError("first_person_identity")
        return self


class DecisionLensArtifactV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["decision-lens/v1"] = "decision-lens/v1"
    artifact_id: str = Field(pattern=_ARTIFACT_ID_PATTERN)
    simulation_id: str = Field(min_length=1, max_length=128, pattern=_SERVER_ID_PATTERN)
    revision: int = Field(ge=1)
    created_at: datetime
    prompt_record: PromptRecordV1
    input_refs: tuple[InputReferenceV1, ...] = Field(min_length=1, max_length=256)
    lenses: tuple[DecisionLensV1, ...] = Field(min_length=4, max_length=8)
    truth_fields: TruthBundle = Field(default_factory=TruthBundle.synthetic)
    artifact_sha256: str | None = Field(default=None, pattern=_HASH_PATTERN)

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at_timezone_required")
        return value

    @model_validator(mode="after")
    def validate_artifact_contract(self) -> Self:
        lens_ids = tuple(lens.lens_id for lens in self.lenses)
        if len(set(lens_ids)) != len(lens_ids):
            raise DecisionLensValidationError("duplicate_lens_id")

        top_level_refs = {reference.ref_id for reference in self.input_refs}
        used_refs = {
            reference.ref_id for lens in self.lenses for reference in lens.input_refs
        }
        unresolved = sorted(used_refs - top_level_refs)
        if unresolved:
            raise DecisionLensValidationError(
                "input_reference_unresolved", {"ref_ids": unresolved}
            )

        signatures: dict[str, str] = {}
        for lens in self.lenses:
            signature = _material_signature(lens)
            if signature in signatures:
                raise DecisionLensValidationError(
                    "material_duplicate",
                    {"lens_ids": [signatures[signature], lens.lens_id]},
                )
            signatures[signature] = lens.lens_id

        if self.artifact_sha256 is not None:
            expected = canonical_payload_sha256(self)
            if self.artifact_sha256 != expected:
                raise DecisionLensValidationError("artifact_hash_mismatch")
        return self


class LensDispositionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    lens_id: str = Field(pattern=_LENS_ID_PATTERN)
    disposition: Literal["approved", "rejected"]
    note: str = Field(min_length=1, max_length=1200)
    sensitive_attribute_dispositions: tuple[SensitiveAttributeDispositionV1, ...] = (
        Field(default_factory=tuple)
    )

    @model_validator(mode="after")
    def require_unique_sensitive_attribute_dispositions(self) -> Self:
        attributes = tuple(
            item.attribute for item in self.sensitive_attribute_dispositions
        )
        if len(set(attributes)) != len(attributes):
            raise DecisionLensValidationError(
                "duplicate_sensitive_attribute_disposition"
            )
        return self


class SensitiveAttributeDispositionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    attribute: str = Field(min_length=1, max_length=120)
    disposition: Literal["approved", "rejected"]
    justification: str = Field(min_length=20, max_length=800)


class DecisionLensReviewV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["decision-lens-review/v1"] = "decision-lens-review/v1"
    review_id: str = Field(pattern=_REVIEW_ID_PATTERN)
    simulation_id: str = Field(min_length=1, max_length=128, pattern=_SERVER_ID_PATTERN)
    lens_artifact_id: str = Field(pattern=_ARTIFACT_ID_PATTERN)
    lens_artifact_sha256: str = Field(pattern=_HASH_PATTERN)
    reviewed_at: datetime
    reviewer_assertion: str = Field(min_length=2, max_length=160)
    authentication_strength: Literal[
        "application_bearer_self_attested_reviewer",
        "development_no_auth_self_attested_reviewer",
    ]
    dispositions: tuple[LensDispositionV1, ...] = Field(min_length=4, max_length=8)
    overall_status: Literal["approved", "rejected"]
    review_sha256: str | None = Field(default=None, pattern=_HASH_PATTERN)

    @field_validator("reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at_timezone_required")
        return value

    @model_validator(mode="after")
    def validate_review_contract(self) -> Self:
        lens_ids = tuple(disposition.lens_id for disposition in self.dispositions)
        if len(set(lens_ids)) != len(lens_ids):
            raise DecisionLensValidationError("duplicate_review_lens_id")

        fully_approved = all(
            disposition.disposition == "approved"
            and all(
                item.disposition == "approved"
                for item in disposition.sensitive_attribute_dispositions
            )
            for disposition in self.dispositions
        )
        expected_status = "approved" if fully_approved else "rejected"
        if self.overall_status != expected_status:
            raise DecisionLensValidationError("review_overall_status_mismatch")

        if self.review_sha256 is not None:
            expected = canonical_payload_sha256(self)
            if self.review_sha256 != expected:
                raise DecisionLensValidationError("review_hash_mismatch")
        return self


def canonical_payload_bytes(model: BaseModel) -> bytes:
    """Return canonical JSON bytes, excluding a top-level self-hash field."""

    payload = model.model_dump(
        mode="json",
        exclude={"artifact_sha256", "review_sha256"},
    )
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_payload_sha256(model: BaseModel) -> str:
    return hashlib.sha256(canonical_payload_bytes(model)).hexdigest()


def _material_signature(lens: DecisionLensV1) -> str:
    material = (
        lens.goals,
        lens.constraints,
        lens.access_conditions,
        lens.information_conditions,
        lens.decision_criteria,
    )
    normalized = [
        " ".join(re.findall(r"[a-z0-9]+", value.lower()))
        for group in material
        for value in group
    ]
    return "|".join(normalized)


__all__ = [
    "DecisionLensArtifactV1",
    "DecisionLensReviewV1",
    "DecisionLensV1",
    "DecisionLensValidationError",
    "InputReferenceV1",
    "LensDispositionV1",
    "LensStatus",
    "PromptRecordV1",
    "SensitiveAttributeDispositionV1",
    "SensitiveAttributeV1",
    "canonical_payload_bytes",
    "canonical_payload_sha256",
]
