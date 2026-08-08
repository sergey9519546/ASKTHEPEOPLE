"""Controlled source-ingestion domain tests."""

from datetime import UTC, datetime
from hashlib import sha256
from itertools import product

import pytest
from pydantic import ValidationError

AUTHORIZED_SOURCE_TRANSITIONS = (
    ("UPLOADING", "QUARANTINED", "COMPLETE_SOURCE_UPLOAD"),
    ("UPLOADING", "FAILED", "FAIL_SOURCE_UPLOAD"),
    ("QUARANTINED", "SCANNING", "BEGIN_SOURCE_SCAN"),
    ("QUARANTINED", "REJECTED", "RECORD_SOURCE_QUARANTINE_REJECTION"),
    ("SCANNING", "PARSING", "RECORD_SOURCE_SCAN_PASS"),
    ("SCANNING", "REJECTED", "RECORD_SOURCE_SCAN_REJECTION"),
    ("SCANNING", "FAILED", "RECORD_SOURCE_SCAN_FAILURE"),
    ("PARSING", "FLAGGED", "RECORD_SOURCE_PARSE_FLAGGED"),
    ("PARSING", "NEEDS_REVIEW", "RECORD_SOURCE_PARSE_REVIEWABLE"),
    ("PARSING", "REJECTED", "RECORD_SOURCE_PARSE_REJECTION"),
    ("PARSING", "FAILED", "RECORD_SOURCE_PARSE_FAILURE"),
    ("FLAGGED", "NEEDS_REVIEW", "COMPLETE_SOURCE_FLAG_RELEASE"),
    ("FLAGGED", "NEEDS_REVIEW", "RELEASE_REVIEW_REPORTED_FLAG"),
    ("FLAGGED", "REJECTED", "REJECT_FLAGGED_SOURCE"),
    ("NEEDS_REVIEW", "READY", "FINALIZE_SOURCE_REVIEW"),
    ("NEEDS_REVIEW", "REJECTED", "REJECT_SOURCE_REVIEW"),
    ("NEEDS_REVIEW", "FLAGGED", "REPORT_SOURCE_CANDIDATE_SUSPICIOUS"),
    ("DELETION_PENDING", "DELETED", "COMPLETE_SOURCE_DELETION"),
    *((state, "DELETION_PENDING", "REQUEST_SOURCE_DELETION") for state in (
        "UPLOADING", "QUARANTINED", "SCANNING", "PARSING", "FLAGGED",
        "NEEDS_REVIEW", "READY", "REJECTED", "FAILED",
    )),
)


def _passing_source_guard_data() -> dict[str, bool]:
    return {
        "upload_verified": True,
        "format_enabled": True,
        "exact_object_key_exists": True,
        "byte_length_matches": True,
        "sha256_matches": True,
        "object_private": True,
        "upload_intent_unexpired": True,
        "operational_failure_recorded": True,
        "policy_rejection_recorded": True,
        "open_flags_rejected": True,
        "open_flag_created": True,
        "deletion_request_committed": True,
        "deletion_fence_committed": True,
        "upload_intent_revoked": True,
        "queued_work_cancelled": True,
        "deletion_target_inventory_complete": True,
        "worker_lease_valid": True,
        "scanner_definitions_fresh": True,
        "scan_clean_receipt_stored": True,
        "scan_result_clean": True,
        "source_limits_pass": True,
        "parse_artifacts_durable": True,
        "candidates_durable": True,
        "prompt_model_schema_records_durable": True,
        "artifact_hashes_durable": True,
        "no_open_flags": True,
        "flags_released": True,
        "candidate_reset": True,
        "all_candidates_terminal": True,
        "review_records_durable": True,
        "deletion_targets_resolved": True,
    }


def test_uploading_may_transition_to_quarantined() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.UPLOADING,
        SourceIngestionState.QUARANTINED,
        SourceCommandKind.COMPLETE_SOURCE_UPLOAD,
        SourceTransitionGuardFacts(
            upload_verified=True,
            format_enabled=True,
            exact_object_key_exists=True,
            byte_length_matches=True,
            sha256_matches=True,
            object_private=True,
            upload_intent_unexpired=True,
        ),
    )

    assert result is SourceIngestionState.QUARANTINED


def test_scanning_operational_exhaustion_transitions_to_failed() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.SCANNING,
        SourceIngestionState.FAILED,
        SourceCommandKind.RECORD_SOURCE_SCAN_FAILURE,
        SourceTransitionGuardFacts(operational_failure_recorded=True),
    )

    assert result is SourceIngestionState.FAILED


