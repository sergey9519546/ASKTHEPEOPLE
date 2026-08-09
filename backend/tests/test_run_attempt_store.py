"""Filesystem-backed ownership tests for durable simulation attempts."""

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.services import run_attempt_store as run_attempt_store_module
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


def test_owned_run_state_write_holds_lock_through_owner_check_and_replace(
    monkeypatch, tmp_path
):
    store = RunAttemptStore()
    attempt = store.acquire(str(tmp_path), "sim-atomic-save", "worker-1", 30)
    assert hasattr(store, "write_owned_run_state"), (
        "owned run-state writes must be provided by RunAttemptStore"
    )

    write_started = threading.Event()
    allow_write = threading.Event()
    rotation_done = threading.Event()
    original_write = store._write_json_atomic

    def paused_write(path, payload):
        if os.path.basename(path) == "run_state.json":
            write_started.set()
            assert allow_write.wait(timeout=2)
        original_write(path, payload)

    monkeypatch.setattr(store, "_write_json_atomic", paused_write)
    writer = threading.Thread(
        target=store.write_owned_run_state,
        args=(
            str(tmp_path),
            attempt.attempt_id,
            attempt.fencing_token,
            {"attempt_id": attempt.attempt_id, "fencing_token": attempt.fencing_token},
        ),
        daemon=True,
    )

    def rotate_owner():
        store.expire_if_stale(str(tmp_path), _future(31))
        store.acquire(str(tmp_path), "sim-atomic-save", "worker-2", 30)
        rotation_done.set()

    rotator = threading.Thread(target=rotate_owner, daemon=True)
    try:
        writer.start()
        assert write_started.wait(timeout=2)
        rotator.start()
        time.sleep(0.05)
        assert not rotation_done.is_set()
    finally:
        allow_write.set()
        writer.join(timeout=2)
        if rotator.ident is not None:
            rotator.join(timeout=2)

    assert not writer.is_alive()
    assert not rotator.is_alive()
    assert rotation_done.is_set()
    persisted = json.loads((tmp_path / "run_state.json").read_text("utf-8"))
    assert persisted["attempt_id"] == attempt.attempt_id
    assert store.read(str(tmp_path)).fencing_token == attempt.fencing_token + 1


def test_stale_reconciliation_is_ordered_and_rejects_newer_attempt(
    monkeypatch, tmp_path
):
    store = RunAttemptStore()
    assert hasattr(store, "reconcile_stale_run_state"), (
        "stale reconciliation must be a single store operation"
    )

    order_dir = tmp_path / "ordered"
    first = store.acquire(str(order_dir), "sim-reconcile-order", "worker-1", 30)
    (order_dir / "run_state.json").write_text(
        json.dumps(
            {
                "simulation_id": "sim-reconcile-order",
                "attempt_id": first.attempt_id,
                "fencing_token": first.fencing_token,
                "runner_status": "running",
            }
        ),
        encoding="utf-8",
    )
    writes = []
    original_write = store._write_json_atomic

    def record_write(path, payload):
        writes.append(os.path.basename(path))
        original_write(path, payload)

    monkeypatch.setattr(store, "_write_json_atomic", record_write)
    reconciled = store.reconcile_stale_run_state(
        str(order_dir),
        first.attempt_id,
        first.fencing_token,
        {
            "simulation_id": "sim-reconcile-order",
            "attempt_id": first.attempt_id,
            "fencing_token": first.fencing_token,
            "runner_status": "interrupted",
        },
        now=_future(31),
    )

    assert reconciled.status == "expired"
    assert writes[-2:] == ["run_state.json", "run_attempt.json"]

    identity_dir = tmp_path / "identity"
    stale = store.acquire(str(identity_dir), "sim-reconcile-id", "worker-1", 30)
    attempt_path = identity_dir / "run_attempt.json"
    attempt_data = json.loads(attempt_path.read_text("utf-8"))
    attempt_data["expires_at"] = (_future(-1)).isoformat()
    attempt_path.write_text(json.dumps(attempt_data), encoding="utf-8")
    newer = store.acquire(str(identity_dir), "sim-reconcile-id", "worker-2", 30)
    newer_state = {
        "simulation_id": "sim-reconcile-id",
        "attempt_id": newer.attempt_id,
        "fencing_token": newer.fencing_token,
        "runner_status": "running",
    }
    (identity_dir / "run_state.json").write_text(
        json.dumps(newer_state), encoding="utf-8"
    )

    result = store.reconcile_stale_run_state(
        str(identity_dir),
        stale.attempt_id,
        stale.fencing_token,
        {
            "simulation_id": "sim-reconcile-id",
            "attempt_id": stale.attempt_id,
            "fencing_token": stale.fencing_token,
            "runner_status": "interrupted",
        },
        now=_future(31),
    )

    assert result is None
    assert store.read(str(identity_dir)) == newer
    assert json.loads((identity_dir / "run_state.json").read_text("utf-8")) == newer_state


def test_lock_owner_record_contains_pid_and_unique_token(tmp_path):
    store = RunAttemptStore()
    lock_path = tmp_path / ".run_attempt.lock"

    with store._lock(str(tmp_path)):
        pass
    first = json.loads(lock_path.read_text(encoding="ascii"))
    with store._lock(str(tmp_path)):
        pass
    second = json.loads(lock_path.read_text(encoding="ascii"))

    assert isinstance(first, dict)
    assert first["pid"] == os.getpid()
    assert first["token"]
    assert second["pid"] == os.getpid()
    assert second["token"] != first["token"]
    assert lock_path.exists()


def test_acquire_recovers_empty_lock_file_from_create_write_crash(tmp_path):
    lock_path = tmp_path / ".run_attempt.lock"
    lock_path.touch()

    attempt = RunAttemptStore().acquire(
        str(tmp_path), "sim-empty-lock", "worker-2", 30
    )

    assert attempt.owner_id == "worker-2"
    assert json.loads(lock_path.read_text(encoding="ascii"))["pid"] == os.getpid()


def test_aged_live_kernel_lock_cannot_be_stolen(monkeypatch, tmp_path):
    store = RunAttemptStore()
    lock_path = tmp_path / ".run_attempt.lock"
    entered = threading.Event()
    release = threading.Event()

    def hold_lock():
        with store._lock(str(tmp_path)):
            old = time.time() - 3600
            os.utime(lock_path, (old, old))
            entered.set()
            release.wait(timeout=2)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert entered.wait(timeout=1)

    try:
        monkeypatch.setattr(run_attempt_store_module, "_LOCK_TIMEOUT_SECONDS", 0.02)
        with pytest.raises(RunAttemptHeld):
            store.acquire(str(tmp_path), "sim-live-lock", "worker-2", 30)
    finally:
        release.set()
        holder.join(timeout=2)

    assert not holder.is_alive()


def test_concurrent_recoverers_never_overlap_critical_sections(tmp_path):
    store = RunAttemptStore()
    active = 0
    max_active = 0
    gate = threading.Barrier(3)
    state_guard = threading.Lock()

    def contend():
        nonlocal active, max_active
        gate.wait(timeout=2)
        with store._lock(str(tmp_path)):
            with state_guard:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.03)
            with state_guard:
                active -= 1

    contenders = [threading.Thread(target=contend) for _ in range(2)]
    for contender in contenders:
        contender.start()
    gate.wait(timeout=2)
    for contender in contenders:
        contender.join(timeout=2)

    assert all(not contender.is_alive() for contender in contenders)
    assert max_active == 1
