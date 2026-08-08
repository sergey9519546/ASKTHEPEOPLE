"""Normative epistemic-ledger/v2 contract tests."""

from itertools import product

import pytest
from pydantic import ValidationError

from app.domain.decision_workspace import (
    EpistemicOrigin,
    EpistemicRole,
    ProvenanceEdge,
    ProvenanceRelation,
    ProvenanceViolation,
    validate_provenance_edge,
)

EXPECTED_ORIGINS = (
    "USER_STATED",
    "SOURCE_EXTRACTED",
    "ASSUMPTION_DECLARED",
    "SYNTHETIC_GENERATED",
    "EXTERNAL_HUMAN_EVIDENCE",
    "SYSTEM_METADATA",
)

EXPECTED_ROLES = (
    "USER_STATEMENT",
    "DECISION",
    "SCOPE_CONSTRAINT",
    "SOURCE_ASSET",
    "SOURCE_SEGMENT",
    "EXTRACTION_CANDIDATE",
    "STARTING_CONDITION",
    "ASSUMPTION",
    "CRITICAL_UNCERTAINTY",
    "UNCERTAINTY_STATE",
    "DECISION_LENS",
    "SCENARIO_RULE",
    "POSSIBLE_PATH",
    "PATH_STEP",
    "CONSIDERATION",
    "CONFLICT",
    "MISSING_INFORMATION",
    "DISCONFIRMING_CONDITION",
    "VALIDATION_QUESTION",
    "RELATED_RUN_RECORD",
    "EXTERNAL_HUMAN_FINDING",
    "BRIEF_STATEMENT",
    "DECISION_OWNER_CONCLUSION",
)

EXPECTED_RELATIONS = (
    "CONTAINS",
    "EXTRACTED_FROM",
    "ACCEPTED_AS",
    "REVISED_AS",
    "DEFINES",
    "INFORMS",
    "CONSTRAINS",
    "BRANCHES_ON",
    "APPLIES_LENS",
    "SEQUENCES",
    "SURFACES",
    "DISCONFIRMED_BY",
    "PRODUCES_QUESTION",
    "SUMMARIZES",
)

ALLOWED_TRIPLES = (
    ("SOURCE_ASSET", "CONTAINS", "SOURCE_SEGMENT"),
    ("EXTRACTION_CANDIDATE", "EXTRACTED_FROM", "SOURCE_SEGMENT"),
    ("EXTRACTION_CANDIDATE", "ACCEPTED_AS", "STARTING_CONDITION"),
    ("EXTRACTION_CANDIDATE", "REVISED_AS", "STARTING_CONDITION"),
    ("SOURCE_SEGMENT", "INFORMS", "STARTING_CONDITION"),
    ("USER_STATEMENT", "DEFINES", "DECISION"),
    ("STARTING_CONDITION", "CONSTRAINS", "SCENARIO_RULE"),
    ("POSSIBLE_PATH", "BRANCHES_ON", "ASSUMPTION"),
    ("POSSIBLE_PATH", "BRANCHES_ON", "UNCERTAINTY_STATE"),
    ("DECISION_LENS", "APPLIES_LENS", "PATH_STEP"),
    ("POSSIBLE_PATH", "SEQUENCES", "PATH_STEP"),
    ("POSSIBLE_PATH", "SURFACES", "CONSIDERATION"),
    ("POSSIBLE_PATH", "SURFACES", "CONFLICT"),
    ("POSSIBLE_PATH", "SURFACES", "MISSING_INFORMATION"),
    ("POSSIBLE_PATH", "DISCONFIRMED_BY", "DISCONFIRMING_CONDITION"),
    ("CONSIDERATION", "PRODUCES_QUESTION", "VALIDATION_QUESTION"),
    ("BRIEF_STATEMENT", "SUMMARIZES", "POSSIBLE_PATH"),
    ("BRIEF_STATEMENT", "SUMMARIZES", "CONSIDERATION"),
)


def test_v2_vocabularies_are_exact_and_ordered() -> None:
    assert tuple(member.value for member in EpistemicOrigin) == EXPECTED_ORIGINS
    assert tuple(member.value for member in EpistemicRole) == EXPECTED_ROLES
    assert tuple(member.value for member in ProvenanceRelation) == EXPECTED_RELATIONS


@pytest.mark.parametrize(("source", "relation", "target"), ALLOWED_TRIPLES)
def test_every_v2_triple_is_allowed(
    source: str,
    relation: str,
    target: str,
) -> None:
    edge = ProvenanceEdge(
        source_id="source-1",
        source_role=EpistemicRole(source),
        target_id="target-1",
        target_role=EpistemicRole(target),
        relation=ProvenanceRelation(relation),
    )

    assert edge.contract_version == "epistemic-ledger/v2"
    assert validate_provenance_edge(edge) is None


def test_complete_v2_cartesian_complement_fails_closed() -> None:
    allowed = frozenset(ALLOWED_TRIPLES)
    for source, relation, target in product(EXPECTED_ROLES, EXPECTED_RELATIONS, EXPECTED_ROLES):
        if (source, relation, target) in allowed:
            continue
        edge = ProvenanceEdge(
            source_id="source-1",
            source_role=EpistemicRole(source),
            target_id="target-1",
            target_role=EpistemicRole(target),
            relation=ProvenanceRelation(relation),
        )
        with pytest.raises(ProvenanceViolation, match="^provenance_edge_forbidden$"):
            validate_provenance_edge(edge)


@pytest.mark.parametrize("legacy_relation", ["SUPPORTS", "BRANCHES_TO", "VALIDATED_BY"])
def test_transition_relation_names_are_not_v2_aliases(legacy_relation: str) -> None:
    with pytest.raises(ValueError):
        ProvenanceRelation(legacy_relation)


def test_contract_version_is_locked_to_v2() -> None:
    with pytest.raises(ValidationError):
        ProvenanceEdge(
            contract_version="epistemic-ledger/v1",
            source_id="source-1",
            source_role=EpistemicRole.SOURCE_ASSET,
            target_id="target-1",
            target_role=EpistemicRole.SOURCE_SEGMENT,
            relation=ProvenanceRelation.CONTAINS,
        )