def test_parsing_policy_violation_transitions_to_rejected() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.PARSING,
        SourceIngestionState.REJECTED,
        SourceCommandKind.RECORD_SOURCE_PARSE_REJECTION,
        SourceTransitionGuardFacts(policy_rejection_recorded=True),
    )

    assert result is SourceIngestionState.REJECTED


def test_parsing_operational_exhaustion_transitions_to_failed() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.PARSING,
        SourceIngestionState.FAILED,
        SourceCommandKind.RECORD_SOURCE_PARSE_FAILURE,
        SourceTransitionGuardFacts(operational_failure_recorded=True),
    )

    assert result is SourceIngestionState.FAILED


def test_flagged_source_may_be_rejected() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.FLAGGED,
        SourceIngestionState.REJECTED,
        SourceCommandKind.REJECT_FLAGGED_SOURCE,
        SourceTransitionGuardFacts(open_flags_rejected=True),
    )

    assert result is SourceIngestionState.REJECTED


def test_suspicious_review_report_transitions_to_flagged() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState.NEEDS_REVIEW,
        SourceIngestionState.FLAGGED,
        SourceCommandKind.REPORT_SOURCE_CANDIDATE_SUSPICIOUS,
        SourceTransitionGuardFacts(open_flag_created=True),
    )

    assert result is SourceIngestionState.FLAGGED


@pytest.mark.parametrize(
    "current_state",
    [
        "UPLOADING",
        "QUARANTINED",
        "SCANNING",
        "PARSING",
        "FLAGGED",
        "NEEDS_REVIEW",
        "READY",
        "REJECTED",
        "FAILED",
    ],
)
def test_every_non_deleting_state_may_enter_deletion_pending(
    current_state: str,
) -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    result = transition_source_version(
        SourceIngestionState(current_state),
        SourceIngestionState.DELETION_PENDING,
        SourceCommandKind.REQUEST_SOURCE_DELETION,
        SourceTransitionGuardFacts(
            deletion_request_committed=True,
            deletion_fence_committed=True,
            upload_intent_revoked=True,
            queued_work_cancelled=True,
            deletion_target_inventory_complete=True,
        ),
    )

    assert result is SourceIngestionState.DELETION_PENDING


def test_unlisted_source_transition_fails_closed() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        SourceTransitionViolation,
        transition_source_version,
    )

    with pytest.raises(SourceTransitionViolation, match="^source_transition_forbidden$"):
        transition_source_version(
            SourceIngestionState.UPLOADING,
            SourceIngestionState.READY,
            SourceCommandKind.COMPLETE_SOURCE_UPLOAD,
            SourceTransitionGuardFacts(**_passing_source_guard_data()),
        )


@pytest.mark.parametrize(
    ("current", "target", "command"),
    AUTHORIZED_SOURCE_TRANSITIONS,
)
def test_all_authorized_source_transitions_match_reconciled_closed_set(
    current: str,
    target: str,
    command: str,
) -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        transition_source_version,
    )

    assert transition_source_version(
        SourceIngestionState(current),
        SourceIngestionState(target),
        SourceCommandKind[command],
        SourceTransitionGuardFacts(**_passing_source_guard_data()),
    ) is SourceIngestionState(target)


def test_cartesian_complement_of_source_transitions_is_forbidden() -> None:
    from app.domain.source_ingestion import (
        SourceIngestionState,
        SourceTransitionViolation,
        validate_source_state_pair,
    )

    allowed = {
        (SourceIngestionState(current), SourceIngestionState(target))
        for current, target, _command in AUTHORIZED_SOURCE_TRANSITIONS
    }
    for current, target in product(SourceIngestionState, repeat=2):
        if (current, target) in allowed:
            assert validate_source_state_pair(current, target) is None
            continue
        with pytest.raises(
            SourceTransitionViolation,
            match="^source_transition_forbidden$",
        ):
            validate_source_state_pair(current, target)


def test_ready_allows_zero_candidates_but_rejects_nonterminal_candidates() -> None:
    from app.domain.source_ingestion import (
        CandidateDisposition,
        candidate_review_is_finalizable,
    )

    assert candidate_review_is_finalizable((), open_flag_count=0)
    assert not candidate_review_is_finalizable(
        (CandidateDisposition.PENDING,), open_flag_count=0
    )
    assert not candidate_review_is_finalizable(
        (CandidateDisposition.ACCEPTED_SOURCE_CONDITION,), open_flag_count=1
    )


