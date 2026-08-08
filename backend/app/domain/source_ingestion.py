"""Pure contracts for controlled source ingestion and review."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import RFC_4122, UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .decision_workspace import (
    EpistemicOrigin,
    EpistemicRole,
    ProvenanceEdge,
    ProvenanceRelation,
    validate_provenance_edge,
)


class SourceIngestionState(str, Enum):
    UPLOADING = "UPLOADING"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    PARSING = "PARSING"
    FLAGGED = "FLAGGED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY = "READY"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    DELETION_PENDING = "DELETION_PENDING"
    DELETED = "DELETED"


class SourceCommandKind(str, Enum):
    COMPLETE_SOURCE_UPLOAD = "complete_source_upload"
    FAIL_SOURCE_UPLOAD = "fail_source_upload"
    BEGIN_SOURCE_SCAN = "begin_source_scan"
    RECORD_SOURCE_QUARANTINE_REJECTION = "record_source_quarantine_rejection"
    RECORD_SOURCE_SCAN_PASS = "record_source_scan_pass"
    RECORD_SOURCE_SCAN_REJECTION = "record_source_scan_rejection"
    RECORD_SOURCE_SCAN_FAILURE = "record_source_scan_failure"
    RECORD_SOURCE_PARSE_FLAGGED = "record_source_parse_flagged"
    RECORD_SOURCE_PARSE_REVIEWABLE = "record_source_parse_reviewable"
    RECORD_SOURCE_PARSE_REJECTION = "record_source_parse_rejection"
    RECORD_SOURCE_PARSE_FAILURE = "record_source_parse_failure"
    COMPLETE_SOURCE_FLAG_RELEASE = "complete_source_flag_release"
    RELEASE_REVIEW_REPORTED_FLAG = "release_review_reported_flag"
    REJECT_FLAGGED_SOURCE = "reject_flagged_source"
    FINALIZE_SOURCE_REVIEW = "finalize_source_review"
    REJECT_SOURCE_REVIEW = "reject_source_review"
    REPORT_SOURCE_CANDIDATE_SUSPICIOUS = "report_source_candidate_suspicious"
    REQUEST_SOURCE_DELETION = "request_source_deletion"
    COMPLETE_SOURCE_DELETION = "complete_source_deletion"


class CandidateDisposition(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVISED = "REVISED"
    REJECTED = "REJECTED"


class DeletionTargetState(str, Enum):
    PENDING = "PENDING"
    DELETED = "DELETED"
    RETAINED_BY_POLICY = "RETAINED_BY_POLICY"


_TERMINAL_CANDIDATE_DISPOSITIONS = frozenset(
    {
        CandidateDisposition.ACCEPTED,
        CandidateDisposition.REVISED,
        CandidateDisposition.REJECTED,
    }
)


class SourceReviewViolation(ValueError):
    """Raised when review semantics would overstate provenance or completion."""


class SourceCommandContext(BaseModel):
    """Immutable server-derived command envelope for source mutations."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    actor_type: Literal["USER", "SERVICE", "SECURITY_REVIEWER", "DELETION_WORKER"]
    actor_id: UUID
    organization_id: UUID
    workspace_id: UUID
    project_id: UUID
    request_id: UUID
    capabilities: frozenset[str]
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    reason_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime

    @field_validator(
        "actor_id",
        "organization_id",
        "workspace_id",
        "project_id",
        "request_id",
    )
    @classmethod
    def require_uuid7(cls, value: UUID) -> UUID:
        if value.version != 7 or value.variant != RFC_4122:
            raise ValueError("source_context_ids_must_be_uuid7")
        return value

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source_context_timestamp_must_be_timezone_aware")
        return value


@dataclass(frozen=True, slots=True)
class CandidateReviewResult:
    condition_origin: EpistemicOrigin
    condition_statement: str
    edges: tuple[ProvenanceEdge, ...]


def _edge(
    source_id: str,
    source_role: EpistemicRole,
    target_id: str,
    target_role: EpistemicRole,
    relation: ProvenanceRelation,
) -> ProvenanceEdge:
    edge = ProvenanceEdge(
        source_id=source_id,
        source_role=source_role,
        target_id=target_id,
        target_role=target_role,
        relation=relation,
    )
    validate_provenance_edge(edge)
    return edge


