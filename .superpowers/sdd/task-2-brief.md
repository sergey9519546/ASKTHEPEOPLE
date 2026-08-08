# Task 2 brief — Typed product-truth and provenance contracts

Read this first. It is the complete requirement for this task.

## Deliverable

Create a small, dependency-light domain module that makes the immutable
synthetic truth boundary and allowed provenance relationships impossible to
represent with arbitrary strings.

## Files

- Create `backend/app/domain/__init__.py`.
- Create `backend/app/domain/decision_workspace.py`.
- Create `backend/tests/domain/__init__.py`.
- Create `backend/tests/domain/test_decision_workspace.py`.
- Do not modify any existing route or persistence file.

## Required public interfaces

```python
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
    model_config = ConfigDict(frozen=True, extra="forbid")
    output_origin: Literal["synthetic"] = "synthetic"
    human_respondent_count: Literal[0] = 0
    is_forecast: Literal[False] = False
    is_public_opinion_measure: Literal[False] = False
    is_causal_evidence: Literal[False] = False
    source_role: Literal["starting_conditions_only"] = "starting_conditions_only"
    human_validation_scope: Literal["external_to_synthetic_run"] = "external_to_synthetic_run"

    @classmethod
    def synthetic(cls) -> "TruthBundle": ...

class ProvenanceEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: str = Field(min_length=1, max_length=128)
    source_role: EpistemicRole
    target_id: str = Field(min_length=1, max_length=128)
    target_role: EpistemicRole
    relation: ProvenanceRelation

class PathStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=1)
    statement: str = Field(min_length=1, max_length=1200)
    origin: Literal[EpistemicOrigin.SYNTHETIC_GENERATED]

class PossiblePath(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    label: str = Field(pattern=r"^P-\d{2}$")
    branch_reason: str = Field(min_length=1, max_length=1200)
    origin: Literal[EpistemicOrigin.SYNTHETIC_GENERATED]
    steps: tuple[PathStep, ...] = Field(min_length=1)
    truth: TruthBundle = Field(default_factory=TruthBundle.synthetic)

class ProvenanceViolation(ValueError): ...

def validate_provenance_edge(edge: ProvenanceEdge) -> None: ...
```

## Allowed provenance edges

Use a closed allowlist. Every unlisted triple is rejected.

```text
SOURCE_ASSET --CONTAINS--> SOURCE_SEGMENT
SOURCE_SEGMENT --SUPPORTS--> STARTING_CONDITION
USER decision --DECLARES--> ASSUMPTION
ASSUMPTION --BRANCHES_TO--> POSSIBLE_PATH
UNCERTAINTY_STATE --BRANCHES_TO--> POSSIBLE_PATH
POSSIBLE_PATH --CONTAINS--> PATH_STEP
POSSIBLE_PATH --SURFACES--> CONSIDERATION
POSSIBLE_PATH --DISCONFIRMED_BY--> DISCONFIRMING_CONDITION
POSSIBLE_PATH --VALIDATED_BY--> VALIDATION_QUESTION
POSSIBLE_PATH --SUMMARIZED_BY--> BRIEF_STATEMENT
```

Reject `SOURCE_SEGMENT --SUPPORTS--> POSSIBLE_PATH` with the stable message
`source_to_path_forbidden`. Reject every other unlisted triple with the stable
message `provenance_edge_forbidden`.

## Required tests and order

Follow one-test-at-a-time TDD and capture RED then GREEN evidence in the report.

1. `TruthBundle.synthetic()` serializes to all seven locked values.
2. Attempts to override any locked value fail Pydantic validation.
3. `SOURCE_SEGMENT --SUPPORTS--> STARTING_CONDITION` passes.
4. `SOURCE_SEGMENT --SUPPORTS--> POSSIBLE_PATH` raises
   `source_to_path_forbidden`.
5. An arbitrary unlisted edge raises `provenance_edge_forbidden`.
6. A `PossiblePath` requires server-style stable IDs, `P-##`, at least one
   ordered synthetic step, and the complete truth bundle.
7. Frozen models reject assignment.

Run:

```powershell
cd backend
.\.venv\Scripts\pytest tests/domain/test_decision_workspace.py -q
```

Run the repository truth/provenance regression tests after focused tests:

```powershell
cd backend
.\.venv\Scripts\pytest tests/test_provenance_separation.py tests/test_api_schemas.py -q
```

## Constraints

- Do not add `EXTERNAL_HUMAN_EVIDENCE` to V1 origins.
- Do not model likelihood, support scores, confidence, winners, or rankings.
- Do not use generic parent IDs or arbitrary role strings.
- Do not persist, route, or render anything in this task.
- Do not add dependencies.
- Preserve all unrelated dirty work.

## Report

Write a full report to `.superpowers/sdd/task-2-report.md` containing:

- status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
- files changed;
- each RED and GREEN command with the observed result;
- regression-test result;
- self-review findings;
- concerns.