def test_unchanged_acceptance_preserves_source_origin_and_informs_edge() -> None:
    from app.domain.decision_workspace import (
        EpistemicOrigin,
        ProvenanceRelation,
    )
    from app.domain.source_ingestion import accept_candidate_unchanged

    result = accept_candidate_unchanged(
        candidate_id="cand_1",
        segment_id="seg_1",
        condition_id="cond_1",
        extracted_statement="Weekend service is currently hourly.",
        extracted_statement_sha256=sha256(
            b"Weekend service is currently hourly."
        ).hexdigest(),
        accepted_statement="Weekend service is currently hourly.",
    )
    assert result.condition_origin is EpistemicOrigin.SOURCE_EXTRACTED
    assert {edge.relation for edge in result.edges} == {
        ProvenanceRelation.EXTRACTED_FROM,
        ProvenanceRelation.ACCEPTED_AS,
        ProvenanceRelation.INFORMS,
    }


def test_revision_becomes_user_stated_and_never_claims_source_informs_it() -> None:
    from app.domain.decision_workspace import (
        EpistemicOrigin,
        ProvenanceRelation,
    )
    from app.domain.source_ingestion import revise_candidate

    result = revise_candidate(
        candidate_id="cand_1",
        segment_id="seg_1",
        condition_id="cond_1",
        extracted_statement="Weekend service is currently hourly.",
        extracted_statement_sha256=sha256(
            b"Weekend service is currently hourly."
        ).hexdigest(),
        revised_statement="Weekend service is usually hourly.",
    )
    assert result.condition_origin is EpistemicOrigin.USER_STATED
    assert {edge.relation for edge in result.edges} == {
        ProvenanceRelation.EXTRACTED_FROM,
        ProvenanceRelation.REVISED_AS,
    }


def test_acceptance_and_revision_require_semantically_distinct_operations() -> None:
    from app.domain.source_ingestion import SourceReviewViolation, revise_candidate

    with pytest.raises(SourceReviewViolation, match="^revision_must_change_statement$"):
        revise_candidate(
            candidate_id="cand_1",
            segment_id="seg_1",
            condition_id="cond_1",
            extracted_statement="Exact statement",
            extracted_statement_sha256=sha256(b"Exact statement").hexdigest(),
            revised_statement="Exact statement",
        )


def test_deletion_completion_rejects_any_unresolved_target() -> None:
    from app.domain.source_ingestion import (
        DeletionTargetState,
        SourceReviewViolation,
        validate_deletion_completion,
    )

    with pytest.raises(SourceReviewViolation, match="^deletion_targets_unresolved$"):
        validate_deletion_completion(
            (DeletionTargetState.CONFIRMED, DeletionTargetState.PENDING),
            primary_content_absent=True,
        )
    with pytest.raises(SourceReviewViolation, match="^deletion_inventory_required$"):
        validate_deletion_completion((), primary_content_absent=True)
    with pytest.raises(SourceReviewViolation, match="^primary_content_still_present$"):
        validate_deletion_completion(
            (DeletionTargetState.CONFIRMED,), primary_content_absent=False
        )
    assert validate_deletion_completion(
        (
            DeletionTargetState.CONFIRMED,
            DeletionTargetState.NOT_APPLICABLE,
            DeletionTargetState.SCHEDULED_AGE_OUT,
        ),
        primary_content_absent=True,
        scheduled_expiry_disclosed=True,
    ) is None


def test_exact_source_review_and_deletion_vocabulary() -> None:
    from app.domain.source_ingestion import (
        CandidateDisposition,
        DeletionTargetKind,
        DeletionTargetState,
        ReviewFlagDisposition,
        SourceAttemptState,
        SourceProcessingStage,
    )

    assert {item.value for item in CandidateDisposition} == {
        "PENDING", "ACCEPTED_SOURCE_CONDITION", "REVISED_USER_CONDITION",
        "EXCLUDED", "REPORTED_SUSPICIOUS",
    }
    assert {item.value for item in ReviewFlagDisposition} == {"OPEN", "RELEASED", "REJECTED"}
    assert {item.value for item in SourceProcessingStage} == {"SCAN", "PARSE", "EXTRACT"}
    assert {item.value for item in SourceAttemptState} == {
        "READY", "RUNNING", "RETRY_WAIT", "SUCCEEDED", "FAILED_TERMINAL", "CANCELLED",
    }
    assert len(DeletionTargetKind) == 9
    assert {item.value for item in DeletionTargetState} == {
        "PENDING", "IN_PROGRESS", "CONFIRMED", "SCHEDULED_AGE_OUT", "FAILED",
        "NOT_APPLICABLE", "LEGAL_HOLD",
    }


