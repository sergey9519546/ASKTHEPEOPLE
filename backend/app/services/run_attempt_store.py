"""Durable filesystem ownership for simulation runtime attempts."""

from __future__ import annotations

import errno
import json
import math
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Iterator


_ATTEMPT_FILENAME = "run_attempt.json"
_COUNTER_FILENAME = "run_attempt_counter.json"
_LOCK_FILENAME = ".run_attempt.lock"
_LOCK_TIMEOUT_SECONDS = 2.0
_LOCK_RETRY_SECONDS = 0.01
_STALE_LOCK_AGE_SECONDS = 60.0
_TERMINAL_STATUSES = frozenset(
    {"completed", "failed", "stopped", "interrupted", "expired"}
)


def _pid_is_alive(pid: int) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        still_active = 259
        access_denied = 5
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if not handle:
            return ctypes.get_last_error() == access_denied
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        return exc.errno != errno.ESRCH
    return True


def _read_lock_record(lock_path: str) -> tuple[int, str] | None:
    try:
        with open(lock_path, "r", encoding="ascii") as handle:
            data = json.load(handle)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    pid = data.get("pid")
    token = data.get("token")
    if (
        isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or not isinstance(token, str)
        or not token
    ):
        return None
    return pid, token


def _unlink_lock_if_token_matches(lock_path: str, expected_token: str) -> bool:
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    while True:
        record = _read_lock_record(lock_path)
        if record is None or record[1] != expected_token:
            return False
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            return False
        except PermissionError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(_LOCK_RETRY_SECONDS)
            continue
        return True


@dataclass(frozen=True)
class RunAttempt:
    simulation_id: str
    attempt_id: str
    owner_id: str
    fencing_token: int
    status: str
    acquired_at: str
    heartbeat_at: str
    expires_at: str


class RunAttemptHeld(RuntimeError):
    """Raised when another owner has a live attempt for the simulation."""


