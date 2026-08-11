"""Durable per-platform runtime control queue for simulation workers."""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SUPPORTED_PLATFORMS = ("twitter", "reddit")
SUPPORTED_COMMANDS = (
    "inject_post",
    "inject_event",
    "pause_after_round",
    "resume",
    "stop",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_copy(value: Any) -> Any:
    """Detach caller-owned data and reject non-JSON command payloads."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"runtime control artifact must be an object: {path.name}")
    return payload


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _atomic_create_json(path: Path, payload: Dict[str, Any]) -> bool:
    """Publish JSON atomically without ever replacing an existing artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            return False
        return True
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _exclusive_file_lock(path: Path, timeout_seconds: float = 5.0):
    """Kernel-managed cross-process lock released automatically on crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"0")
            os.fsync(fd)
        deadline = time.monotonic() + timeout_seconds
        while True:
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("runtime control store lock timed out") from exc
                time.sleep(0.01)
        try:
            yield
        finally:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class RuntimeControlStore:
    """Filesystem queue shared by HTTP workers and the OASIS runtime process."""

    def __init__(
        self,
        simulation_dir: str,
        *,
        attempt_id: Optional[str] = None,
        fencing_token: Optional[int] = None,
    ):
        if (attempt_id is None) != (fencing_token is None):
            raise ValueError("attempt_id and fencing_token must be provided together")
        if attempt_id is not None and not str(attempt_id).strip():
            raise ValueError("attempt_id must not be blank")
        if fencing_token is not None and (
            isinstance(fencing_token, bool) or not isinstance(fencing_token, int)
        ):
            raise ValueError("fencing_token must be an integer")
        self.simulation_dir = Path(simulation_dir)
        self.attempt_id = str(attempt_id) if attempt_id is not None else None
        self.fencing_token = fencing_token
        self.root = self.simulation_dir / "runtime_controls"
        self.manifests_dir = self.root / "manifests"
        self.state_dir = self.root / "platform_state"

    @staticmethod
    def _validate_platform(platform: str) -> str:
        normalized = str(platform or "").strip().lower()
        if normalized not in SUPPORTED_PLATFORMS:
            raise ValueError(f"unsupported runtime control platform: {platform}")
        return normalized

    @classmethod
    def _normalize_platforms(cls, platforms: Iterable[str]) -> List[str]:
        if isinstance(platforms, (str, bytes)):
            raise ValueError("platforms must be a non-empty list")
        normalized: List[str] = []
        for platform in platforms or []:
            value = cls._validate_platform(platform)
            if value not in normalized:
                normalized.append(value)
        if not normalized:
            raise ValueError("platforms must include twitter or reddit")
        return normalized

    @staticmethod
    def _validate_control_id(control_id: str) -> Optional[str]:
        try:
            parsed = uuid.UUID(str(control_id))
        except (TypeError, ValueError, AttributeError):
            return None
        return str(parsed)

    def _artifact_path(self, stage: str, platform: str, control_id: str) -> Path:
        return self.root / stage / platform / f"{control_id}.json"

    def enqueue(
        self,
        command_type: str,
        args: dict,
        platforms: list[str],
        *,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        if self.attempt_id is None or self.fencing_token is None:
            raise ValueError("enqueue requires a bound runtime attempt")
        normalized_command = str(command_type or "").strip().lower()
        if normalized_command not in SUPPORTED_COMMANDS:
            raise ValueError(f"unsupported runtime control: {command_type}")
        if not isinstance(args, dict):
            raise ValueError("runtime control args must be an object")

        targets = self._normalize_platforms(platforms)
        detached_args = _json_copy(args)
        request_fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "command_type": normalized_command,
                    "args": detached_args,
                    "expected_platforms": targets,
                    "attempt_id": self.attempt_id,
                    "fencing_token": self.fencing_token,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        normalized_key = str(idempotency_key or "").strip()
        if len(normalized_key) > 200:
            raise ValueError("idempotency_key must be at most 200 characters")
        if normalized_key:
            key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
            control_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{self.simulation_dir.resolve()}:{self.attempt_id}:{key_hash}",
                )
            )
        else:
            key_hash = None
            control_id = str(uuid.uuid4())

        manifest_path = self.manifests_dir / f"{control_id}.json"
        lock_path = self.root / ".enqueue.lock"
        with _exclusive_file_lock(lock_path):
            if manifest_path.exists():
                existing = _read_json(manifest_path)
                if existing.get("request_fingerprint") != request_fingerprint:
                    raise ValueError("idempotency_key_conflict")
                return self.get_status(control_id) or existing

            existing_copy = None
            for platform in SUPPORTED_PLATFORMS:
                for stage in ("pending", "processing", "receipts"):
                    candidate = self._artifact_path(stage, platform, control_id)
                    if not candidate.exists():
                        continue
                    payload = _read_json(candidate)
                    if payload.get("request_fingerprint") != request_fingerprint:
                        raise ValueError("idempotency_key_conflict")
                    existing_copy = existing_copy or payload

            if existing_copy is not None:
                enqueue_sequence = existing_copy.get("enqueue_sequence")
                created_at = existing_copy.get("created_at") or _utc_now()
                if not isinstance(enqueue_sequence, int):
                    raise ValueError("partial runtime control has no enqueue sequence")
            else:
                counter_path = self.root / "enqueue_sequence.json"
                counter = 0
                if counter_path.exists():
                    counter = int(_read_json(counter_path).get("sequence", 0))
                enqueue_sequence = counter + 1
                _atomic_write_json(
                    counter_path,
                    {"sequence": enqueue_sequence, "updated_at": _utc_now()},
                )
                created_at = _utc_now()

            manifest = {
                "control_id": control_id,
                "command_type": normalized_command,
                "args": detached_args,
                "platforms": targets,
                "expected_platforms": targets,
                "attempt_id": self.attempt_id,
                "fencing_token": self.fencing_token,
                "idempotency_key_hash": key_hash,
                "request_fingerprint": request_fingerprint,
                "enqueue_sequence": enqueue_sequence,
                "status": "queued",
                "created_at": created_at,
            }

            for platform in targets:
                command = {**manifest, "platform": platform}
                command_path = self._artifact_path("pending", platform, control_id)
                if not _atomic_create_json(command_path, command):
                    current = _read_json(command_path)
                    if current.get("request_fingerprint") != request_fingerprint:
                        raise ValueError("idempotency_key_conflict")

            # Claimers ignore every copy until this no-overwrite commit point.
            if not _atomic_create_json(manifest_path, manifest):
                current = _read_json(manifest_path)
                if current.get("request_fingerprint") != request_fingerprint:
                    raise ValueError("idempotency_key_conflict")
                return self.get_status(control_id) or current

            return copy.deepcopy(manifest)

    def claim_next(self, platform: str) -> dict | None:
        if self.attempt_id is None or self.fencing_token is None:
            raise ValueError("claim_next requires a bound runtime attempt")
        target = self._validate_platform(platform)
        pending_dir = self.root / "pending" / target
        candidates = []
        for path in pending_dir.glob("*.json"):
            try:
                command = _read_json(path)
            except FileNotFoundError:
                continue
            sequence = command.get("enqueue_sequence")
            if not isinstance(sequence, int):
                continue
            candidates.append((sequence, path.name, path))

        for _, _, source in sorted(candidates):
            control_id = source.stem
            manifest_path = self.manifests_dir / f"{control_id}.json"
            if not manifest_path.exists():
                continue
            manifest = _read_json(manifest_path)
            if (
                manifest.get("attempt_id") != self.attempt_id
                or manifest.get("fencing_token") != self.fencing_token
                or target not in (manifest.get("expected_platforms") or [])
            ):
                continue
            destination = self._artifact_path("processing", target, control_id)
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                # A hard-link reservation is no-overwrite atomic. Moving with
                # os.replace alone lets two Windows claimers both succeed in a
                # tight race because replacement permits an existing target.
                os.link(source, destination)
            except (FileExistsError, FileNotFoundError):
                continue
            try:
                source.unlink()
            except FileNotFoundError:
                pass
            command = _read_json(destination)
            if (
                command.get("platform") != target
                or command.get("request_fingerprint")
                != manifest.get("request_fingerprint")
                or command.get("attempt_id") != self.attempt_id
                or command.get("fencing_token") != self.fencing_token
            ):
                raise ValueError("claimed runtime control does not match its manifest")
            return command
        return None

    def _write_receipt(
        self,
        platform: str,
        command: dict,
        *,
        status: str,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> dict:
        target = self._validate_platform(platform)
        if not isinstance(command, dict):
            raise ValueError("claimed runtime control must be an object")
        control_id = self._validate_control_id(command.get("control_id"))
        if control_id is None:
            raise ValueError("claimed runtime control has an invalid control_id")
        if command.get("platform") != target:
            raise ValueError("claimed runtime control platform mismatch")

        receipt_path = self._artifact_path("receipts", target, control_id)
        receipt = {
            "control_id": control_id,
            "command_type": command.get("command_type"),
            "platform": target,
            "platforms": list(command.get("platforms") or [target]),
            "expected_platforms": list(
                command.get("expected_platforms")
                or command.get("platforms")
                or [target]
            ),
            "attempt_id": command.get("attempt_id"),
            "fencing_token": command.get("fencing_token"),
            "request_fingerprint": command.get("request_fingerprint"),
            "enqueue_sequence": command.get("enqueue_sequence"),
            "status": status,
            "created_at": command.get("created_at"),
            "completed_at": _utc_now(),
            "result": _json_copy(result or {}) if status == "completed" else None,
            "error": str(error) if error is not None else None,
        }
        if not _atomic_create_json(receipt_path, receipt):
            existing = _read_json(receipt_path)
            if (
                existing.get("attempt_id") != command.get("attempt_id")
                or existing.get("fencing_token") != command.get("fencing_token")
                or existing.get("request_fingerprint")
                != command.get("request_fingerprint")
            ):
                raise ValueError("runtime control receipt identity conflict")
            return existing
        return copy.deepcopy(receipt)

    def complete(
        self,
        platform: str,
        command: dict,
        result: dict,
    ) -> dict:
        if not isinstance(result, dict):
            raise ValueError("runtime control result must be an object")
        return self._write_receipt(
            platform,
            command,
            status="completed",
            result=result,
        )

    def fail(self, platform: str, command: dict, error: str) -> dict:
        return self._write_receipt(
            platform,
            command,
            status="failed",
            error=str(error),
        )

    def get_status(self, control_id: str) -> dict | None:
        normalized_id = self._validate_control_id(control_id)
        if normalized_id is None:
            return None
        manifest_path = self.manifests_dir / f"{normalized_id}.json"
        if not manifest_path.exists():
            return None

        manifest = _read_json(manifest_path)
        platforms = self._normalize_platforms(
            manifest.get("expected_platforms") or manifest.get("platforms") or []
        )
        platform_statuses: Dict[str, Dict[str, Any]] = {}
        completed_results: Dict[str, Dict[str, Any]] = {}
        errors: Dict[str, str] = {}

        for platform in platforms:
            receipt_path = self._artifact_path(
                "receipts", platform, normalized_id
            )
            processing_path = self._artifact_path(
                "processing", platform, normalized_id
            )
            if receipt_path.exists():
                receipt = _read_json(receipt_path)
                entry = {
                    "status": receipt.get("status", "failed"),
                    "completed_at": receipt.get("completed_at"),
                }
                if receipt.get("status") == "completed":
                    result = receipt.get("result") or {}
                    entry["result"] = result
                    completed_results[platform] = result
                else:
                    error = str(receipt.get("error") or "runtime control failed")
                    entry["error"] = error
                    errors[platform] = error
                platform_statuses[platform] = entry
            elif processing_path.exists():
                platform_statuses[platform] = {"status": "processing"}
            else:
                platform_statuses[platform] = {"status": "queued"}

        states = [entry["status"] for entry in platform_statuses.values()]
        if states and all(state == "completed" for state in states):
            aggregate = "completed"
        elif states and all(state in {"completed", "failed"} for state in states):
            aggregate = "failed" if "failed" in states else "completed"
        elif any(state in {"processing", "completed", "failed"} for state in states):
            aggregate = "processing"
        else:
            aggregate = "queued"

        response = {
            **manifest,
            "status": aggregate,
            "platform_statuses": platform_statuses,
        }
        if completed_results:
            response["result"] = completed_results
        if errors:
            response["errors"] = errors
        return response

    def write_platform_state(self, platform: str, state: dict) -> None:
        target = self._validate_platform(platform)
        if not isinstance(state, dict):
            raise ValueError("runtime platform state must be an object")
        payload = {
            **_json_copy(state),
            "platform": target,
            "attempt_id": self.attempt_id,
            "fencing_token": self.fencing_token,
            "updated_at": _utc_now(),
        }
        _atomic_write_json(self.state_dir / f"{target}.json", payload)

    def get_platform_states(self) -> dict:
        states: Dict[str, Dict[str, Any]] = {}
        for platform in SUPPORTED_PLATFORMS:
            path = self.state_dir / f"{platform}.json"
            if path.exists():
                states[platform] = _read_json(path)
        return states

    def list_receipts(
        self,
        *,
        command_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        receipts: List[Dict[str, Any]] = []
        for platform in SUPPORTED_PLATFORMS:
            for path in (self.root / "receipts" / platform).glob("*.json"):
                receipt = _read_json(path)
                if command_type and receipt.get("command_type") != command_type:
                    continue
                receipts.append(receipt)
        return sorted(
            receipts,
            key=lambda item: (str(item.get("completed_at") or ""), str(item.get("platform") or "")),
        )

    def find_completed_control(
        self,
        command_type: str,
        *,
        attempt_id: str,
        fencing_token: int,
    ) -> dict | None:
        """Find the latest fully receipted control for one current attempt."""
        candidates = []
        for path in self.manifests_dir.glob("*.json"):
            manifest = _read_json(path)
            if (
                manifest.get("command_type") != command_type
                or manifest.get("attempt_id") != attempt_id
                or manifest.get("fencing_token") != fencing_token
            ):
                continue
            sequence = manifest.get("enqueue_sequence")
            if isinstance(sequence, int):
                candidates.append((sequence, manifest["control_id"]))
        for _, control_id in sorted(candidates, reverse=True):
            status = self.get_status(control_id)
            if status and status.get("status") == "completed":
                return status
        return None