def test_acceptance_is_bound_to_persisted_canonical_hash() -> None:
    from app.domain.source_ingestion import (
        SourceReviewViolation,
        accept_candidate_unchanged,
    )

    statement = "Weekend service is currently hourly."
    digest = sha256(statement.encode("utf-8")).hexdigest()
    result = accept_candidate_unchanged(
        candidate_id="cand_1", segment_id="seg_1", condition_id="cond_1",
        extracted_statement=statement, extracted_statement_sha256=digest,
        accepted_statement=statement,
    )
    assert result.condition_statement_sha256 == digest
    with pytest.raises(SourceReviewViolation, match="^candidate_statement_hash_mismatch$"):
        accept_candidate_unchanged(
            candidate_id="cand_1", segment_id="seg_1", condition_id="cond_1",
            extracted_statement=statement, extracted_statement_sha256="0" * 64,
            accepted_statement=statement,
        )


def test_checkpoint_4a_aggregate_identity_and_scope_are_strict() -> None:
    from app.domain.identifiers import new_public_id, new_uuid7
    from app.domain.source_ingestion import SourceRecord

    ids = iter(new_uuid7(clock=lambda n=n: 1_900_000_000 + n, randbits=lambda _: 1) for n in range(6))
    physical = next(ids)
    record = SourceRecord(
        id=physical,
        public_id=new_public_id("source", physical, uuid7_factory=lambda: next(ids)),
        organization_id=next(ids), workspace_id=next(ids), project_id=next(ids),
        display_name="Transit evidence", version=1,
        created_by_actor_id=next(ids), created_at=datetime(2030, 1, 1, tzinfo=UTC),
        updated_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert record.public_id.startswith("src_")
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**record.model_dump(), "version": "1"})


def test_security_guards_require_decomposed_server_facts() -> None:
    from app.domain.source_ingestion import (
        SourceCommandKind,
        SourceIngestionState,
        SourceTransitionGuardFacts,
        SourceTransitionGuardViolation,
        transition_source_version,
    )

    with pytest.raises(SourceTransitionGuardViolation, match="^source_upload_guard_failed$"):
        transition_source_version(
            SourceIngestionState.UPLOADING, SourceIngestionState.QUARANTINED,
            SourceCommandKind.COMPLETE_SOURCE_UPLOAD,
            SourceTransitionGuardFacts(upload_verified=True, format_enabled=True),
        )
    with pytest.raises(SourceTransitionGuardViolation, match="^clean_scan_receipt_required$"):
        transition_source_version(
            SourceIngestionState.SCANNING, SourceIngestionState.PARSING,
            SourceCommandKind.RECORD_SOURCE_SCAN_PASS,
            SourceTransitionGuardFacts(scan_clean_receipt_stored=True),
        )


def test_source_command_context_is_strict_frozen_and_server_scoped() -> None:
    from datetime import UTC, datetime

    from app.domain.identifiers import new_uuid7
    from app.domain.source_ingestion import SourceCommandContext

    identifier = new_uuid7(clock=lambda: 1_900_000_000, randbits=lambda _: 1)
    context = SourceCommandContext(
        actor_type="USER",
        actor_id=identifier,
        organization_id=identifier,
        workspace_id=identifier,
        project_id=identifier,
        request_id=identifier,
        capabilities=frozenset({"source:review"}),
        expected_version=1,
        idempotency_key="source-review-0001",
        reason_code="USER_ACCEPTED_SOURCE",
        occurred_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ValidationError):
        SourceCommandContext.model_validate(
            {
                **context.model_dump(),
                "occurred_at": datetime(2030, 1, 1, tzinfo=UTC).replace(tzinfo=None),
            }
        )
    with pytest.raises(ValidationError):
        SourceCommandContext.model_validate(
            {**context.model_dump(), "expected_version": "1"}
        )
    with pytest.raises(ValidationError):
        context.expected_version = 2