class StaleRunAttempt(RuntimeError):
    """Raised when an owner no longer holds the active fencing token."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_ttl(ttl_seconds: float) -> float:
    try:
        ttl = float(ttl_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("ttl_seconds must be a positive finite number") from exc
    if not math.isfinite(ttl) or ttl <= 0:
        raise ValueError("ttl_seconds must be a positive finite number")
    return ttl


class RunAttemptStore:
    """Persist a single current attempt and a monotonic fencing counter."""

    def acquire(
        self,
        simulation_dir: str,
        simulation_id: str,
        owner_id: str,
        ttl_seconds: float,
    ) -> RunAttempt:
        ttl = _validate_ttl(ttl_seconds)
        if not simulation_id or not owner_id:
            raise ValueError("simulation_id and owner_id are required")
        os.makedirs(simulation_dir, exist_ok=True)

        with self._lock(simulation_dir):
            now = _utc_now()
            current = self._read_unlocked(simulation_dir)
            if (
                current is not None
                and current.status == "active"
                and _parse_timestamp(current.expires_at) > now
            ):
                raise RunAttemptHeld(
                    f"simulation {simulation_id} is held by {current.owner_id}"
                )

            counter = max(
                current.fencing_token if current is not None else 0,
                self._read_counter_unlocked(simulation_dir),
            ) + 1
            timestamp = now.isoformat()
            attempt = RunAttempt(
                simulation_id=simulation_id,
                attempt_id=str(uuid.uuid4()),
                owner_id=owner_id,
                fencing_token=counter,
                status="active",
                acquired_at=timestamp,
                heartbeat_at=timestamp,
                expires_at=(now + timedelta(seconds=ttl)).isoformat(),
            )
            self._write_json_atomic(
                os.path.join(simulation_dir, _COUNTER_FILENAME),
                {"fencing_token": counter},
            )
            self._write_attempt_unlocked(simulation_dir, attempt)
            return attempt

    def read(self, simulation_dir: str) -> RunAttempt | None:
        return self._read_unlocked(simulation_dir)

    def heartbeat(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
        ttl_seconds: float,
    ) -> RunAttempt:
        ttl = _validate_ttl(ttl_seconds)
        with self._lock(simulation_dir):
            now = _utc_now()
            current = self._assert_owner_unlocked(
                simulation_dir, attempt_id, fencing_token, now
            )
            renewed = replace(
                current,
                heartbeat_at=now.isoformat(),
                expires_at=(now + timedelta(seconds=ttl)).isoformat(),
            )
            self._write_attempt_unlocked(simulation_dir, renewed)
            return renewed

    def assert_owner(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
    ) -> RunAttempt:
        with self._lock(simulation_dir):
            return self._assert_owner_unlocked(
                simulation_dir, attempt_id, fencing_token, _utc_now()
            )

    def write_owned_run_state(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
        payload: dict,
    ) -> None:
        """Validate ownership and replace run state under one lock."""
        with self._lock(simulation_dir):
            self._assert_owner_unlocked(
                simulation_dir, attempt_id, fencing_token, _utc_now()
            )
            if (
                payload.get("attempt_id") != attempt_id
                or payload.get("fencing_token") != fencing_token
            ):
                raise StaleRunAttempt(
                    "run-state payload does not match the active attempt"
                )
            self._write_json_atomic(
                os.path.join(simulation_dir, "run_state.json"), payload
            )

    def reconcile_stale_run_state(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
        payload: dict,
        now: datetime | None = None,
    ) -> RunAttempt | None:
        """Write interrupted state before expiring the same stale attempt."""
        effective_now = self._normalize_now(now)
        with self._lock(simulation_dir):
            current = self._read_unlocked(simulation_dir)
            if (
                current is None
                or current.status != "active"
                or current.attempt_id != attempt_id
                or current.fencing_token != fencing_token
                or _parse_timestamp(current.expires_at) > effective_now
            ):
                return None

            state_path = os.path.join(simulation_dir, "run_state.json")
            persisted_state = self._read_json_unlocked(state_path)
            if (
                persisted_state is None
                or persisted_state.get("attempt_id") != current.attempt_id
                or persisted_state.get("fencing_token") != current.fencing_token
                or payload.get("attempt_id") != current.attempt_id
                or payload.get("fencing_token") != current.fencing_token
            ):
                return None

            self._write_json_atomic(state_path, payload)
            expired = replace(current, status="expired")
            self._write_attempt_unlocked(simulation_dir, expired)
            return expired

    def release(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
        status: str,
    ) -> RunAttempt:
        if status not in _TERMINAL_STATUSES:
            raise ValueError(f"invalid terminal run-attempt status: {status}")
        with self._lock(simulation_dir):
            current = self._assert_owner_unlocked(
                simulation_dir, attempt_id, fencing_token, _utc_now()
            )
            terminal = replace(current, status=status)
            self._write_attempt_unlocked(simulation_dir, terminal)
            return terminal

    def expire_if_stale(
        self,
        simulation_dir: str,
        now: datetime | None = None,
    ) -> RunAttempt | None:
        effective_now = self._normalize_now(now)

        with self._lock(simulation_dir):
            current = self._read_unlocked(simulation_dir)
            if (
                current is None
                or current.status != "active"
                or _parse_timestamp(current.expires_at) > effective_now
            ):
                return None
            expired = replace(current, status="expired")
            self._write_attempt_unlocked(simulation_dir, expired)
            return expired

    def _assert_owner_unlocked(
        self,
        simulation_dir: str,
        attempt_id: str,
        fencing_token: int,
        now: datetime,
    ) -> RunAttempt:
        current = self._read_unlocked(simulation_dir)
        if (
            current is None
            or current.status != "active"
            or current.attempt_id != attempt_id
            or current.fencing_token != fencing_token
            or _parse_timestamp(current.expires_at) <= now
        ):
            raise StaleRunAttempt(
                f"run attempt {attempt_id} no longer owns fencing token {fencing_token}"
            )
        return current

    def _read_unlocked(self, simulation_dir: str) -> RunAttempt | None:
        path = os.path.join(simulation_dir, _ATTEMPT_FILENAME)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return RunAttempt(**json.load(handle))

    def _read_counter_unlocked(self, simulation_dir: str) -> int:
        path = os.path.join(simulation_dir, _COUNTER_FILENAME)
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as handle:
            return int(json.load(handle).get("fencing_token", 0))

    @staticmethod
    def _read_json_unlocked(path: str) -> dict | None:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _normalize_now(now: datetime | None) -> datetime:
        effective_now = now or _utc_now()
        if effective_now.tzinfo is None:
            return effective_now.replace(tzinfo=timezone.utc)
        return effective_now.astimezone(timezone.utc)

    def _write_attempt_unlocked(
        self, simulation_dir: str, attempt: RunAttempt
    ) -> None:
        self._write_json_atomic(
            os.path.join(simulation_dir, _ATTEMPT_FILENAME), asdict(attempt)
        )

    @staticmethod
    def _write_json_atomic(path: str, payload: dict) -> None:
        temp_path = f"{path}.{uuid.uuid4().hex}.tmp"
        fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except BaseException:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def _lock(self, simulation_dir: str) -> Iterator[None]:
        os.makedirs(simulation_dir, exist_ok=True)
        lock_path = os.path.join(simulation_dir, _LOCK_FILENAME)
        deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
        lock_token = uuid.uuid4().hex
        while True:
            try:
                fd = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                break
            except (FileExistsError, PermissionError) as exc:
                if not os.path.exists(lock_path):
                    raise
                record = _read_lock_record(lock_path)
                try:
                    lock_age = time.time() - os.path.getmtime(lock_path)
                except FileNotFoundError:
                    continue
                if (
                    record is not None
                    and lock_age >= _STALE_LOCK_AGE_SECONDS
                    and not _pid_is_alive(record[0])
                    and _unlink_lock_if_token_matches(lock_path, record[1])
                ):
                    continue
                if time.monotonic() >= deadline:
                    raise RunAttemptHeld(
                        f"timed out acquiring run-attempt lock for {simulation_dir}"
                    ) from exc
                time.sleep(_LOCK_RETRY_SECONDS)

        try:
            with os.fdopen(fd, "w", encoding="ascii") as handle:
                json.dump(
                    {"pid": os.getpid(), "token": lock_token},
                    handle,
                    separators=(",", ":"),
                )
            yield
        finally:
            _unlink_lock_if_token_matches(lock_path, lock_token)
