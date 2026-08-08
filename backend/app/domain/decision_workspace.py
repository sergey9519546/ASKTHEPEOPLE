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
    EXTERNAL_HUMAN_EVIDENCE = "EXTERNAL_HUMAN_EVIDENCE"
    SYSTEM_METADATA = "SYSTEM_METADATA"


class EpistemicRole(str, Enum):
    USER_STATEMENT = "USER_STATEMENT"
    DECISION = "DECISION"
    SCOPE_CONSTRAINT = "SCOPE_CONSTRAINT"
    SOURCE_ASSET = "SOURCE_ASSET"
    SOURCE_SEGMENT = "SOURCE_SEGMENT"
    EXTRACTION_CANDIDATE = "EXTRACTION_CANDIDATE"
    STARTING_CONDITION = "STARTING_CONDITION"
    ASSUMPTION = "ASSUMPTION"
    CRITICAL_UNCERTAINTY = "CRITICAL_UNCERTAINTY"
    UNCERTAINTY_STATE = "UNCERTAINTY_STATE"
    DECISION_LENS = "DECISION_LENS"
    SCENARIO_RULE = "SCENARIO_RULE"
    POSSIBLE_PATH = "POSSIBLE_PATH"
    PATH_STEP = "PATH_STEP"
    CONSIDERATION = "CONSIDERATION"
    CONFLICT = "CONFLICT"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    DISCONFIRMING_CONDITION = "DISCONFIRMING_CONDITION"
    VALIDATION_QUESTION = "VALIDATION_QUESTION"
    RELATED_RUN_RECORD = "RELATED_RUN_RECORD"
    EXTERNAL_HUMAN_FINDING = "EXTERNAL_HUMAN_FINDING"
    BRIEF_STATEMENT = "BRIEF_STATEMENT"
    DECISION_OWNER_CONCLUSION = "DECISION_OWNER_CONCLUSION"


class ProvenanceRelation(str, Enum):
    CONTAINS = "CONTAINS"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    ACCEPTED_AS = "ACCEPTED_AS"
    REVISED_AS = "REVISED_AS"
    DEFINES = "DEFINES"
    INFORMS = "INFORMS"
    CONSTRAINS = "CONSTRAINS"
    BRANCHES_ON = "BRANCHES_ON"
    APPLIES_LENS = "APPLIES_LENS"
    SEQUENCES = "SEQUENCES"
    SURFACES = "SURFACES"
    DISCONFIRMED_BY = "DISCONFIRMED_BY"
    PRODUCES_QUESTION = "PRODUCES_QUESTION"
    SUMMARIZES = "SUMMARIZES"


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

    contract_version: Literal["epistemic-ledger/v2"] = "epistemic-ledger/v2"
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
            EpistemicRole.EXTRACTION_CANDIDATE,
            ProvenanceRelation.EXTRACTED_FROM,
            EpistemicRole.SOURCE_SEGMENT,
        ),
        (
            EpistemicRole.EXTRACTION_CANDIDATE,
            ProvenanceRelation.ACCEPTED_AS,
            EpistemicRole.STARTING_CONDITION,
        ),
        (
            EpistemicRole.EXTRACTION_CANDIDATE,
            ProvenanceRelation.REVISED_AS,
            EpistemicRole.STARTING_CONDITION,
        ),
        (
            EpistemicRole.SOURCE_SEGMENT,
            ProvenanceRelation.INFORMS,
            EpistemicRole.STARTING_CONDITION,
        ),
        (
            EpistemicRole.USER_STATEMENT,
            ProvenanceRelation.DEFINES,
            EpistemicRole.DECISION,
        ),
        (
            EpistemicRole.STARTING_CONDITION,
            ProvenanceRelation.CONSTRAINS,
            EpistemicRole.SCENARIO_RULE,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.BRANCHES_ON,
            EpistemicRole.ASSUMPTION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.BRANCHES_ON,
            EpistemicRole.UNCERTAINTY_STATE,
        ),
        (
            EpistemicRole.DECISION_LENS,
            ProvenanceRelation.APPLIES_LENS,
            EpistemicRole.PATH_STEP,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SEQUENCES,
            EpistemicRole.PATH_STEP,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SURFACES,
            EpistemicRole.CONSIDERATION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SURFACES,
            EpistemicRole.CONFLICT,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.SURFACES,
            EpistemicRole.MISSING_INFORMATION,
        ),
        (
            EpistemicRole.POSSIBLE_PATH,
            ProvenanceRelation.DISCONFIRMED_BY,
            EpistemicRole.DISCONFIRMING_CONDITION,
        ),
        (
            EpistemicRole.CONSIDERATION,
            ProvenanceRelation.PRODUCES_QUESTION,
            EpistemicRole.VALIDATION_QUESTION,
        ),
        (
            EpistemicRole.BRIEF_STATEMENT,
            ProvenanceRelation.SUMMARIZES,
            EpistemicRole.POSSIBLE_PATH,
        ),
        (
            EpistemicRole.BRIEF_STATEMENT,
            ProvenanceRelation.SUMMARIZES,
            EpistemicRole.CONSIDERATION,
        ),
    }
)


def validate_provenance_edge(edge: ProvenanceEdge) -> None:
    provenance_triple = (
        edge.source_role,
        edge.relation,
        edge.target_role,
    )
    if provenance_triple not in _ALLOWED_PROVENANCE_EDGES:
        raise ProvenanceViolation("provenance_edge_forbidden")