def candidate_review_is_finalizable(
    dispositions: tuple[CandidateDisposition, ...],
    *,
    open_flag_count: int,
) -> bool:
    if type(open_flag_count) is not int or open_flag_count < 0:
        raise SourceReviewViolation("invalid_open_flag_count")
    return open_flag_count == 0 and all(
        disposition in _TERMINAL_CANDIDATE_DISPOSITIONS
        for disposition in dispositions
    )


def accept_candidate_unchanged(
    *,
    candidate_id: str,
    segment_id: str,
    condition_id: str,
    extracted_statement: str,
    accepted_statement: str,
) -> CandidateReviewResult:
    if accepted_statement != extracted_statement:
        raise SourceReviewViolation("unchanged_acceptance_must_match_extraction")
    edges = (
        _edge(
            candidate_id,
            EpistemicRole.EXTRACTION_CANDIDATE,
            segment_id,
            EpistemicRole.SOURCE_SEGMENT,
            ProvenanceRelation.EXTRACTED_FROM,
        ),
        _edge(
            candidate_id,
            EpistemicRole.EXTRACTION_CANDIDATE,
            condition_id,
            EpistemicRole.STARTING_CONDITION,
            ProvenanceRelation.ACCEPTED_AS,
        ),
        _edge(
            segment_id,
            EpistemicRole.SOURCE_SEGMENT,
            condition_id,
            EpistemicRole.STARTING_CONDITION,
            ProvenanceRelation.INFORMS,
        ),
    )
    return CandidateReviewResult(
        condition_origin=EpistemicOrigin.SOURCE_EXTRACTED,
        condition_statement=accepted_statement,
        edges=edges,
    )


def revise_candidate(
    *,
    candidate_id: str,
    segment_id: str,
    condition_id: str,
    extracted_statement: str,
    revised_statement: str,
) -> CandidateReviewResult:
    if revised_statement == extracted_statement:
        raise SourceReviewViolation("revision_must_change_statement")
    edges = (
        _edge(
            candidate_id,
            EpistemicRole.EXTRACTION_CANDIDATE,
            segment_id,
            EpistemicRole.SOURCE_SEGMENT,
            ProvenanceRelation.EXTRACTED_FROM,
        ),
        _edge(
            candidate_id,
            EpistemicRole.EXTRACTION_CANDIDATE,
            condition_id,
            EpistemicRole.STARTING_CONDITION,
            ProvenanceRelation.REVISED_AS,
        ),
    )
    return CandidateReviewResult(
        condition_origin=EpistemicOrigin.USER_STATED,
        condition_statement=revised_statement,
        edges=edges,
    )


def validate_deletion_completion(
    targets: tuple[DeletionTargetState, ...],
) -> None:
    if any(target is DeletionTargetState.PENDING for target in targets):
        raise SourceReviewViolation("deletion_targets_unresolved")


