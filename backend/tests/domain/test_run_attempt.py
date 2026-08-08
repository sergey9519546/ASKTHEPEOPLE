"""Durable run domain-kernel tests."""

from uuid import UUID

import pytest
from pydantic import ValidationError


ALLOWED_RUN_TRANSITIONS = (
    ("DRAFT", "SUBMIT_FOR_REVIEW", "NEEDS_REVIEW"),
    ("NEEDS_REVIEW", "BLOCK_REVIEW", "BLOCKED"),
    ("BLOCKED", "RESUBMIT_REVIEW", "NEEDS_REVIEW"),
    ("NEEDS_REVIEW", "APPROVE_CONFIGURATION", "READY"),
    ("READY", "START_RUN", "QUEUED"),
    ("QUEUED", "ACCEPT_WORKFLOW", "PREPARING"),
    ("PREPARING", "SUCCEED_STAGE", "EXTRACTING"),
    ("EXTRACTING", "SUCCEED_STAGE", "REVIEWING_CONDITIONS"),
    ("REVIEWING_CONDITIONS", "SUCCEED_STAGE", "GENERATING_PROFILES"),
    ("GENERATING_PROFILES", "SUCCEED_STAGE", "CONSTRUCTING_SCENARIOS"),
    ("CONSTRUCTING_SCENARIOS", "SUCCEED_STAGE", "GENERATING_PATHS"),
    ("GENERATING_PATHS", "SUCCEED_STAGE", "SYNTHESIZING"),
    ("SYNTHESIZING", "SUCCEED_STAGE", "VALIDATING_OUTPUT"),
    ("VALIDATING_OUTPUT", "SUCCEED_STAGE", "GENERATING_BRIEF"),
    ("GENERATING_BRIEF", "SUCCEED_STAGE", "COMPLETED"),
    ("QUEUED", "REQUEST_STOP", "STOP_REQUESTED"),
    ("PREPARING", "REQUEST_STOP", "STOP_REQUESTED"),
    ("EXTRACTING", "REQUEST_STOP", "STOP_REQUESTED"),
    ("REVIEWING_CONDITIONS", "REQUEST_STOP", "STOP_REQUESTED"),
    ("GENERATING_PROFILES", "REQUEST_STOP", "STOP_REQUESTED"),
    ("CONSTRUCTING_SCENARIOS", "REQUEST_STOP", "STOP_REQUESTED"),
    ("GENERATING_PATHS", "REQUEST_STOP", "STOP_REQUESTED"),
    ("SYNTHESIZING", "REQUEST_STOP", "STOP_REQUESTED"),
    ("VALIDATING_OUTPUT", "REQUEST_STOP", "STOP_REQUESTED"),
    ("GENERATING_BRIEF", "REQUEST_STOP", "STOP_REQUESTED"),
    ("STOP_REQUESTED", "CONFIRM_STOPPED", "STOPPED"),
    ("PREPARING", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("EXTRACTING", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("REVIEWING_CONDITIONS", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("GENERATING_PROFILES", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("CONSTRUCTING_SCENARIOS", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("GENERATING_PATHS", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("SYNTHESIZING", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("VALIDATING_OUTPUT", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("GENERATING_BRIEF", "RECORD_RETRYABLE_FAILURE", "FAILED_RETRYABLE"),
    ("FAILED_RETRYABLE", "ACCEPT_RETRY", "QUEUED"),
    ("FAILED_RETRYABLE", "EXHAUST_RETRY_BUDGET", "FAILED_TERMINAL"),
    ("COMPLETED", "ARCHIVE_RUN", "ARCHIVED"),
    ("STOPPED", "ARCHIVE_RUN", "ARCHIVED"),
    ("FAILED_TERMINAL", "ARCHIVE_RUN", "ARCHIVED"),
)


def _uuid7(*, second: int, random_value: int) -> UUID:
    from app.domain.identifiers import new_uuid7

    return new_uuid7(clock=lambda: second, randbits=lambda _: random_value)


def _snapshot_data() -> dict[str, object]:
    from app.domain.run_attempt import RunState

    physical_id = _uuid7(second=1_700_000_000, random_value=1)
    public_uuid = _uuid7(second=1_700_000_001, random_value=2)
    return {
        "id": physical_id,
        "public_id": f"run_{public_uuid.hex}",
        "organization_id": _uuid7(second=1_700_000_002, random_value=3),
        "workspace_id": _uuid7(second=1_700_000_003, random_value=4),
        "run_config_id": _uuid7(second=1_700_000_004, random_value=5),
        "parent_run_id": None,
        "state": RunState.DRAFT,
        "version": 1,
        "current_stage_code": None,
        "stop_fence": 0,
    }


def _guard_data(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "decision_and_config_refs_exist": False,
        "deficiency_recorded": False,
        "deficiency_revision_recorded": False,
        "review_approved": False,
        "policy_allowed": False,
        "sources_ready": False,
        "assumptions_approved": False,
        "decision_lenses_approved": False,
        "truth_fields_present": False,
        "release_ids_present": False,
        "config_sealed": False,
        "config_hash_verified": False,
        "idempotency_accepted": False,
        "stage_attempt_leased": False,
        "critical_validators_pass": False,
        "current_path_set_review_approved": False,
        "path_set_review_hashes_match": False,
        "path_validator_bundle_matches": False,
        "brief_gate_hashes_bound": False,
        "brief_manifest_accepted": False,
        "export_eligibility_calculated": False,
        "authorized_stop": False,
        "active_work_drained": False,
        "retry_budget_remaining": False,
        "release_set_unchanged": False,
        "approved_replacement_release": False,
        "retry_budget_exhausted": False,
        "retention_allows_archive": False,
    }
    values.update(overrides)
    return values


def _passing_guard_data() -> dict[str, object]:
    values = _guard_data()
    for field, value in tuple(values.items()):
        if isinstance(value, bool):
            values[field] = True
    values.update(
        {
            "accepted_stage_output_artifact_ref_id": _uuid7(
                second=1_700_000_010,
                random_value=10,
            ),
            "current_path_set_id": _uuid7(
                second=1_700_000_011,
                random_value=11,
            ),
            "approved_path_review_id": _uuid7(
                second=1_700_000_012,
                random_value=12,
            ),
            "current_path_set_sha256": "a" * 64,
            "approved_path_review_sha256": "b" * 64,
            "brief_gate_sha256": "c" * 64,
            "path_validator_bundle_version": "path-validator/1.0.0",
            "retryable_failure_code": "provider_timeout",
        }
    )
    return values


def _snapshot_for_state(state_value: str):
    from app.domain.run_attempt import RunSnapshot, RunStageCode, RunState

    state = RunState(state_value)
    current_stage = (
        RunStageCode(state.value)
        if state.value in {stage.value for stage in RunStageCode}
        else None
    )
    return RunSnapshot(
        **{
            **_snapshot_data(),
            "state": state,
            "current_stage_code": current_stage,
        }
    )


def test_run_state_vocabulary_is_exact() -> None:
    from app.domain.run_attempt import RunState

    assert tuple(state.value for state in RunState) == (
        "DRAFT",
        "NEEDS_REVIEW",
        "BLOCKED",
        "READY",
        "QUEUED",
        "PREPARING",
        "EXTRACTING",
        "REVIEWING_CONDITIONS",
        "GENERATING_PROFILES",
        "CONSTRUCTING_SCENARIOS",
        "GENERATING_PATHS",
        "SYNTHESIZING",
        "VALIDATING_OUTPUT",
        "GENERATING_BRIEF",
        "STOP_REQUESTED",
        "STOPPED",
        "FAILED_RETRYABLE",
        "FAILED_TERMINAL",
        "COMPLETED",
        "ARCHIVED",
    )


def test_stage_command_and_event_vocabularies_are_exact() -> None:
    from app.domain.run_attempt import (
        RunCommandKind,
        RunEventType,
        RunStageAttemptState,
        RunStageCode,
    )

    assert tuple(stage.value for stage in RunStageCode) == (
        "PREPARING",
        "EXTRACTING",
        "REVIEWING_CONDITIONS",
        "GENERATING_PROFILES",
        "CONSTRUCTING_SCENARIOS",
        "GENERATING_PATHS",
        "SYNTHESIZING",
        "VALIDATING_OUTPUT",
        "GENERATING_BRIEF",
    )
    assert tuple(state.value for state in RunStageAttemptState) == (
        "PENDING",
        "READY",
        "RUNNING",
        "VALIDATING",
        "SUCCEEDED",
        "RETRY_WAIT",
        "FAILED_TERMINAL",
        "CANCEL_REQUESTED",
        "CANCELLED",
    )
    assert tuple(command.value for command in RunCommandKind) == (
        "SUBMIT_FOR_REVIEW",
        "BLOCK_REVIEW",
        "RESUBMIT_REVIEW",
        "APPROVE_CONFIGURATION",
        "START_RUN",
        "ACCEPT_WORKFLOW",
        "SUCCEED_STAGE",
        "REQUEST_STOP",
        "CONFIRM_STOPPED",
        "RECORD_RETRYABLE_FAILURE",
        "ACCEPT_RETRY",
        "EXHAUST_RETRY_BUDGET",
        "ARCHIVE_RUN",
    )
    assert tuple(event.value for event in RunEventType) == (
        "RUN_CREATED",
        "RUN_STATE_CHANGED",
        "RERUN_CREATED",
        "STAGE_ATTEMPT_CREATED",
        "STAGE_STATE_CHANGED",
        "STAGE_LEASE_CLAIMED",
        "STAGE_LEASE_EXPIRED",
        "STAGE_OUTPUT_ACCEPTED",
        "STAGE_OUTPUT_QUARANTINED",
        "RUN_STOP_FENCE_ADVANCED",
        "RETRY_BUDGET_EXHAUSTED",
        "RUN_ARCHIVED",
    )


def test_run_snapshot_guard_facts_and_transition_are_strict_frozen_models() -> None:
    from app.domain.decision_workspace import TruthBundle
    from app.domain.run_attempt import (
        RunCommandKind,
        RunEventType,
        RunGuardFacts,
        RunSnapshot,
        RunState,
        RunTransition,
    )

    snapshot = RunSnapshot(**_snapshot_data())
    guards = RunGuardFacts(**_guard_data())
    transition = RunTransition(
        command=RunCommandKind.SUBMIT_FOR_REVIEW,
        from_state=RunState.DRAFT,
        to_state=RunState.NEEDS_REVIEW,
        next_version=2,
        event_type=RunEventType.RUN_STATE_CHANGED,
    )

    assert snapshot.truth == TruthBundle.synthetic()
    assert guards.authorized_stop is False
    assert transition.next_version == 2
    with pytest.raises(ValidationError):
        snapshot.version = 2
    with pytest.raises(ValidationError):
        RunSnapshot(**{**_snapshot_data(), "version": "1"})
    with pytest.raises(ValidationError):
        RunGuardFacts(**_guard_data(authorized_stop=1))


@pytest.mark.parametrize(("from_state", "command", "to_state"), ALLOWED_RUN_TRANSITIONS)
def test_every_allowed_run_transition_is_decided(
    from_state: str,
    command: str,
    to_state: str,
) -> None:
    from app.domain.run_attempt import (
        RunCommandKind,
        RunGuardFacts,
        RunState,
        decide_run_transition,
    )

    snapshot = _snapshot_for_state(from_state)
    transition = decide_run_transition(
        snapshot,
        command=RunCommandKind(command),
        guards=RunGuardFacts(**_passing_guard_data()),
    )

    assert transition.from_state is RunState(from_state)
    assert transition.to_state is RunState(to_state)
    assert transition.next_version == snapshot.version + 1
