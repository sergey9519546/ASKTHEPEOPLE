"""Typed product-truth and provenance contracts for decision workspaces."""

from enum import Enum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SERVER_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"


class EpistemicOrigin(str, Enum):
    USER_STATED = "USER_STATED"
    SOURCE_EXTRACTED = "SOURCE_EXTRACTED"
    ASSUMPTION_DECLARED = "ASSUMPTION_DECLARED"
    SYNTHETIC_GENERATED = "SYNTHETIC_GENERATED"
    SYSTEM_METADATA = "SYSTEM_METADATA"


class EpistemicRole(str, Enum):
    DECISION = "DECISION"
    SOURCE_ASSET = "SOURCE_ASSET"
    SOURCE_SEGMENT = "SOURCE_SEGMENT"
    STARTING_CONDITION = "STARTING_CONDITION"
    ASSUMPTION = "ASSUMPTION"
    UNCERTAINTY_STATE = "UNCERTAINTY_STATE"
    POSSIBLE_PATH = "POSSIBLE_PATH"
    PATH_STEP = "PATH_STEP"
    CONSIDERATION = "CONSIDERATION"
    DISCONFIRMING_CONDITION = "DISCONFIRMING_CONDITION"
    VALIDATION_QUESTION = "VALIDATION_QUESTION"
    BRIEF_STATEMENT = "BRIEF_STATEMENT"


class ProvenanceRelation(str, Enum):
    EXTRACTED_FROM = "EXTRACTED_FROM"
    SUPPORTS = "SUPPORTS"
    DECLARES = "DECLARES"
    BRANCHES_TO = "BRANCHES_TO"
    CONTAINS = "CONTAINS"
    SURFACES = "SURFACES"
    DISCONFIRMED_BY = "DISCONFIRMED_BY"
    VALIDATED_BY = "VALIDATED_BY"
    SUMMARIZED_BY = "SUMMARIZED_BY"


class TruthBundle(BaseModel):
    """Immutable claims that every synthetic output carries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    output_origin: Literal["synthetic"] = "synthetic"
    human_respondent_count: Literal[0] = 0
    is_forecast: Literal[False] = False
    is_public_opinion_measure: Literal[False] = False
    is_causal_evidence: Literal[False] = False
    source_role: Literal["starting_conditions_only"] = "starting_conditions_only"
    human_validation_scope: Literal[
        "external_to_synthetic_run"
    ] = "external_to_synthetic_run"

    @field_validator("human_respondent_count", mode="before")
    @classmethod
    def require_exact_zero_integer(cls, value: object) -> object:
        if type(value) is not int or value != 0:
            raise ValueError("human_respondent_count_must_be_exact_zero_integer")
        return value

    @field_validator(
        "is_forecast",
        "is_public_opinion_measure",
        "is_causal_evidence",
        mode="before",
    )
    @classmethod
    def require_exact_false_boolean(cls, value: object) -> object:
        if type(value) is not bool or value is not False:
            raise ValueError("truth_flag_must_be_exact_false_boolean")
        return value

    @field_validator(
        "output_origin",
        "source_role",
        "human_validation_scope",
        mode="before",
    )
    @classmethod
    def require_string_primitive(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("truth_string_must_be_exact_string")
        return value

    @classmethod
    def synthetic(cls) -> "TruthBundle":
        return cls()


class PathStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_SERVER_ID_PATTERN,
    )
    sequence: int = Field(ge=1)
    statement: str = Field(min_length=1, max_length=1200)
    origin: Literal[EpistemicOrigin.SYNTHETIC_GENERATED]


class PossiblePath(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_SERVER_ID_PATTERN,
    )
    run_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_SERVER_ID_PATTERN,
    )
    label: str = Field(pattern=r"^P-\d{2}$")
    branch_reason: str = Field(min_length=1, max_length=1200)
    origin: Literal[EpistemicOrigin.SYNTHETIC_GENERATED]
    steps: tuple[PathStep, ...] = Field(min_length=1)
    truth: TruthBundle = Field(default_factory=TruthBundle.synthetic)

    @model_validator(mode="after")
    def require_contiguous_step_sequence(self) -> Self:
        actual = tuple(step.sequence for step in self.steps)
        expected = tuple(range(1, len(self.steps) + 1))
        if actual != expected:
            raise ValueError("path_steps_must_be_contiguous_in_tuple_order")
        return self


class ProvenanceEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_SERVER_ID_PATTERN,
    )
    source_role: EpistemicRole
    target_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_SERVER_ID_PATTERN,
    )
    target_role: EpistemicRole
    relation: ProvenanceRelation


class ProvenanceViolation(ValueError):
    """Raised when an edge violates the closed provenance contract."""


_ALLOWED_PROVENANCE_EDGES = frozenset(
    {
        (
            EpistemicRole.SOURCE_ASSET,
            ProvenanceRelation.CONTAINS,
            EpistemicRole.SOURCE_SEGMENT,
        ),
        (
            EpistemicRole.SOURCE_SEGMENT,
            ProvenanceRelation.SUPPORTS,
            EpistemicRole.STARTING_CONDITION,
        ),
        (
            EpistemicRole.DECISION,
            ProvenanceRelation.DECLARES,
            EpistemicRole.ASSUMPTION,
        ),
        (
            EpistemicRole.ASSUMPTION,
            ProvenanceRelation.BRANCHES_TO,
            EpistemicRole.POSSIBLE_PATH,
        ),
        (
            EpistemicRole.UNCERTAINTY_STATE,
            ProvenanceRelation.BRANCHES_TO,
            EpistemicRole.POSSIBLE_PATH,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.CONTAINS,
            EpistemicRole.PATH_STEP,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SURFACES,
            EpistemicRole.CONSIDERATION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.DISCONFIRMED_BY,
            EpistemicRole.DISCONFIRMING_CONDITION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.VALIDATED_BY,
            EpistemicRole.VALIDATION_QUESTION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SUMMARIZED_BY,
            EpistemicRole.BRIEF_STATEMENT,
        ),
    }
)


def validate_provenance_edge(edge: ProvenanceEdge) -> None:
    provenance_triple = (
        edge.source_role,
        edge.relation,
        edge.target_role,
    )
    if provenance_triple == (
        EpistemicRole.SOURCE_SEGMENT,
        ProvenanceRelation.SUPPORTS,
        EpistemicRole.POSSIBLE_PATH,
    ):
        raise ProvenanceViolation("source_to_path_forbidden")
    if provenance_triple not in _ALLOWED_PROVENANCE_EDGES:
        raise ProvenanceViolation("provenance_edge_forbidden")
