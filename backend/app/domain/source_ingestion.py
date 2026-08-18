"""Pure contracts for controlled source ingestion and review."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import ClassVar, Literal, Self
from uuid import RFC_4122, UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    CREATE_SOURCE_UPLOAD_INTENT = "create_source_upload_intent"
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
    AUTHORIZE_SOURCE_FLAG_RELEASE = "authorize_source_flag_release"
    RELEASE_REVIEW_REPORTED_FLAG = "release_review_reported_flag"
    REJECT_FLAGGED_SOURCE = "reject_flagged_source"
    FINALIZE_SOURCE_REVIEW = "finalize_source_review"
    REJECT_SOURCE_REVIEW = "reject_source_review"
    REPORT_SOURCE_CANDIDATE_SUSPICIOUS = "report_source_candidate_suspicious"
    ACCEPT_SOURCE_CANDIDATE = "accept_source_candidate"
    REVISE_SOURCE_CANDIDATE = "revise_source_candidate"
    EXCLUDE_SOURCE_CANDIDATE = "exclude_source_candidate"
    REQUEST_SOURCE_DELETION = "request_source_deletion"
    RECORD_DELETION_TARGET_RESULT = "record_deletion_target_result"
    COMPLETE_SOURCE_DELETION = "complete_source_deletion"


class CandidateDisposition(str, Enum):
    PENDING = "PENDING"
    ACCEPTED_SOURCE_CONDITION = "ACCEPTED_SOURCE_CONDITION"
    REVISED_USER_CONDITION = "REVISED_USER_CONDITION"
    EXCLUDED = "EXCLUDED"
    REPORTED_SUSPICIOUS = "REPORTED_SUSPICIOUS"


class ReviewFlagDisposition(str, Enum):
    OPEN = "OPEN"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"


class SourceProcessingStage(str, Enum):
    SCAN = "SCAN"
    PARSE = "PARSE"
    EXTRACT = "EXTRACT"


class SourceAttemptState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCELLED = "CANCELLED"


class DeletionTargetKind(str, Enum):
    PRIMARY_DATABASE = "PRIMARY_DATABASE"
    QUARANTINE_OBJECT = "QUARANTINE_OBJECT"
    PROCESSED_OBJECT = "PROCESSED_OBJECT"
    OBJECT_VERSIONS = "OBJECT_VERSIONS"
    DERIVED_INDEX = "DERIVED_INDEX"
    CACHE = "CACHE"
    EXPORT = "EXPORT"
    PROVIDER_RECORD = "PROVIDER_RECORD"
    BACKUP_EXPIRY = "BACKUP_EXPIRY"


class DeletionTargetState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    SCHEDULED_AGE_OUT = "SCHEDULED_AGE_OUT"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LEGAL_HOLD = "LEGAL_HOLD"


TERMINAL_REVIEW_DISPOSITIONS = frozenset(
    {
        CandidateDisposition.ACCEPTED_SOURCE_CONDITION,
        CandidateDisposition.REVISED_USER_CONDITION,
        CandidateDisposition.EXCLUDED,
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


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PUBLIC_PATTERNS = {
    "src": re.compile(r"src_[0-9a-f]{32}"),
    "srcv": re.compile(r"srcv_[0-9a-f]{32}"),
    "seg": re.compile(r"seg_[0-9a-f]{32}"),
    "cand": re.compile(r"cand_[0-9a-f]{32}"),
    "cond": re.compile(r"cond_[0-9a-f]{32}"),
    "sflag": re.compile(r"sflag_[0-9a-f]{32}"),
    "srev": re.compile(r"srev_[0-9a-f]{32}"),
    "del": re.compile(r"del_[0-9a-f]{32}"),
}


class _StrictRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def validate_record_values(cls, value: object, info: object) -> object:
        field_name = getattr(info, "field_name", "")
        if isinstance(value, UUID) and (value.version != 7 or value.variant != RFC_4122):
            raise ValueError("source_record_ids_must_be_uuid7")
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("source_record_timestamp_must_be_timezone_aware")
        if field_name.endswith("sha256") and value is not None and (
            not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None
        ):
            raise ValueError("source_record_sha256_invalid")
        return value


class _AddressableRecord(_StrictRecord):
    public_id_prefix: ClassVar[str]

    id: UUID
    public_id: str

    @model_validator(mode="after")
    def validate_public_identity(self) -> Self:
        prefix = self.public_id.split("_", 1)[0]
        pattern = _PUBLIC_PATTERNS.get(prefix)
        if pattern is None or pattern.fullmatch(self.public_id) is None:
            raise ValueError("source_public_id_invalid")
        if prefix != self.public_id_prefix:
            raise ValueError("source_public_id_kind_mismatch")
        if self.public_id.endswith(self.id.hex):
            raise ValueError("source_public_id_must_not_reveal_physical_id")
        return self


class _ScopedRecord(_AddressableRecord):
    organization_id: UUID
    workspace_id: UUID
    project_id: UUID


class SourceRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "src"

    display_name: str = Field(min_length=1, max_length=255)
    current_version_id: UUID | None = None
    version: int = Field(ge=1)
    created_by_actor_id: UUID
    created_at: datetime
    updated_at: datetime


class SourceVersionRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "srcv"

    source_id: UUID
    version_number: int = Field(ge=1)
    state: SourceIngestionState
    original_filename_display: str
    declared_media_type: str
    detected_media_type: str | None = None
    raw_object_ref: str | None = None
    processed_object_ref: str | None = None
    raw_byte_length: int | None = Field(default=None, ge=0)
    raw_sha256: str | None = None
    normalized_byte_length: int | None = Field(default=None, ge=0)
    normalized_sha256: str | None = None
    normalized_token_count: int | None = Field(default=None, ge=0)
    scanner_name: str | None = None
    scanner_version: str | None = None
    scanner_definitions_version: str | None = None
    parser_name: str | None = None
    parser_version: str | None = None
    parser_policy_version: str | None = None
    extraction_prompt_id: str | None = None
    extraction_prompt_version: str | None = None
    extraction_schema_id: str | None = None
    extraction_schema_version: str | None = None
    extraction_model_release_id: str | None = None
    processing_fence: int = Field(ge=0)
    deletion_fence: int = Field(ge=0)
    version: int = Field(ge=1)
    created_by_actor_id: UUID
    created_at: datetime
    updated_at: datetime


class SourceSegmentRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "seg"

    source_version_id: UUID
    ordinal: int = Field(ge=0)
    normalized_start_byte: int = Field(ge=0)
    normalized_end_byte: int = Field(ge=0)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    segment_sha256: str
    created_at: datetime


class CandidateStartingConditionRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "cand"

    source_version_id: UUID
    source_segment_id: UUID
    ordinal: int = Field(ge=0)
    proposed_statement: str = Field(min_length=1, max_length=4000)
    proposed_statement_sha256: str
    extraction_origin: Literal["GENERATED_GENERATED"] = "GENERATED_GENERATED"
    disposition: CandidateDisposition
    disposition_reason_code: str | None = None
    disposition_reason_note: str | None = None
    disposed_by_actor_id: UUID | None = None
    disposed_at: datetime | None = None
    version: int = Field(ge=1)


class StartingConditionRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "cond"

    statement: str = Field(min_length=1, max_length=4000)
    statement_sha256: str
    origin: Literal[
        EpistemicOrigin.SOURCE_EXTRACTED,
        EpistemicOrigin.USER_STATED,
    ]
    source_version_id: UUID
    source_segment_id: UUID | None
    candidate_id: UUID
    created_by_actor_id: UUID
    created_at: datetime


class SourceReviewFlagRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "sflag"

    source_version_id: UUID
    candidate_id: UUID | None = None
    flag_code: str
    severity: str
    disposition: ReviewFlagDisposition
    detected_by: str
    disposition_reason_code: str | None = None
    disposed_by_actor_id: UUID | None = None
    disposed_at: datetime | None = None
    created_at: datetime
    version: int = Field(ge=1)


class SourceReviewEventRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "srev"

    source_version_id: UUID
    command_name: str
    from_state: SourceIngestionState | None
    to_state: SourceIngestionState | None
    actor_type: str
    actor_id: UUID
    capability: str
    expected_version: int = Field(ge=1)
    resulting_version: int = Field(ge=1)
    idempotency_key: str
    request_body_sha256: str
    reason_code: str
    reason_note: str | None = None
    request_id: UUID
    occurred_at: datetime


class SourceProcessingAttemptRecord(_StrictRecord):
    id: UUID
    source_version_id: UUID
    organization_id: UUID
    workspace_id: UUID
    project_id: UUID
    stage: SourceProcessingStage
    attempt_number: int = Field(ge=1)
    state: SourceAttemptState
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    fencing_token: int = Field(ge=1)
    deletion_fence_at_claim: int = Field(ge=0)
    retry_class: str | None = None
    error_code: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DeletionRequestRecord(_ScopedRecord):
    public_id_prefix: ClassVar[str] = "del"

    source_version_id: UUID
    requested_by_actor_id: UUID
    reason_code: str
    requested_at: datetime
    completed_at: datetime | None = None
    version: int = Field(ge=1)


class DeletionTargetStatusRecord(_StrictRecord):
    deletion_request_id: UUID
    target_kind: DeletionTargetKind
    target_ref_hash: str
    state: DeletionTargetState
    provider_receipt_ref: str | None = None
    attempt_count: int = Field(ge=0)
    last_error_code: str | None = None
    next_attempt_at: datetime | None = None
    confirmed_at: datetime | None = None
    scheduled_expiry_at: datetime | None = None
    version: int = Field(ge=1)

@dataclass(frozen=True, slots=True)
class CandidateReviewResult:
    condition_origin: EpistemicOrigin
    condition_statement: str
    condition_statement_sha256: str
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
        disposition in TERMINAL_REVIEW_DISPOSITIONS
        for disposition in dispositions
    )


def accept_candidate_unchanged(
    *,
    candidate_id: str,
    segment_id: str,
    condition_id: str,
    extracted_statement: str,
    extracted_statement_sha256: str,
    accepted_statement: str,
) -> CandidateReviewResult:
    actual_hash = sha256(extracted_statement.encode("utf-8")).hexdigest()
    if actual_hash != extracted_statement_sha256:
        raise SourceReviewViolation("candidate_statement_hash_mismatch")
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
        condition_statement_sha256=actual_hash,
        edges=edges,
    )


def revise_candidate(
    *,
    candidate_id: str,
    segment_id: str,
    condition_id: str,
    extracted_statement: str,
    extracted_statement_sha256: str,
    revised_statement: str,
) -> CandidateReviewResult:
    if sha256(extracted_statement.encode("utf-8")).hexdigest() != extracted_statement_sha256:
        raise SourceReviewViolation("candidate_statement_hash_mismatch")
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
        condition_statement_sha256=sha256(revised_statement.encode("utf-8")).hexdigest(),
        edges=edges,
    )


def validate_deletion_completion(
    targets: tuple[DeletionTargetState, ...],
    *,
    primary_content_absent: bool,
    scheduled_expiry_disclosed: bool = False,
) -> None:
    if not primary_content_absent:
        raise SourceReviewViolation("primary_content_still_present")
    if not targets:
        raise SourceReviewViolation("deletion_inventory_required")
    terminal = {
        DeletionTargetState.CONFIRMED,
        DeletionTargetState.NOT_APPLICABLE,
        DeletionTargetState.SCHEDULED_AGE_OUT,
    }
    if any(target not in terminal for target in targets):
        raise SourceReviewViolation("deletion_targets_unresolved")
    if DeletionTargetState.SCHEDULED_AGE_OUT in targets and not scheduled_expiry_disclosed:
        raise SourceReviewViolation("scheduled_expiry_required")


class SourceTransitionGuardFacts(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    upload_verified: bool = False
    format_enabled: bool = False
    exact_object_key_exists: bool = False
    byte_length_matches: bool = False
    sha256_matches: bool = False
    object_private: bool = False
    upload_intent_unexpired: bool = False
    operational_failure_recorded: bool = False
    policy_rejection_recorded: bool = False
    open_flags_rejected: bool = False
    open_flag_created: bool = False
    deletion_request_committed: bool = False
    deletion_fence_committed: bool = False
    upload_intent_revoked: bool = False
    queued_work_cancelled: bool = False
    deletion_target_inventory_complete: bool = False
    worker_lease_valid: bool = False
    scanner_definitions_fresh: bool = False
    scan_clean_receipt_stored: bool = False
    scan_result_clean: bool = False
    source_limits_pass: bool = False
    parse_artifacts_durable: bool = False
    candidates_durable: bool = False
    prompt_model_schema_records_durable: bool = False
    artifact_hashes_durable: bool = False
    no_open_flags: bool = False
    flags_released: bool = False
    named_reviewer_authorized: bool = False
    release_event_durable: bool = False
    extraction_events_durable: bool = False
    schema_references_valid: bool = False
    candidate_reset: bool = False
    finalization_invalidated: bool = False
    review_event_durable: bool = False
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
        not guards.upload_verified
        or not guards.format_enabled
        or not guards.exact_object_key_exists
        or not guards.byte_length_matches
        or not guards.sha256_matches
        or not guards.object_private
        or not guards.upload_intent_unexpired
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
        and not all(
            (
                guards.open_flag_created,
                guards.finalization_invalidated,
                guards.review_event_durable,
            )
        )
    ):
        raise SourceTransitionGuardViolation("open_flag_required")
    if (
        command is SourceCommandKind.REQUEST_SOURCE_DELETION
        and not all(
            (
                guards.deletion_request_committed,
                guards.deletion_fence_committed,
                guards.upload_intent_revoked,
                guards.queued_work_cancelled,
                guards.deletion_target_inventory_complete,
            )
        )
    ):
        raise SourceTransitionGuardViolation("deletion_request_required")
    if command is SourceCommandKind.BEGIN_SOURCE_SCAN and not (
        guards.worker_lease_valid and guards.scanner_definitions_fresh
    ):
        raise SourceTransitionGuardViolation("source_scan_start_guard_failed")
    if (
        command is SourceCommandKind.RECORD_SOURCE_SCAN_PASS
        and not all(
            (
                guards.scan_clean_receipt_stored,
                guards.scan_result_clean,
                guards.source_limits_pass,
            )
        )
    ):
        raise SourceTransitionGuardViolation("clean_scan_receipt_required")
    if command is SourceCommandKind.RECORD_SOURCE_PARSE_FLAGGED and not (
        guards.parse_artifacts_durable and guards.open_flag_created
    ):
        raise SourceTransitionGuardViolation("flagged_parse_artifacts_required")
    if command is SourceCommandKind.RECORD_SOURCE_PARSE_REVIEWABLE and not (
        guards.parse_artifacts_durable
        and guards.candidates_durable
        and guards.prompt_model_schema_records_durable
        and guards.artifact_hashes_durable
        and guards.no_open_flags
    ):
        raise SourceTransitionGuardViolation("reviewable_parse_artifacts_required")
    if command is SourceCommandKind.COMPLETE_SOURCE_FLAG_RELEASE and not (
        guards.flags_released
        and guards.candidates_durable
        and guards.named_reviewer_authorized
        and guards.release_event_durable
        and guards.extraction_events_durable
        and guards.schema_references_valid
    ):
        raise SourceTransitionGuardViolation("flag_release_guard_failed")
    if command is SourceCommandKind.RELEASE_REVIEW_REPORTED_FLAG and not (
        guards.flags_released
        and guards.candidate_reset
        and guards.named_reviewer_authorized
        and guards.release_event_durable
        and guards.review_event_durable
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
