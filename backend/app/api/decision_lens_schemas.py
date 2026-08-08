"""Strict request-only schemas for the decision-lens review API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.decision_lens import (
    SensitiveAttributeDispositionV1,
    SensitiveAttributeV1,
)

BoundedItem = Annotated[str, Field(min_length=3, max_length=800)]


class DecisionLensEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    purpose: str = Field(min_length=10, max_length=600)
    context: str = Field(min_length=10, max_length=1200)
    goals: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    constraints: tuple[BoundedItem, ...] = Field(min_length=1, max_length=12)
    access_conditions: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    incentives: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    switching_costs: tuple[BoundedItem, ...] = Field(min_length=1, max_length=8)
    information_conditions: tuple[BoundedItem, ...] = Field(
        min_length=1,
        max_length=12,
    )
    decision_criteria: tuple[BoundedItem, ...] = Field(
        min_length=1,
        max_length=10,
    )
    excluded_inferences: tuple[BoundedItem, ...] = Field(
        min_length=1,
        max_length=10,
    )
    uncertainty_notes: tuple[BoundedItem, ...] = Field(
        min_length=1,
        max_length=10,
    )
    input_ref_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    sensitive_attributes: tuple[SensitiveAttributeV1, ...] = Field(
        default_factory=tuple
    )


class LensReviewDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lens_id: str = Field(pattern=r"^lens_[a-z0-9_]{1,64}$")
    disposition: Literal["approved", "rejected"]
    note: str = Field(min_length=1, max_length=1200)
    sensitive_attribute_dispositions: tuple[
        SensitiveAttributeDispositionV1, ...
    ] = Field(default_factory=tuple)


class DecisionLensReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reviewer_assertion: str = Field(min_length=2, max_length=160)
    dispositions: tuple[LensReviewDispositionRequest, ...] = Field(
        min_length=4,
        max_length=8,
    )


__all__ = [
    "DecisionLensEditRequest",
    "DecisionLensReviewRequest",
    "LensReviewDispositionRequest",
]
