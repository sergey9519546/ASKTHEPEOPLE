from itertools import product

import pytest
from pydantic import ValidationError

from app.domain.decision_workspace import (
    EpistemicRole,
    ProvenanceEdge,
    ProvenanceRelation,
    ProvenanceViolation,
    validate_provenance_edge,
)

ALLOWED_PROVENANCE_TRIPLES = (
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
)

UNLISTED_PROVENANCE_TRIPLES = tuple(
    triple
    for triple in product(EpistemicRole, ProvenanceRelation, EpistemicRole)
    if triple not in ALLOWED_PROVENANCE_TRIPLES
)


def test_synthetic_truth_bundle_serializes_to_locked_values() -> None:
    from app.domain.decision_workspace import TruthBundle

    assert TruthBundle.synthetic().model_dump() == {
        "output_origin": "synthetic",
        "human_respondent_count": 0,
        "is_forecast": False,
        "is_public_opinion_measure": False,
        "is_causal_evidence": False,
        "source_role": "starting_conditions_only",
        "human_validation_scope": "external_to_synthetic_run",
    }


@pytest.mark.parametrize(
    ("field", "override"),
    [
        ("output_origin", "human"),
        ("human_respondent_count", 1),
        ("is_forecast", True),
        ("is_public_opinion_measure", True),
        ("is_causal_evidence", True),
        ("source_role", "evidence"),
        ("human_validation_scope", "inside_synthetic_run"),
    ],
)
def test_truth_bundle_rejects_overrides_of_locked_values(
    field: str, override: object
) -> None:
    from app.domain.decision_workspace import TruthBundle

    with pytest.raises(ValidationError):
        TruthBundle(**{field: override})


@pytest.mark.parametrize(
    ("field", "alias"),
    [
        ("human_respondent_count", False),
        ("human_respondent_count", 0.0),
        ("human_respondent_count", "0"),
        *[
            (field, alias)
            for field in (
                "is_forecast",
                "is_public_opinion_measure",
                "is_causal_evidence",
            )
            for alias in (0, 1, "false", "true")
        ],
        ("output_origin", b"synthetic"),
        ("source_role", b"starting_conditions_only"),
        ("human_validation_scope", b"external_to_synthetic_run"),
    ],
)
def test_truth_bundle_rejects_coercion_and_equality_aliases(
    field: str, alias: object
) -> None:
    from app.domain.decision_workspace import TruthBundle

    with pytest.raises(ValidationError):
        TruthBundle(**{field: alias})


def test_source_segment_may_inform_starting_condition() -> None:
    from app.domain.decision_workspace import (
        EpistemicRole,
        ProvenanceEdge,
        ProvenanceRelation,
        validate_provenance_edge,
    )

    edge = ProvenanceEdge(
        source_id="segment-1",
        source_role=EpistemicRole.SOURCE_SEGMENT,
        target_id="condition-1",
        target_role=EpistemicRole.STARTING_CONDITION,
        relation=ProvenanceRelation.INFORMS,
    )

    assert validate_provenance_edge(edge) is None


@pytest.mark.parametrize(
    ("source_role", "relation", "target_role"),
    ALLOWED_PROVENANCE_TRIPLES,
)
def test_all_allowed_provenance_triples_pass(
    source_role: EpistemicRole,
    relation: ProvenanceRelation,
    target_role: EpistemicRole,
) -> None:
    edge = ProvenanceEdge(
        source_id="source-1",
        source_role=source_role,
        target_id="target-1",
        target_role=target_role,
        relation=relation,
    )

    assert validate_provenance_edge(edge) is None


@pytest.mark.parametrize(
    ("source_role", "relation", "target_role"),
    UNLISTED_PROVENANCE_TRIPLES,
)
def test_cartesian_complement_of_provenance_triples_fails_closed(
    source_role: EpistemicRole,
    relation: ProvenanceRelation,
    target_role: EpistemicRole,
) -> None:
    edge = ProvenanceEdge(
        source_id="source-1",
        source_role=source_role,
        target_id="target-1",
        target_role=target_role,
        relation=relation,
    )

    with pytest.raises(ProvenanceViolation, match="^provenance_edge_forbidden$"):
        validate_provenance_edge(edge)


def test_source_segment_may_not_inform_possible_path() -> None:
    from app.domain.decision_workspace import (
        EpistemicRole,
        ProvenanceEdge,
        ProvenanceRelation,
        ProvenanceViolation,
        validate_provenance_edge,
    )

    edge = ProvenanceEdge(
        source_id="segment-1",
        source_role=EpistemicRole.SOURCE_SEGMENT,
        target_id="path-1",
        target_role=EpistemicRole.POSSIBLE_PATH,
        relation=ProvenanceRelation.INFORMS,
    )

    with pytest.raises(ProvenanceViolation, match="^provenance_edge_forbidden$"):
        validate_provenance_edge(edge)


