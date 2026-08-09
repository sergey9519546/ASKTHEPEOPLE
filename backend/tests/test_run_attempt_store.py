"""Filesystem-backed ownership tests for durable simulation attempts."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.run_attempt_store import (
    RunAttemptHeld,
    RunAttemptStore,
    StaleRunAttempt,
)


def _future(seconds: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def test_acquire_persists_active_attempt_and_rejects_competing_owner(tmp_path):
    store = RunAttemptStore()

    attempt = store.acquire(str(tmp_path), "sim-1", "worker-1", 30)

    assert attempt.simulation_id == "sim-1"
    assert attempt.owner_id == "worker-1"
    assert attempt.fencing_token == 1
    assert attempt.status == "active"
    assert store.read(str(tmp_path)) == attempt
    assert (tmp_path / "run_attempt.json").exists()

    with pytest.raises(RunAttemptHeld):
        store.acquire(str(tmp_path), "sim-1", "worker-2", 30)


def test_heartbeat_extends_lease_and_rejects_stale_fencing_token(tmp_path):
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), "sim-2", "worker-1", 30)

    renewed = store.heartbeat(
        str(tmp_path), attempt.attempt_id, attempt.fencing_token, 60
    )

    assert renewed.heartbeat_at >= attempt.heartbeat_at
    assert renewed.expires_at > attempt.expires_at
    with pytest.raises(StaleRunAttempt):
        store.heartbeat(str(tmp_path), attempt.attempt_id, 999, 60)


def test_release_preserves_terminal_attempt_and_rejects_stale_owner(tmp_path):
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), "sim-3", "worker-1", 30)

    released = store.release(
        str(tmp_path), attempt.attempt_id, attempt.fencing_token, "completed"
    )

    assert released.status == "completed"
    assert store.read(str(tmp_path)) == released
    with pytest.raises(StaleRunAttempt):
        store.assert_owner(str(tmp_path), attempt.attempt_id, attempt.fencing_token)


def test_expiry_is_terminal_and_next_attempt_increments_fencing_token(tmp_path):
    store = RunAttemptStore()
    first = store.acquire(str(tmp_path), "sim-4", "worker-1", 30)

    assert store.expire_if_stale(str(tmp_path), _future(31)).status == "expired"
    assert store.expire_if_stale(str(tmp_path), _future(32)) is None

    second = store.acquire(str(tmp_path), "sim-4", "worker-2", 30)
    assert second.attempt_id != first.attempt_id
    assert second.fencing_token == first.fencing_token + 1
    assert second.owner_id == "worker-2"


def test_fresh_attempt_does_not_expire(tmp_path):
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), "sim-5", "worker-1", 30)

    assert store.expire_if_stale(str(tmp_path), _future(1)) is None
    assert store.read(str(tmp_path)) == attempt
