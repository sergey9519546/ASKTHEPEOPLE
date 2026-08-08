"""Pure durable-run and immutable stage-attempt domain contracts."""

import re
from enum import Enum
from itertools import pairwise
from typing import Self
from uuid import RFC_4122, UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .decision_workspace import TruthBundle

_PUBLIC_RUN_ID_PATTERN = re.compile(r"run_([0-9a-f]{32})")
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_BOUNDED_CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$"


def _require_uuid7(value: UUID, *, code: str) -> UUID:
    if value.version != 7 or value.variant != RFC_4122:
        raise ValueError(code)
    return value


class RunState(str, Enum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"
    READY = "READY"
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    EXTRACTING = "EXTRACTING"
    REVIEWING_CONDITIONS = "REVIEWING_CONDITIONS"
    GENERATING_PROFILES = "GENERATING_PROFILES"
    CONSTRUCTING_SCENARIOS = "CONSTRUCTING_SCENARIOS"
    GENERATING_PATHS = "GENERATING_PATHS"
    SYNTHESIZING = "SYNTHESIZING"
    VALIDATING_OUTPUT = "VALIDATING_OUTPUT"
    GENERATING_BRIEF = "GENERATING_BRIEF"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class RunStageCode(str, Enum):
    PREPARING = "PREPARING"
    EXTRACTING = "EXTRACTING"
    REVIEWING_CONDITIONS = "REVIEWING_CONDITIONS"
    GENERATING_PROFILES = "GENERATING_PROFILES"
    CONSTRUCTING_SCENARIOS = "CONSTRUCTING_SCENARIOS"
    GENERATING_PATHS = "GENERATING_PATHS"
    SYNTHESIZING = "SYNTHESIZING"
    VALIDATING_OUTPUT = "VALIDATING_OUTPUT"
    GENERATING_BRIEF = "GENERATING_BRIEF"


class RunStageAttemptState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    SUCCEEDED = "SUCCEEDED"
    RETRY_WAIT = "RETRY_WAIT"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class RunCommandKind(str, Enum):
    SUBMIT_FOR_REVIEW = "SUBMIT_FOR_REVIEW"
    BLOCK_REVIEW = "BLOCK_REVIEW"
    RESUBMIT_REVIEW = "RESUBMIT_REVIEW"
    APPROVE_CONFIGURATION = "APPROVE_CONFIGURATION"
    START_RUN = "START_RUN"
    ACCEPT_WORKFLOW = "ACCEPT_WORKFLOW"
    SUCCEED_STAGE = "SUCCEED_STAGE"
    REQUEST_STOP = "REQUEST_STOP"
    CONFIRM_STOPPED = "CONFIRM_STOPPED"
    RECORD_RETRYABLE_FAILURE = "RECORD_RETRYABLE_FAILURE"
    ACCEPT_RETRY = "ACCEPT_RETRY"
    EXHAUST_RETRY_BUDGET = "EXHAUST_RETRY_BUDGET"
    ARCHIVE_RUN = "ARCHIVE_RUN"


class RunEventType(str, Enum):
    RUN_CREATED = "RUN_CREATED"
    RUN_STATE_CHANGED = "RUN_STATE_CHANGED"
    RERUN_CREATED = "RERUN_CREATED"
    STAGE_ATTEMPT_CREATED = "STAGE_ATTEMPT_CREATED"
    STAGE_STATE_CHANGED = "STAGE_STATE_CHANGED"
    STAGE_LEASE_CLAIMED = "STAGE_LEASE_CLAIMED"
    STAGE_LEASE_EXPIRED = "STAGE_LEASE_EXPIRED"
    STAGE_OUTPUT_ACCEPTED = "STAGE_OUTPUT_ACCEPTED"
    STAGE_OUTPUT_QUARANTINED = "STAGE_OUTPUT_QUARANTINED"
    RUN_STOP_FENCE_ADVANCED = "RUN_STOP_FENCE_ADVANCED"
    RETRY_BUDGET_EXHAUSTED = "RETRY_BUDGET_EXHAUSTED"
    RUN_ARCHIVED = "RUN_ARCHIVED"


class RunSnapshot(BaseModel):
    """Internal immutable run state used by the transition policy."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: UUID
    public_id: str
    organization_id: UUID
    workspace_id: UUID
    run_config_id: UUID
    parent_run_id: UUID | None
    state: RunState
    version: int = Field(ge=1)
    current_stage_code: RunStageCode | None
    stop_fence: int = Field(ge=0)
    truth: TruthBundle = Field(default_factory=TruthBundle.synthetic)

    @field_validator(
        "id",
        "organization_id",
        "workspace_id",
        "run_config_id",
        "parent_run_id",
    )
    @classmethod
    def require_uuid7_fields(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return None
        return _require_uuid7(value, code="run_physical_id_must_be_uuid7")

    @model_validator(mode="after")
    def require_independent_run_public_id(self) -> Self:
        match = _PUBLIC_RUN_ID_PATTERN.fullmatch(self.public_id)
        if match is None:
            raise ValueError("invalid_run_public_id")
        public_uuid = UUID(hex=match.group(1))
        _require_uuid7(public_uuid, code="run_public_id_must_contain_uuid7")
        if public_uuid == self.id:
            raise ValueError("run_public_id_must_not_reveal_physical_id")
        return self


class RunGuardFacts(BaseModel):
    """Server-derived facts consumed by the pure transition policy."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    decision_and_config_refs_exist: bool
    deficiency_recorded: bool
    deficiency_revision_recorded: bool
    review_approved: bool
    policy_allowed: bool
    sources_ready: bool
    assumptions_approved: bool
    decision_lenses_approved: bool
    truth_fields_present: bool
    release_ids_present: bool
    config_sealed: bool
    config_hash_verified: bool
    idempotency_accepted: bool
    stage_attempt_leased: bool
    critical_validators_pass: bool
    current_path_set_review_approved: bool
    path_set_review_hashes_match: bool
    path_validator_bundle_matches: bool
    brief_gate_hashes_bound: bool
    brief_manifest_accepted: bool
    export_eligibility_calculated: bool
    authorized_stop: bool
    active_work_drained: bool
    retry_budget_remaining: bool
    release_set_unchanged: bool
    approved_replacement_release: bool
    retry_budget_exhausted: bool
    retention_allows_archive: bool
    accepted_stage_output_artifact_ref_id: UUID | None = None
    current_path_set_id: UUID | None = None
    approved_path_review_id: UUID | None = None
    current_path_set_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    approved_path_review_sha256: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    brief_gate_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    path_validator_bundle_version: str | None = Field(
        default=None,
        pattern=_BOUNDED_CODE_PATTERN,
    )
    retryable_failure_code: str | None = Field(
        default=None,
        pattern=_BOUNDED_CODE_PATTERN,
    )

    @field_validator(
        "accepted_stage_output_artifact_ref_id",
        "current_path_set_id",
        "approved_path_review_id",
    )
    @classmethod
    def require_uuid7_references(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return None
        return _require_uuid7(value, code="run_guard_reference_must_be_uuid7")


class RunTransition(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    command: RunCommandKind
    from_state: RunState
    to_state: RunState
    next_version: int = Field(ge=2)
    event_type: RunEventType


class RunTransitionViolation(ValueError):
    """Raised when a command is not an edge in the closed run graph."""


class RunGuardViolation(ValueError):
    """Raised when server-derived facts do not satisfy an allowed edge."""


class StageAttemptTransitionViolation(ValueError):
    """Raised when an immutable stage attempt is asked to cross a closed edge."""


class RerunIdentityViolation(ValueError):
    """Raised when a rerun tries to reuse identity or omit its parent link."""


_STAGE_SEQUENCE = tuple(RunStageCode)
_ACTIVE_RUN_STATES = frozenset(
    {RunState.QUEUED, *(RunState(stage.value) for stage in _STAGE_SEQUENCE)}
)
_STAGE_RUN_STATES = frozenset(RunState(stage.value) for stage in _STAGE_SEQUENCE)

_COMMAND_TARGETS: dict[tuple[RunState, RunCommandKind], RunState] = {
    (RunState.DRAFT, RunCommandKind.SUBMIT_FOR_REVIEW): RunState.NEEDS_REVIEW,
    (RunState.NEEDS_REVIEW, RunCommandKind.BLOCK_REVIEW): RunState.BLOCKED,
    (RunState.BLOCKED, RunCommandKind.RESUBMIT_REVIEW): RunState.NEEDS_REVIEW,
    (
        RunState.NEEDS_REVIEW,
        RunCommandKind.APPROVE_CONFIGURATION,
    ): RunState.READY,
    (RunState.READY, RunCommandKind.START_RUN): RunState.QUEUED,
    (RunState.QUEUED, RunCommandKind.ACCEPT_WORKFLOW): RunState.PREPARING,
    (RunState.STOP_REQUESTED, RunCommandKind.CONFIRM_STOPPED): RunState.STOPPED,
    (RunState.FAILED_RETRYABLE, RunCommandKind.ACCEPT_RETRY): RunState.QUEUED,
    (
        RunState.FAILED_RETRYABLE,
        RunCommandKind.EXHAUST_RETRY_BUDGET,
    ): RunState.FAILED_TERMINAL,
    (RunState.COMPLETED, RunCommandKind.ARCHIVE_RUN): RunState.ARCHIVED,
    (RunState.STOPPED, RunCommandKind.ARCHIVE_RUN): RunState.ARCHIVED,
    (RunState.FAILED_TERMINAL, RunCommandKind.ARCHIVE_RUN): RunState.ARCHIVED,
}

for current_stage, next_stage in pairwise(_STAGE_SEQUENCE):
    _COMMAND_TARGETS[
        (RunState(current_stage.value), RunCommandKind.SUCCEED_STAGE)
    ] = RunState(next_stage.value)
_COMMAND_TARGETS[
    (RunState.GENERATING_BRIEF, RunCommandKind.SUCCEED_STAGE)
] = RunState.COMPLETED
for active_state in _ACTIVE_RUN_STATES:
    _COMMAND_TARGETS[(active_state, RunCommandKind.REQUEST_STOP)] = (
        RunState.STOP_REQUESTED
    )
for stage_state in _STAGE_RUN_STATES:
    _COMMAND_TARGETS[
        (stage_state, RunCommandKind.RECORD_RETRYABLE_FAILURE)
    ] = RunState.FAILED_RETRYABLE

_ALLOWED_RUN_STATE_PAIRS = frozenset(
    (from_state, to_state)
    for (from_state, _command), to_state in _COMMAND_TARGETS.items()
)

_ALLOWED_STAGE_ATTEMPT_PAIRS = frozenset(
    {
        (RunStageAttemptState.PENDING, RunStageAttemptState.READY),
        (RunStageAttemptState.READY, RunStageAttemptState.RUNNING),
        (RunStageAttemptState.RUNNING, RunStageAttemptState.VALIDATING),
        (RunStageAttemptState.VALIDATING, RunStageAttemptState.SUCCEEDED),
        (RunStageAttemptState.RUNNING, RunStageAttemptState.RETRY_WAIT),
        (RunStageAttemptState.VALIDATING, RunStageAttemptState.RETRY_WAIT),
        (RunStageAttemptState.RUNNING, RunStageAttemptState.FAILED_TERMINAL),
        (
            RunStageAttemptState.VALIDATING,
            RunStageAttemptState.FAILED_TERMINAL,
        ),
        (RunStageAttemptState.RUNNING, RunStageAttemptState.CANCEL_REQUESTED),
        (
            RunStageAttemptState.CANCEL_REQUESTED,
            RunStageAttemptState.CANCELLED,
        ),
    }
)


def validate_run_state_pair(from_state: RunState, to_state: RunState) -> None:
    if (from_state, to_state) not in _ALLOWED_RUN_STATE_PAIRS:
        raise RunTransitionViolation("run_transition_forbidden")


def validate_stage_attempt_transition(
    from_state: RunStageAttemptState,
    to_state: RunStageAttemptState,
) -> None:
    if (from_state, to_state) not in _ALLOWED_STAGE_ATTEMPT_PAIRS:
        raise StageAttemptTransitionViolation("stage_attempt_transition_forbidden")


def next_retry_attempt_number(
    closed_attempt_number: int,
    closed_state: RunStageAttemptState,
) -> int:
    if type(closed_attempt_number) is not int or closed_attempt_number < 1:
        raise ValueError("attempt_number_must_be_positive_integer")
    if closed_state is not RunStageAttemptState.RETRY_WAIT:
        raise ValueError("retry_requires_closed_retry_wait_attempt")
    return closed_attempt_number + 1


def validate_rerun_identity(parent: RunSnapshot, child: RunSnapshot) -> None:
    if child.parent_run_id != parent.id:
        raise RerunIdentityViolation("rerun_parent_mismatch")
    if child.id == parent.id or child.public_id == parent.public_id:
        raise RerunIdentityViolation("rerun_identity_must_be_new")


def _require_guard(condition: bool, code: str) -> None:
    if not condition:
        raise RunGuardViolation(code)


def _validate_transition_guards(
    snapshot: RunSnapshot,
    command: RunCommandKind,
    guards: RunGuardFacts,
) -> None:
    if snapshot.state in _STAGE_RUN_STATES:
        expected_stage = RunStageCode(snapshot.state.value)
        _require_guard(
            snapshot.current_stage_code is expected_stage,
            "run_current_stage_mismatch",
        )

    if command is RunCommandKind.SUBMIT_FOR_REVIEW:
        _require_guard(
            guards.decision_and_config_refs_exist,
            "decision_and_config_refs_required",
        )
    elif command is RunCommandKind.BLOCK_REVIEW:
        _require_guard(guards.deficiency_recorded, "review_deficiency_required")
    elif command is RunCommandKind.RESUBMIT_REVIEW:
        _require_guard(
            guards.deficiency_revision_recorded,
            "deficiency_revision_required",
        )
    elif command is RunCommandKind.APPROVE_CONFIGURATION:
        required = (
            guards.decision_and_config_refs_exist,
            guards.review_approved,
            guards.policy_allowed,
            guards.sources_ready,
            guards.assumptions_approved,
            guards.decision_lenses_approved,
            guards.truth_fields_present,
            guards.release_ids_present,
        )
        _require_guard(all(required), "configuration_approval_guard_failed")
    elif command is RunCommandKind.START_RUN:
        _require_guard(
            guards.config_sealed
            and guards.config_hash_verified
            and guards.idempotency_accepted,
            "run_start_guard_failed",
        )
    elif command is RunCommandKind.ACCEPT_WORKFLOW:
        _require_guard(guards.stage_attempt_leased, "stage_attempt_lease_required")
    elif command is RunCommandKind.SUCCEED_STAGE:
        _require_guard(
            guards.accepted_stage_output_artifact_ref_id is not None,
            "accepted_stage_output_required",
        )
        if snapshot.state is RunState.VALIDATING_OUTPUT:
            exact_path_gate = (
                guards.critical_validators_pass
                and guards.current_path_set_review_approved
                and guards.path_set_review_hashes_match
                and guards.path_validator_bundle_matches
                and guards.brief_gate_hashes_bound
                and guards.current_path_set_id is not None
                and guards.approved_path_review_id is not None
                and guards.current_path_set_sha256 is not None
                and guards.approved_path_review_sha256 is not None
                and guards.brief_gate_sha256 is not None
                and guards.path_validator_bundle_version is not None
            )
            _require_guard(exact_path_gate, "path_brief_gate_not_satisfied")
        elif snapshot.state is RunState.GENERATING_BRIEF:
            _require_guard(
                guards.brief_manifest_accepted
                and guards.export_eligibility_calculated,
                "brief_completion_guard_failed",
            )
    elif command is RunCommandKind.REQUEST_STOP:
        _require_guard(guards.authorized_stop, "authorized_stop_required")
    elif command is RunCommandKind.CONFIRM_STOPPED:
        _require_guard(guards.active_work_drained, "active_work_must_be_drained")
    elif command is RunCommandKind.RECORD_RETRYABLE_FAILURE:
        _require_guard(
            guards.retryable_failure_code is not None,
            "retryable_failure_code_required",
        )
    elif command is RunCommandKind.ACCEPT_RETRY:
        _require_guard(
            guards.retry_budget_remaining
            and (
                guards.release_set_unchanged
                or guards.approved_replacement_release
            ),
            "retry_acceptance_guard_failed",
        )
    elif command is RunCommandKind.EXHAUST_RETRY_BUDGET:
        _require_guard(
            guards.retry_budget_exhausted,
            "retry_budget_must_be_exhausted",
        )
    elif command is RunCommandKind.ARCHIVE_RUN:
        _require_guard(
            guards.retention_allows_archive,
            "retention_does_not_allow_archive",
        )


def decide_run_transition(
    snapshot: RunSnapshot,
    *,
    command: RunCommandKind,
    guards: RunGuardFacts,
) -> RunTransition:
    """Apply the closed state graph and server-derived guards without I/O."""

    to_state = _COMMAND_TARGETS.get((snapshot.state, command))
    if to_state is None:
        raise RunTransitionViolation("run_transition_forbidden")
    validate_run_state_pair(snapshot.state, to_state)
    _validate_transition_guards(snapshot, command, guards)

    event_type = RunEventType.RUN_STATE_CHANGED
    if command is RunCommandKind.REQUEST_STOP:
        event_type = RunEventType.RUN_STOP_FENCE_ADVANCED
    elif command is RunCommandKind.EXHAUST_RETRY_BUDGET:
        event_type = RunEventType.RETRY_BUDGET_EXHAUSTED
    elif command is RunCommandKind.ARCHIVE_RUN:
        event_type = RunEventType.RUN_ARCHIVED

    return RunTransition(
        command=command,
        from_state=snapshot.state,
        to_state=to_state,
        next_version=snapshot.version + 1,
        event_type=event_type,
    )