def test_arbitrary_unlisted_provenance_edge_is_forbidden() -> None:
    from app.domain.decision_workspace import (
        EpistemicRole,
        ProvenanceEdge,
        ProvenanceRelation,
        ProvenanceViolation,
        validate_provenance_edge,
    )

    edge = ProvenanceEdge(
        source_id="decision-1",
        source_role=EpistemicRole.DECISION,
        target_id="asset-1",
        target_role=EpistemicRole.SOURCE_ASSET,
        relation=ProvenanceRelation.DEFINES,
    )

    with pytest.raises(ProvenanceViolation, match="^provenance_edge_forbidden$"):
        validate_provenance_edge(edge)


def test_possible_path_includes_ordered_synthetic_steps_and_truth() -> None:
    from app.domain.decision_workspace import (
        EpistemicOrigin,
        PathStep,
        PossiblePath,
        TruthBundle,
    )

    step = PathStep(
        id="step-1",
        sequence=1,
        statement="A plausible consequence is explored.",
        origin=EpistemicOrigin.SYNTHETIC_GENERATED,
    )
    path = PossiblePath(
        id="path-1",
        run_id="run-1",
        label="P-01",
        branch_reason="A declared assumption creates this branch.",
        origin=EpistemicOrigin.SYNTHETIC_GENERATED,
        steps=(step,),
    )

    assert path.steps == (step,)
    assert path.truth == TruthBundle.synthetic()
    assert path.truth.model_dump() == TruthBundle.synthetic().model_dump()


@pytest.mark.parametrize(
    ("field", "invalid_id"),
    [
        ("step_id", ""),
        ("step_id", "x" * 129),
        ("path_id", ""),
        ("path_id", "x" * 129),
        ("run_id", ""),
        ("run_id", "x" * 129),
    ],
)
def test_possible_path_rejects_invalid_stable_ids(
    field: str, invalid_id: str
) -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep, PossiblePath

    step_data = {
        "id": "step-1",
        "sequence": 1,
        "statement": "A plausible consequence is explored.",
        "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
    }
    path_data = {
        "id": "path-1",
        "run_id": "run-1",
        "label": "P-01",
        "branch_reason": "A declared assumption creates this branch.",
        "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
    }

    with pytest.raises(ValidationError):
        if field == "step_id":
            PathStep(**{**step_data, "id": invalid_id})
        else:
            path_field = "id" if field == "path_id" else "run_id"
            PossiblePath(
                **{**path_data, path_field: invalid_id},
                steps=(PathStep(**step_data),),
            )


@pytest.mark.parametrize(
    "invalid_id",
    [" ", "id with space", "id/slash", "id\x00control", "Ａ"],
)
@pytest.mark.parametrize(
    "field", ["step_id", "path_id", "run_id", "source_id", "target_id"]
)
def test_server_ids_reject_non_canonical_shapes(field: str, invalid_id: str) -> None:
    from app.domain.decision_workspace import (
        EpistemicOrigin,
        EpistemicRole,
        PathStep,
        PossiblePath,
        ProvenanceEdge,
        ProvenanceRelation,
    )

    step_data = {
        "id": "step-1",
        "sequence": 1,
        "statement": "A plausible consequence is explored.",
        "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
    }

    with pytest.raises(ValidationError):
        if field == "step_id":
            PathStep(**{**step_data, "id": invalid_id})
        elif field in {"path_id", "run_id"}:
            path_field = "id" if field == "path_id" else "run_id"
            PossiblePath(
                **{
                    "id": "path-1",
                    "run_id": "run-1",
                    "label": "P-01",
                    "branch_reason": "A declared assumption creates this branch.",
                    "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
                    path_field: invalid_id,
                },
                steps=(PathStep(**step_data),),
            )
        else:
            edge_field = "source_id" if field == "source_id" else "target_id"
            ProvenanceEdge(
                **{
                    "source_id": "segment-1",
                    "source_role": EpistemicRole.SOURCE_SEGMENT,
                    "target_id": "condition-1",
                    "target_role": EpistemicRole.STARTING_CONDITION,
                    "relation": ProvenanceRelation.INFORMS,
                    edge_field: invalid_id,
                }
            )


@pytest.mark.parametrize("invalid_label", ["P-1", "P-001", "PATH-01"])
def test_possible_path_rejects_labels_outside_p_number_format(
    invalid_label: str,
) -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep, PossiblePath

    step = PathStep(
        id="step-1",
        sequence=1,
        statement="A plausible consequence is explored.",
        origin=EpistemicOrigin.SYNTHETIC_GENERATED,
    )

    with pytest.raises(ValidationError):
        PossiblePath(
            id="path-1",
            run_id="run-1",
            label=invalid_label,
            branch_reason="A declared assumption creates this branch.",
            origin=EpistemicOrigin.SYNTHETIC_GENERATED,
            steps=(step,),
        )