class SourceTransitionGuardFacts(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    upload_verified: bool = False
    format_enabled: bool = False
    operational_failure_recorded: bool = False
    policy_rejection_recorded: bool = False
    open_flags_rejected: bool = False
    open_flag_created: bool = False
    deletion_request_committed: bool = False
    worker_lease_valid: bool = False
    scanner_definitions_fresh: bool = False
    scan_clean_receipt_stored: bool = False
    parse_artifacts_durable: bool = False
    candidates_durable: bool = False
    no_open_flags: bool = False
    flags_released: bool = False
    candidate_reset: bool = False
    all_candidates_terminal: bool = False
    review_records_durable: bool = False
    deletion_targets_resolved: bool = False


class SourceTransitionViolation(ValueError):
    """Raised when a source transition is absent from the closed graph."""


class SourceTransitionGuardViolation(ValueError):
    """Raised when an allowed source edge lacks server-derived facts."""


_ALLOWED_SOURCE_TRANSITIONS = {
    (
        SourceIngestionState.UPLOADING,
        SourceIngestionState.QUARANTINED,
        SourceCommandKind.COMPLETE_SOURCE_UPLOAD,
    ),
    (
        SourceIngestionState.UPLOADING,
        SourceIngestionState.FAILED,
        SourceCommandKind.FAIL_SOURCE_UPLOAD,
    ),
    (
        SourceIngestionState.QUARANTINED,
        SourceIngestionState.SCANNING,
        SourceCommandKind.BEGIN_SOURCE_SCAN,
    ),
    (
        SourceIngestionState.QUARANTINED,
        SourceIngestionState.REJECTED,
        SourceCommandKind.RECORD_SOURCE_QUARANTINE_REJECTION,
    ),
    (
        SourceIngestionState.SCANNING,
        SourceIngestionState.PARSING,
        SourceCommandKind.RECORD_SOURCE_SCAN_PASS,
    ),
    (
        SourceIngestionState.SCANNING,
        SourceIngestionState.REJECTED,
        SourceCommandKind.RECORD_SOURCE_SCAN_REJECTION,
    ),
    (
        SourceIngestionState.SCANNING,
        SourceIngestionState.FAILED,
        SourceCommandKind.RECORD_SOURCE_SCAN_FAILURE,
    ),
    (
        SourceIngestionState.PARSING,
        SourceIngestionState.FLAGGED,
        SourceCommandKind.RECORD_SOURCE_PARSE_FLAGGED,
    ),
    (
        SourceIngestionState.PARSING,
        SourceIngestionState.NEEDS_REVIEW,
        SourceCommandKind.RECORD_SOURCE_PARSE_REVIEWABLE,
    ),
    (
        SourceIngestionState.PARSING,
        SourceIngestionState.REJECTED,
        SourceCommandKind.RECORD_SOURCE_PARSE_REJECTION,
    ),
    (
        SourceIngestionState.PARSING,
        SourceIngestionState.FAILED,
        SourceCommandKind.RECORD_SOURCE_PARSE_FAILURE,
    ),
    (
        SourceIngestionState.FLAGGED,
        SourceIngestionState.NEEDS_REVIEW,
        SourceCommandKind.COMPLETE_SOURCE_FLAG_RELEASE,
    ),
    (
        SourceIngestionState.FLAGGED,
        SourceIngestionState.NEEDS_REVIEW,
        SourceCommandKind.RELEASE_REVIEW_REPORTED_FLAG,
    ),
    (
        SourceIngestionState.FLAGGED,
        SourceIngestionState.REJECTED,
        SourceCommandKind.REJECT_FLAGGED_SOURCE,
    ),
    (
        SourceIngestionState.NEEDS_REVIEW,
        SourceIngestionState.READY,
        SourceCommandKind.FINALIZE_SOURCE_REVIEW,
    ),
    (
        SourceIngestionState.NEEDS_REVIEW,
        SourceIngestionState.REJECTED,
        SourceCommandKind.REJECT_SOURCE_REVIEW,
    ),
    (
        SourceIngestionState.NEEDS_REVIEW,
        SourceIngestionState.FLAGGED,
        SourceCommandKind.REPORT_SOURCE_CANDIDATE_SUSPICIOUS,
    ),
    (
        SourceIngestionState.DELETION_PENDING,
        SourceIngestionState.DELETED,
        SourceCommandKind.COMPLETE_SOURCE_DELETION,
    ),
}
_ALLOWED_SOURCE_TRANSITIONS.update(
    (
        source_state,
        SourceIngestionState.DELETION_PENDING,
        SourceCommandKind.REQUEST_SOURCE_DELETION,
    )
    for source_state in SourceIngestionState
    if source_state
    not in {
        SourceIngestionState.DELETION_PENDING,
        SourceIngestionState.DELETED,
    }
)
_ALLOWED_SOURCE_STATE_PAIRS = frozenset(
    (current, target)
    for current, target, _command in _ALLOWED_SOURCE_TRANSITIONS
)


def validate_source_state_pair(
    current: SourceIngestionState,
    target: SourceIngestionState,
) -> None:
    if (current, target) not in _ALLOWED_SOURCE_STATE_PAIRS:
        raise SourceTransitionViolation("source_transition_forbidden")


def transition_source_version(
    current: SourceIngestionState,
    target: SourceIngestionState,
    command: SourceCommandKind,
    guards: SourceTransitionGuardFacts,
) -> SourceIngestionState:
    if (current, target, command) not in _ALLOWED_SOURCE_TRANSITIONS:
        raise SourceTransitionViolation("source_transition_forbidden")
    validate_source_state_pair(current, target)
    if command is SourceCommandKind.COMPLETE_SOURCE_UPLOAD and (
        not guards.upload_verified or not guards.format_enabled
    ):
        raise SourceTransitionGuardViolation("source_upload_guard_failed")
    if (
        command
        in {
            SourceCommandKind.FAIL_SOURCE_UPLOAD,
            SourceCommandKind.RECORD_SOURCE_SCAN_FAILURE,
            SourceCommandKind.RECORD_SOURCE_PARSE_FAILURE,
        }
        and not guards.operational_failure_recorded
    ):
        raise SourceTransitionGuardViolation("operational_failure_required")
    if (
        command
        in {
            SourceCommandKind.RECORD_SOURCE_QUARANTINE_REJECTION,
            SourceCommandKind.RECORD_SOURCE_SCAN_REJECTION,
            SourceCommandKind.RECORD_SOURCE_PARSE_REJECTION,
            SourceCommandKind.REJECT_SOURCE_REVIEW,
        }
        and not guards.policy_rejection_recorded
    ):
        raise SourceTransitionGuardViolation("policy_rejection_required")
    if (
        command is SourceCommandKind.REJECT_FLAGGED_SOURCE
        and not guards.open_flags_rejected
    ):
        raise SourceTransitionGuardViolation("open_flags_must_be_rejected")
    if (
        command is SourceCommandKind.REPORT_SOURCE_CANDIDATE_SUSPICIOUS
        and not guards.open_flag_created
    ):
        raise SourceTransitionGuardViolation("open_flag_required")
    if (
        command is SourceCommandKind.REQUEST_SOURCE_DELETION
        and not guards.deletion_request_committed
    ):
        raise SourceTransitionGuardViolation("deletion_request_required")
    if command is SourceCommandKind.BEGIN_SOURCE_SCAN and not (
        guards.worker_lease_valid and guards.scanner_definitions_fresh
    ):
        raise SourceTransitionGuardViolation("source_scan_start_guard_failed")
    if (
        command is SourceCommandKind.RECORD_SOURCE_SCAN_PASS
        and not guards.scan_clean_receipt_stored
    ):
        raise SourceTransitionGuardViolation("clean_scan_receipt_required")
    if command is SourceCommandKind.RECORD_SOURCE_PARSE_FLAGGED and not (
        guards.parse_artifacts_durable and guards.open_flag_created
    ):
        raise SourceTransitionGuardViolation("flagged_parse_artifacts_required")
    if command is SourceCommandKind.RECORD_SOURCE_PARSE_REVIEWABLE and not (
        guards.parse_artifacts_durable
        and guards.candidates_durable
        and guards.no_open_flags
    ):
        raise SourceTransitionGuardViolation("reviewable_parse_artifacts_required")
    if command is SourceCommandKind.COMPLETE_SOURCE_FLAG_RELEASE and not (
        guards.flags_released and guards.candidates_durable
    ):
        raise SourceTransitionGuardViolation("flag_release_guard_failed")
    if command is SourceCommandKind.RELEASE_REVIEW_REPORTED_FLAG and not (
        guards.flags_released and guards.candidate_reset
    ):
        raise SourceTransitionGuardViolation("reported_flag_release_guard_failed")
    if command is SourceCommandKind.FINALIZE_SOURCE_REVIEW and not (
        guards.all_candidates_terminal
        and guards.no_open_flags
        and guards.review_records_durable
    ):
        raise SourceTransitionGuardViolation("source_review_not_finalizable")
    if (
        command is SourceCommandKind.COMPLETE_SOURCE_DELETION
        and not guards.deletion_targets_resolved
    ):
        raise SourceTransitionGuardViolation("deletion_targets_unresolved")
    return target
