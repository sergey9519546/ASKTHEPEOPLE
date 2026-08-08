import pytest
from pydantic import ValidationError


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


def test_source_segment_may_support_starting_condition() -> None:
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
        relation=ProvenanceRelation.SUPPORTS,
    )

    assert validate_provenance_edge(edge) is None


def test_source_segment_may_not_support_possible_path() -> None:
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
        relation=ProvenanceRelation.SUPPORTS,
    )

    with pytest.raises(ProvenanceViolation, match="^source_to_path_forbidden$"):
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
        relation=ProvenanceRelation.SUPPORTS,
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
                relation=ProvenanceRelation.SUPPORTS,
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