def test_possible_path_requires_at_least_one_step() -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PossiblePath

    with pytest.raises(ValidationError):
        PossiblePath(
            id="path-1",
            run_id="run-1",
            label="P-01",
            branch_reason="A declared assumption creates this branch.",
            origin=EpistemicOrigin.SYNTHETIC_GENERATED,
            steps=(),
        )


def test_path_step_sequence_starts_at_one() -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep

    with pytest.raises(ValidationError):
        PathStep(
            id="step-1",
            sequence=0,
            statement="A plausible consequence is explored.",
            origin=EpistemicOrigin.SYNTHETIC_GENERATED,
        )


@pytest.mark.parametrize("sequences", [(2, 1), (1, 1), (1, 3), (2,)])
def test_possible_path_requires_contiguous_step_sequence_in_tuple_order(
    sequences: tuple[int, ...],
) -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep, PossiblePath

    steps = tuple(
        PathStep(
            id=f"step-{index}",
            sequence=sequence,
            statement=f"Synthetic step {index}.",
            origin=EpistemicOrigin.SYNTHETIC_GENERATED,
        )
        for index, sequence in enumerate(sequences, start=1)
    )

    with pytest.raises(ValidationError):
        PossiblePath(
            id="path-1",
            run_id="run-1",
            label="P-01",
            branch_reason="A declared assumption creates this branch.",
            origin=EpistemicOrigin.SYNTHETIC_GENERATED,
            steps=steps,
        )


@pytest.mark.parametrize("model_name", ["step", "path"])
def test_possible_paths_and_steps_require_synthetic_origin(model_name: str) -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep, PossiblePath

    step_data = {
        "id": "step-1",
        "sequence": 1,
        "statement": "A plausible consequence is explored.",
        "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
    }

    with pytest.raises(ValidationError):
        if model_name == "step":
            PathStep(**{**step_data, "origin": EpistemicOrigin.USER_STATED})
        else:
            PossiblePath(
                id="path-1",
                run_id="run-1",
                label="P-01",
                branch_reason="A declared assumption creates this branch.",
                origin=EpistemicOrigin.USER_STATED,
                steps=(PathStep(**step_data),),
            )


@pytest.mark.parametrize(
    ("model_name", "invalid_statement"),
    [
        ("step", ""),
        ("step", "x" * 1201),
        ("path", ""),
        ("path", "x" * 1201),
    ],
)
def test_possible_path_text_fields_enforce_contract_limits(
    model_name: str, invalid_statement: str
) -> None:
    from app.domain.decision_workspace import EpistemicOrigin, PathStep, PossiblePath

    step_data = {
        "id": "step-1",
        "sequence": 1,
        "statement": "A plausible consequence is explored.",
        "origin": EpistemicOrigin.SYNTHETIC_GENERATED,
    }

    with pytest.raises(ValidationError):
        if model_name == "step":
            PathStep(**{**step_data, "statement": invalid_statement})
        else:
            PossiblePath(
                id="path-1",
                run_id="run-1",
                label="P-01",
                branch_reason=invalid_statement,
                origin=EpistemicOrigin.SYNTHETIC_GENERATED,
                steps=(PathStep(**step_data),),
            )


@pytest.mark.parametrize("model_name", ["truth", "edge", "step", "path"])
def test_domain_models_reject_assignment(model_name: str) -> None:
    from app.domain.decision_workspace import (
        EpistemicOrigin,
        EpistemicRole,
        PathStep,
        PossiblePath,
        ProvenanceEdge,
        ProvenanceRelation,
        TruthBundle,
    )

    step = PathStep(
        id="step-1",
        sequence=1,
        statement="A plausible consequence is explored.",
        origin=EpistemicOrigin.SYNTHETIC_GENERATED,
    )
    models_and_assignments = {
        "truth": (TruthBundle.synthetic(), "output_origin", "human"),
        "edge": (
            ProvenanceEdge(
                source_id="segment-1",
                source_role=EpistemicRole.SOURCE_SEGMENT,
                target_id="condition-1",
                target_role=EpistemicRole.STARTING_CONDITION,
                relation=ProvenanceRelation.INFORMS,
            ),
            "source_id",
            "segment-2",
        ),
        "step": (step, "statement", "A changed statement."),
        "path": (
            PossiblePath(
                id="path-1",
                run_id="run-1",
                label="P-01",
                branch_reason="A declared assumption creates this branch.",
                origin=EpistemicOrigin.SYNTHETIC_GENERATED,
                steps=(step,),
            ),
            "label",
            "P-02",
        ),
    }
    model, field, value = models_and_assignments[model_name]

    with pytest.raises(ValidationError):
        setattr(model, field, value)
