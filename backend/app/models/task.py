"""
Task Status Management
Used to track long-running tasks (like simulation, graph building, report generation)
Distributed task state manager backed by Redis / Celery result backend.
"""

import hashlib
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from ..config import Config
from ..utils.logger import get_logger


def _audit(**kwargs):
    """Lazy import of audit_log.record_event to avoid a circular import
    (services/__init__ eagerly imports graph_builder → models.task)."""
    from ..services.audit_log import record_event
    record_event(**kwargs)

logger = get_logger('askthepeople.models.task')

try:  # redis is optional: the in-memory path must import cleanly without it.
    from redis.exceptions import WatchError
except Exception:  # pragma: no cover - exercised only where redis is absent
    class WatchError(Exception):
        """Stand-in so the transaction retry compiles without redis installed."""

# Task records expire from Redis after this long. The index that lists them is
# pruned on the same horizon so it cannot outlive the records it points at.
TASK_TTL_SECONDS = 86400

# The index of live task ids. A sorted set scored by creation time, so expired
# entries can be dropped by score without loading each record to check its age.
TASK_INDEX_KEY = "tasks:index"

# Superseded plain set. Retired on cleanup: it was written without a TTL and
# with no way to prune members whose task record had already expired, so it grew
# without bound. Kept named here only so the retirement is deliberate.
_LEGACY_TASK_INDEX_KEY = "tasks:all"

# How long to wait before re-probing Redis after a failed connection attempt.
# A one-shot probe meant a single blip at startup left the process in-memory
# only for its entire lifetime: the web process then never saw the worker's
# progress updates and every status poll 404'd until restart.
REDIS_RETRY_INTERVAL_SECONDS = 30.0

# Bound on an optimistic-concurrency retry loop. Contention here is between at
# most a handful of writers (one web process, --concurrency=2 workers), so the
# loop settles well inside this.
_MAX_UPDATE_ATTEMPTS = 5

# Idempotency keys can contain user-controlled text. Hashing keeps that text
# out of Redis key names and gives every process the same bounded key.
_IDEMPOTENCY_RESERVATION_PREFIX = "tasks:idempotency:v1:"
_IDEMPOTENCY_RESERVATION_VERSION = 1

_TERMINAL_STATUSES = frozenset()  # populated below, after TaskStatus exists


class TaskStateError(RuntimeError):
    """Stable fail-closed error for shared task-state operations."""


class TaskStateContentionError(TaskStateError):
    def __init__(self) -> None:
        super().__init__("task_state_contention")


class TaskStateUnavailable(TaskStateError):
    def __init__(self, code: str = "task_state_unavailable") -> None:
        super().__init__(code)


class TaskIdempotencyConflict(TaskStateError):
    def __init__(self) -> None:
        super().__init__("idempotency_key_conflict")


class TaskExecutionConflict(TaskStateError):
    """Another delivery owns the durable task-execution fence."""

    def __init__(self, code: str = "task_execution_in_progress") -> None:
        super().__init__(code)


class TaskStatus(str, Enum):
    """Task Status Enum"""
    PENDING = "pending"          # Pending
    PROCESSING = "processing"    # Processing
    COMPLETED = "completed"      # Completed
    FAILED = "failed"            # Failed
    CANCELLED = "cancelled"      # Cooperatively stopped by request


# A task that has completed, failed, or been cancelled is done. Later writes may still add
# detail, but they must not move it back to pending/processing.
_TERMINAL_STATUSES = frozenset({
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
})


@dataclass
class Task:
    """Task Data Class"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0              # Total progress percentage 0-100
    message: str = ""              # Status message
    result: Optional[Dict] = None  # Task result
    error: Optional[str] = None    # Error information
    public_error: Optional[str] = None  # Stable client-safe error code
    metadata: Dict = field(default_factory=dict)  # Additional metadata
    progress_detail: Dict = field(default_factory=dict)  # Detailed progress information
    idempotency_key: Optional[str] = None  # ADR-0003: dedupes double-submits
    idempotency_fingerprint: Optional[str] = None
    execution_owner: Optional[str] = None
    fencing_token: int = 0  # Gate 2: monotonic counter incremented on claim
    lease_expires_at: Optional[datetime] = None  # Gate 2: renewable lease horizon

    def to_dict(self) -> Dict[str, Any]:
        """Convert to an internal dictionary, including diagnostic details."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "public_error": self.public_error,
            "metadata": self.metadata,
            "idempotency_key": self.idempotency_key,
            "idempotency_fingerprint": self.idempotency_fingerprint,
            "execution_owner": self.execution_owner,
            "fencing_token": self.fencing_token,
            "lease_expires_at": (
                self.lease_expires_at.isoformat()
                if isinstance(self.lease_expires_at, datetime)
                else self.lease_expires_at
            ),
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Convert to a client-safe dictionary without diagnostic error text."""
        payload = self.to_dict()
        if self.status == TaskStatus.FAILED:
            payload["error"] = self.public_error or "task_failed"
        else:
            payload["error"] = None
        # Internal fencing credentials — never API data. The worker token,
        # the monotonic fencing token, and the lease horizon are all owned by
        # the worker layer; leaking the horizon lets a hostile client time a
        # takeover race against a wedged worker, and the fencing token is half
        # the renew_lease credential pair.
        payload.pop("execution_owner", None)
        payload.pop("fencing_token", None)
        payload.pop("lease_expires_at", None)
        return payload

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        """Reconstruct Task instance from dictionary."""
        created_at = d.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()

        updated_at = d.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = datetime.now()
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now()

        raw_status = d.get("status", TaskStatus.PENDING)
        try:
            status = TaskStatus(raw_status)
        except (TypeError, ValueError):
            raise TaskStateUnavailable("task_status_invalid") from None

        raw_lease = d.get("lease_expires_at")
        lease_expires_at = None
        if isinstance(raw_lease, str):
            try:
                lease_expires_at = datetime.fromisoformat(raw_lease)
            except ValueError:
                lease_expires_at = None
        elif isinstance(raw_lease, datetime):
            lease_expires_at = raw_lease

        return cls(
            task_id=d["task_id"],
            task_type=d.get("task_type", "unknown"),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            progress=d.get("progress", 0),
            message=d.get("message", ""),
            result=d.get("result"),
            error=d.get("error"),
            public_error=d.get("public_error"),
            metadata=d.get("metadata", {}),
            progress_detail=d.get("progress_detail", {}),
            idempotency_key=d.get("idempotency_key"),
            idempotency_fingerprint=d.get("idempotency_fingerprint"),
            execution_owner=d.get("execution_owner"),
            fencing_token=d.get("fencing_token", 0),
            lease_expires_at=lease_expires_at,
        )


# Renewable lease horizon for a durable execution claim (ADR-0003). While a
# worker heartbeats inside this window its PROCESSING claim is exclusive; once
# the lease lapses a new delivery may take over, bumping the fencing token.
# Tunable via env so a slow LLM provider can raise the horizon at deploy without
# a code change.
def _positive_int_env(name: str, default: int) -> int:
    """Read a positive-int env var, degraded (not bricked) on a malformed value.

    A non-integer falls back to the default rather than raising at import,
    mirroring how ``from_dict`` swallows malformed timestamps. A non-positive
    value is also rejected (e.g., a zero/negative lease horizon would make every
    claim immediately lapsed).
    """
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("%s=%r is not an int; falling back to %d", name, raw, default)
        return default
    if value <= 0:
        logger.warning("%s=%r must be positive; falling back to %d", name, raw, default)
        return default
    return value


LEASE_DURATION_SECONDS = _positive_int_env("TASK_LEASE_DURATION_SECONDS", 30)
# Legacy records (``lease_expires_at is None``) predate the renewable lease. The
# None-branch of ``_lease_is_lapsed`` falls back to ``updated_at`` rather than
# treating them as instantly lapsed, so a rolling deploy does not seize a live
# old-code worker. Because old-code report workers do not refresh
# ``task.updated_at`` mid-run, this grace must comfortably exceed the longest
# plausible report run or a slow-but-alive legacy worker would be seized after
# the grace expires. The default 6x multiple lets a legacy worker stay unseized
# for ~3min; raise ``TASK_MIGRATION_GRACE_MULTIPLIER`` before deploying if
# reports routinely take longer. Decoupled from ``TASK_LEASE_DURATION_SECONDS``
# so an operator can widen the migration grace during a rolling deploy without
# also delaying crash-recovery latency for new-code workers (which refresh the
# lease every checkpoint).
LEASE_GRACE_MULTIPLIER = _positive_int_env("TASK_MIGRATION_GRACE_MULTIPLIER", 6)


def _lease_is_lapsed(task: "Task", now: datetime) -> bool:
    """True if a PROCESSING task's renewable lease has expired.

    A live lease horizon is checked directly. A legacy record written before
    leases existed carries ``lease_expires_at is None``; rather than treating
    that as immediately lapsed (which would silently seize an in-flight claim
    during a rolling deploy), fall back to the task's last progress write
    (``updated_at``). Old-code report workers do not refresh
    ``task.updated_at`` mid-run, so this grace window must comfortably exceed
    the longest plausible report run or a slow-but-alive legacy worker would
    be seized after the grace expires. Only a stale ``updated_at`` (the worker
    is wedged/dead) becomes eligible for takeover after the grace window.
    New-code claims overwrite ``lease_expires_at`` on first contact, so this
    fallback only governs the deploy migration window.
    """
    if task.lease_expires_at is not None:
        return task.lease_expires_at <= now
    last_contact = getattr(task, "updated_at", None)
    if last_contact is None:
        return True
    return (now - last_contact) > timedelta(
        seconds=LEASE_DURATION_SECONDS * LEASE_GRACE_MULTIPLIER
    )


@dataclass(frozen=True)
class TaskExecutionFence:
    """A report-writer guard bound to one durable, renewable task execution owner.

    Owns a renewable lease (``lease_expires_at``) plus a monotonic fencing
    token. ``renew_lease`` refreshes the lease; ``checkpoint`` re-checks both
    ownership and that the lease has not lapsed. A worker crash lets the lease
    expire, after which a new claim can take over by incrementing the fencing
    token — any write the dead worker's stale fence attempts then fails closed.
    """

    manager: "TaskManager"
    task_id: str
    owner: str
    fencing_token: int = 0

    @property
    def cancelled(self) -> bool:
        return False

    def renew_lease(self) -> Task:
        """Refresh the renewable lease (heartbeat). Idempotent for the live owner."""
        return self.manager.renew_lease(self.task_id, self.owner, self.fencing_token)

    def checkpoint(self) -> None:
        task = self.manager.assert_task_execution_owner(self.task_id, self.owner)
        # Lease expired: a newer delivery may take over. Refuse the write.
        if _lease_is_lapsed(task, datetime.now()):
            raise TaskExecutionConflict("task_execution_fence_expired")
        # Strict monotonic enforcement: a higher recorded token means a newer
        # delivery already took the fence.
        if getattr(task, 'fencing_token', 0) > self.fencing_token:
            raise TaskExecutionConflict("task_execution_fence_token_divergence")

    @contextmanager
    def write_guard(self, *, allow_cancelled: bool = False):
        del allow_cancelled
        self.checkpoint()
        yield


class TaskManager:
    """
    Distributed Task Manager
    Thread-safe & cross-process task status management with Redis & Celery integration.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
                    cls._instance._redis_client = None
                    cls._instance._redis_retry_at = 0.0
        return cls._instance

    def _get_redis(self):
        """Return a live Redis client, re-probing periodically after a failure.

        Task state is shared between the web process and the Celery workers, so
        losing Redis is not a cosmetic degradation: without it a task created by
        the web process is invisible to the worker that runs it, and
        ``GET /api/simulation/task/<id>/status`` answers 404 for the rest of the
        process's life. The probe therefore retries on an interval instead of
        latching off after one failed attempt.
        """
        if self._redis_client is not None:
            return self._redis_client

        now = time.monotonic()
        if now < self._redis_retry_at:
            return None

        import os
        redis_url = (
            os.environ.get('REDIS_URL')
            or getattr(Config, 'REDIS_URL', '')
            or getattr(Config, 'CELERY_BROKER_URL', '')
        )
        if not redis_url or redis_url.startswith('memory://'):
            # Deliberately unconfigured (local dev / tests): in-memory is the
            # intended mode, so do not warn and do not re-probe on a hot path.
            self._redis_retry_at = now + REDIS_RETRY_INTERVAL_SECONDS
            return None

        try:
            import redis
            client = redis.from_url(
                redis_url,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
                decode_responses=True,
            )
            client.ping()
        except Exception as exc:
            # Configured but unreachable is an operational fault, not a debug
            # detail — cross-process task state is silently unavailable.
            logger.warning(
                "Redis configured but unreachable; task state is process-local "
                "until it recovers (retrying in %.0fs): %s",
                REDIS_RETRY_INTERVAL_SECONDS,
                exc,
            )
            self._redis_client = None
            self._redis_retry_at = now + REDIS_RETRY_INTERVAL_SECONDS
            return None

        self._redis_client = client
        self._redis_retry_at = 0.0
        return client

    @staticmethod
    def _durable_redis_required() -> bool:
        """Return whether this process was explicitly configured for Redis.

        Local development may use the legacy in-process task view. A deployed
        process that was given a Redis transport must never silently fall back
        to that view after a dependency failure.
        """
        return any(
            isinstance(value, str)
            and value.strip().lower().startswith(("redis://", "rediss://"))
            for value in (
                os.environ.get("REDIS_URL"),
                os.environ.get("CELERY_BROKER_URL"),
                os.environ.get("CELERY_RESULT_BACKEND"),
            )
        )

    def _drop_redis(self, exc: Exception) -> None:
        """Discard a client that failed mid-operation so the next call re-probes."""
        logger.warning("Redis operation failed; falling back to process-local state: %s", exc)
        self._redis_client = None
        self._redis_retry_at = time.monotonic() + REDIS_RETRY_INTERVAL_SECONDS

    @staticmethod
    def _index_score(task: Task) -> float:
        """Creation time as an epoch score for the task index."""
        created = task.created_at
        if isinstance(created, datetime):
            return created.timestamp()
        return time.time()

    def _save_to_redis(self, task: Task) -> bool:
        """Write the task record and index it, in one round trip."""
        r = self._get_redis()
        if r is None:
            return False
        try:
            pipe = r.pipeline()
            pipe.set(f"task:{task.task_id}", json.dumps(task.to_dict()), ex=TASK_TTL_SECONDS)
            pipe.zadd(TASK_INDEX_KEY, {task.task_id: self._index_score(task)})
            pipe.execute()
            return True
        except Exception as e:
            self._drop_redis(e)
            return False

    def _load_from_redis(self, task_id: str) -> Optional[Task]:
        """Load task from Redis."""
        r = self._get_redis()
        if r is None:
            return None
        try:
            val = r.get(f"task:{task_id}")
            if val:
                return Task.from_dict(json.loads(val))
        except Exception as e:
            self._drop_redis(e)
        return None

    @staticmethod
    def _idempotency_reservation_key(idempotency_key: str) -> str:
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        return f"{_IDEMPOTENCY_RESERVATION_PREFIX}{digest}"

    @staticmethod
    def _idempotency_fingerprint(
        task_type: str,
        identity: Dict[str, Any],
    ) -> str:
        """Hash the semantic request identity, excluding generated task ids."""
        try:
            canonical = json.dumps(
                {"task_type": task_type, "identity": identity},
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError):
            raise ValueError("idempotency_identity_invalid") from None
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_idempotency_reservation(raw: str) -> Dict[str, str]:
        try:
            reservation = json.loads(raw)
        except (TypeError, ValueError):
            raise TaskStateUnavailable("task_idempotency_state_invalid") from None
        if (
            not isinstance(reservation, dict)
            or reservation.get("version") != _IDEMPOTENCY_RESERVATION_VERSION
            or not isinstance(reservation.get("task_id"), str)
            or not reservation["task_id"]
            or not isinstance(reservation.get("fingerprint"), str)
            or len(reservation["fingerprint"]) != 64
        ):
            raise TaskStateUnavailable("task_idempotency_state_invalid")
        return reservation

    def _validate_reservation_for_task(
        self,
        reader,
        task: Task,
    ) -> tuple[str, str] | None:
        """Return the live reservation key/value or fail on any divergence."""
        if task.idempotency_key is None:
            return None
        if not task.idempotency_fingerprint:
            raise TaskStateUnavailable("task_idempotency_state_invalid")
        reservation_key = self._idempotency_reservation_key(task.idempotency_key)
        raw_reservation = reader.get(reservation_key)
        if not raw_reservation:
            raise TaskStateUnavailable("task_idempotency_state_invalid")
        reservation = self._parse_idempotency_reservation(raw_reservation)
        if (
            reservation["task_id"] != task.task_id
            or reservation["fingerprint"] != task.idempotency_fingerprint
        ):
            raise TaskStateUnavailable("task_idempotency_state_invalid")
        return reservation_key, raw_reservation

    def _create_idempotent_in_redis(
        self,
        client,
        task: Task,
    ) -> tuple[Task, bool]:
        """Atomically reserve an idempotency identity and create its task.

        The reservation and task record share one MULTI/EXEC. A missing task
        behind a valid, matching reservation is recoverable (for example when
        the record expired at the TTL boundary); malformed or mismatched state
        fails closed.
        """
        if not task.idempotency_key or not task.idempotency_fingerprint:
            raise ValueError("idempotency_identity_invalid")

        reservation_key = self._idempotency_reservation_key(task.idempotency_key)
        candidate_key = f"task:{task.task_id}"
        reservation_json = json.dumps(
            {
                "version": _IDEMPOTENCY_RESERVATION_VERSION,
                "task_id": task.task_id,
                "fingerprint": task.idempotency_fingerprint,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

        try:
            for _ in range(_MAX_UPDATE_ATTEMPTS):
                with client.pipeline() as pipe:
                    try:
                        pipe.watch(reservation_key)
                        raw_reservation = pipe.get(reservation_key)
                        existing_task = None
                        if raw_reservation:
                            reservation = self._parse_idempotency_reservation(
                                raw_reservation
                            )
                            if (
                                reservation["fingerprint"]
                                != task.idempotency_fingerprint
                            ):
                                raise TaskIdempotencyConflict()

                            existing_key = f"task:{reservation['task_id']}"
                            pipe.watch(existing_key, candidate_key)
                            raw_existing = pipe.get(existing_key)
                            if raw_existing:
                                try:
                                    existing_task = Task.from_dict(
                                        json.loads(raw_existing)
                                    )
                                except (TypeError, ValueError, KeyError):
                                    raise TaskStateUnavailable(
                                        "task_idempotency_state_invalid"
                                    ) from None
                                if (
                                    existing_task.idempotency_key
                                    != task.idempotency_key
                                    or existing_task.idempotency_fingerprint
                                    != task.idempotency_fingerprint
                                ):
                                    raise TaskStateUnavailable(
                                        "task_idempotency_state_invalid"
                                    )
                                if existing_task.status in (
                                    TaskStatus.PENDING,
                                    TaskStatus.PROCESSING,
                                ):
                                    return existing_task, False
                        else:
                            pipe.watch(candidate_key)

                        # A terminal/missing prior task permits a same-payload
                        # rerun, but never by overwriting an existing candidate.
                        raw_candidate = pipe.get(candidate_key)
                        if raw_candidate:
                            if (
                                existing_task is None
                                or existing_task.task_id != task.task_id
                            ):
                                raise TaskStateUnavailable("task_id_conflict")
                            # Reusing a terminal task id would destroy history.
                            raise TaskStateUnavailable("task_id_conflict")

                        pipe.multi()
                        pipe.set(
                            candidate_key,
                            json.dumps(task.to_dict()),
                            ex=TASK_TTL_SECONDS,
                        )
                        pipe.set(
                            reservation_key,
                            reservation_json,
                            ex=TASK_TTL_SECONDS,
                        )
                        pipe.zadd(
                            TASK_INDEX_KEY,
                            {task.task_id: self._index_score(task)},
                        )
                        pipe.execute()
                        return task, True
                    except WatchError:
                        continue
            raise TaskStateContentionError()
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None

    def create_task(
        self,
        task_type: str,
        metadata: Optional[Dict] = None,
        task_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        idempotency_identity: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create and retain a task.

        If ``idempotency_key`` is supplied, Redis is mandatory. The key's
        semantic identity and task record are reserved in one transaction. A
        matching in-flight request returns the reserved id; a different
        identity conflicts. A matching terminal or expired task permits a new
        task id, so an explicit rerun never overwrites the prior record.
        """
        task_id = task_id or str(uuid.uuid4())
        durable_redis_required = self._durable_redis_required()
        if (
            not idempotency_key
            and durable_redis_required
            and self._get_redis() is None
        ):
            raise TaskStateUnavailable()
        now = datetime.now()
        task_metadata = metadata or {}
        idempotency_fingerprint = None
        if idempotency_key:
            identity = (
                idempotency_identity
                if idempotency_identity is not None
                else task_metadata
            )
            if not isinstance(identity, dict):
                raise ValueError("idempotency_identity_invalid")
            idempotency_fingerprint = self._idempotency_fingerprint(
                task_type,
                identity,
            )

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=task_metadata,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
        )

        if idempotency_key:
            redis_client = self._get_redis()
            if redis_client is None:
                # Process-local dedupe is not an idempotency guarantee: two web
                # or worker processes would each admit a different task.
                raise TaskStateUnavailable()
            durable_task, created = self._create_idempotent_in_redis(
                redis_client,
                task,
            )
            with self._task_lock:
                self._tasks[durable_task.task_id] = durable_task
            if not created:
                return durable_task.task_id
            task = durable_task

        with self._task_lock:
            self._tasks[task_id] = task
        if not idempotency_key:
            persisted = self._save_to_redis(task)
            if durable_redis_required and not persisted:
                with self._task_lock:
                    self._tasks.pop(task_id, None)
                raise TaskStateUnavailable()

        _audit(
            action="task.created",
            entity_type="task",
            entity_id=task_id,
            after={"task_type": task_type, "status": TaskStatus.PENDING.value},
        )
        return task_id

    def find_in_flight_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[str]:
        """Return the task_id of an in-flight (PENDING/PROCESSING) task carrying
        ``idempotency_key``, or None.

        Used by route handlers to decide whether a submission is a duplicate
        of one already running, so they can skip enqueueing a second worker
        job (ADR-0003 idempotency keys). The lookup follows the same durable
        Redis reservation used by ``create_task``; it never scans a local dict.
        """
        if not idempotency_key:
            return None
        redis_client = self._get_redis()
        if redis_client is None:
            raise TaskStateUnavailable()
        try:
            raw_reservation = redis_client.get(
                self._idempotency_reservation_key(idempotency_key)
            )
            if not raw_reservation:
                return None
            reservation = self._parse_idempotency_reservation(raw_reservation)
            raw_task = redis_client.get(f"task:{reservation['task_id']}")
            if not raw_task:
                return None
            task = Task.from_dict(json.loads(raw_task))
            if (
                task.idempotency_key != idempotency_key
                or task.idempotency_fingerprint != reservation["fingerprint"]
            ):
                raise TaskStateUnavailable("task_idempotency_state_invalid")
            if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                with self._task_lock:
                    self._tasks[task.task_id] = task
                return task.task_id
            return None
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None

    @staticmethod
    def _validate_execution_identity(
        task: Task,
        *,
        expected_task_type: Optional[str],
        expected_idempotency_key: Optional[str],
        expected_metadata: Optional[Dict[str, Any]],
    ) -> None:
        if expected_task_type is not None and task.task_type != expected_task_type:
            raise TaskExecutionConflict("task_execution_identity_mismatch")
        if (
            expected_idempotency_key is not None
            and task.idempotency_key != expected_idempotency_key
        ):
            raise TaskExecutionConflict("task_execution_identity_mismatch")
        if expected_metadata is not None:
            if not isinstance(task.metadata, dict) or any(
                task.metadata.get(key) != value
                for key, value in expected_metadata.items()
            ):
                raise TaskExecutionConflict("task_execution_identity_mismatch")

    def claim_task_execution(
        self,
        task_id: str,
        owner: str,
        *,
        expected_task_type: Optional[str] = None,
        expected_idempotency_key: Optional[str] = None,
        expected_metadata: Optional[Dict[str, Any]] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Task:
        """Atomically claim one task delivery for a single worker owner.

        A second owner never proceeds while the task is PROCESSING and its
        renewable lease is live. The claim is durable and re-checked by
        ``TaskExecutionFence`` around report checkpoints and writes. Once a
        worker's lease lapses (crash/heartbeat gap), this method takes over:
        the new owner re-claims, increments the fencing token, and refreshes
        the lease. The dead worker's stale fence then fails closed on every
        write, so a paused worker cannot resume and write concurrently.
        """
        if not isinstance(owner, str) or not owner:
            raise ValueError("task_execution_owner_invalid")
        redis_client = self._get_redis()
        if redis_client is None:
            raise TaskStateUnavailable()

        key = f"task:{task_id}"
        try:
            for _ in range(_MAX_UPDATE_ATTEMPTS):
                with redis_client.pipeline() as pipe:
                    try:
                        pipe.watch(key)
                        raw = pipe.get(key)
                        if not raw:
                            raise TaskExecutionConflict("task_execution_not_found")
                        try:
                            task = Task.from_dict(json.loads(raw))
                        except (TypeError, ValueError, KeyError):
                            raise TaskStateUnavailable(
                                "task_state_invalid"
                            ) from None
                        reservation_state = None
                        if task.idempotency_key is not None:
                            reservation_key = self._idempotency_reservation_key(
                                task.idempotency_key
                            )
                            pipe.watch(reservation_key)
                            reservation_state = self._validate_reservation_for_task(
                                pipe,
                                task,
                            )
                        self._validate_execution_identity(
                            task,
                            expected_task_type=expected_task_type,
                            expected_idempotency_key=expected_idempotency_key,
                            expected_metadata=expected_metadata,
                        )

                        now = datetime.now()
                        if task.status is TaskStatus.COMPLETED:
                            return task
                        if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                            raise TaskExecutionConflict("task_execution_terminal")
                        takeover_prev_owner = None
                        if task.status is TaskStatus.PROCESSING:
                            lapsed = _lease_is_lapsed(task, now)
                            if task.execution_owner == owner and not lapsed:
                                return task
                            if not lapsed:
                                raise TaskExecutionConflict("task_execution_in_progress")
                            # Lease lapsed: a crashed/wedged worker's claim
                            # expired. Fall through to the write block, which
                            # re-claims for this owner and increments the fencing
                            # token (takeover). Record the displaced owner so the
                            # operator can see a worker lost its lease mid-run.
                            takeover_prev_owner = task.execution_owner

                        task.status = TaskStatus.PROCESSING
                        task.execution_owner = owner
                        task.fencing_token += 1
                        task.lease_expires_at = now + timedelta(seconds=LEASE_DURATION_SECONDS)
                        if progress is not None:
                            task.progress = progress
                        if message is not None:
                            task.message = message
                        task.updated_at = now
                        if takeover_prev_owner is not None:
                            logger.warning(
                                "task_execution_takeover: task %s lease lapsed;"
                                " owner %r (token %d) -> %r (token %d)",
                                task_id,
                                takeover_prev_owner,
                                task.fencing_token - 1,
                                owner,
                                task.fencing_token,
                            )
                        pipe.multi()
                        pipe.set(
                            key,
                            json.dumps(task.to_dict()),
                            ex=TASK_TTL_SECONDS,
                        )
                        if reservation_state is not None:
                            reservation_key, raw_reservation = reservation_state
                            pipe.set(
                                reservation_key,
                                raw_reservation,
                                ex=TASK_TTL_SECONDS,
                            )
                        pipe.zadd(
                            TASK_INDEX_KEY,
                            {task.task_id: self._index_score(task)},
                        )
                        pipe.execute()
                        with self._task_lock:
                            self._tasks[task.task_id] = task
                        return task
                    except WatchError:
                        continue
            raise TaskStateContentionError()
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None

    def assert_task_execution_owner(self, task_id: str, owner: str) -> Task:
        """Fail unless Redis still records this live owner as the writer."""
        redis_client = self._get_redis()
        if redis_client is None:
            raise TaskStateUnavailable()
        try:
            raw = redis_client.get(f"task:{task_id}")
            if not raw:
                raise TaskExecutionConflict("task_execution_not_found")
            task = Task.from_dict(json.loads(raw))
            self._validate_reservation_for_task(redis_client, task)
            if (
                task.status is not TaskStatus.PROCESSING
                or task.execution_owner != owner
            ):
                raise TaskExecutionConflict("task_execution_fence_lost")
            return task
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None

    def renew_lease(
        self,
        task_id: str,
        owner: str,
        fencing_token: int,
    ) -> Task:
        """Refresh the renewable execution lease for one owner.

        Atomically (WATCH/MULTI) re-asserts the owner holds the recorded
        ``fencing_token`` and a live PROCESSING status, then extends
        ``lease_expires_at``. A stale fence whose token was superseded by a
        takeover raises ``TaskExecutionConflict``; a lapsed lease is renewed,
        not rejected.
        """
        redis_client = self._get_redis()
        if redis_client is None:
            raise TaskStateUnavailable()
        key = f"task:{task_id}"
        try:
            for _ in range(_MAX_UPDATE_ATTEMPTS):
                with redis_client.pipeline() as pipe:
                    try:
                        pipe.watch(key)
                        raw = pipe.get(key)
                        if not raw:
                            raise TaskExecutionConflict("task_execution_not_found")
                        task = Task.from_dict(json.loads(raw))
                        reservation_state = None
                        if task.idempotency_key is not None:
                            reservation_key = self._idempotency_reservation_key(
                                task.idempotency_key
                            )
                            pipe.watch(reservation_key)
                            reservation_state = self._validate_reservation_for_task(
                                pipe, task
                            )
                        if (
                            task.status is not TaskStatus.PROCESSING
                            or task.execution_owner != owner
                        ):
                            raise TaskExecutionConflict("task_execution_fence_lost")
                        if getattr(task, "fencing_token", 0) != fencing_token:
                            raise TaskExecutionConflict(
                                "task_execution_fence_token_divergence"
                            )
                        task.lease_expires_at = datetime.now() + timedelta(
                            seconds=LEASE_DURATION_SECONDS
                        )
                        task.updated_at = task.lease_expires_at
                        pipe.multi()
                        pipe.set(
                            key,
                            json.dumps(task.to_dict()),
                            ex=TASK_TTL_SECONDS,
                        )
                        if reservation_state is not None:
                            reservation_key, raw_reservation = reservation_state
                            pipe.set(
                                reservation_key,
                                raw_reservation,
                                ex=TASK_TTL_SECONDS,
                            )
                        # A heartbeat changes only lease_expires_at/updated_at.
                        # The task is already in TASK_INDEX_KEY (added on
                        # create/claim) and _index_score == created_at timestamp
                        # is immutable under a renewal, so re-running the ZADD
                        # is a no-op write that contends on the shared index key;
                        # omit it.
                        pipe.execute()
                        with self._task_lock:
                            self._tasks[task.task_id] = task
                        return task
                    except WatchError:
                        continue
            raise TaskStateContentionError()
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None

    def execution_fence(self, task_id: str, owner: str) -> TaskExecutionFence:
        token = 0
        task = self._load_from_redis(task_id)
        if task is not None:
            token = getattr(task, 'fencing_token', 0)
        return TaskExecutionFence(self, task_id, owner, fencing_token=token)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task from Redis, memory, or Celery backend."""
        # 1. Redis check
        redis_task = self._load_from_redis(task_id)
        if redis_task:
            with self._task_lock:
                self._tasks[task_id] = redis_task
            return redis_task

        # 2. In-memory check
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                return task

        # 3. Celery backend check fallback
        try:
            from ..celery_app import celery_app
            res = celery_app.AsyncResult(task_id)
            if res and res.state and (res.state != 'PENDING' or res.info is not None):
                state_map = {
                    "PENDING": TaskStatus.PENDING,
                    "STARTED": TaskStatus.PROCESSING,
                    "PROGRESS": TaskStatus.PROCESSING,
                    "SUCCESS": TaskStatus.COMPLETED,
                    "FAILURE": TaskStatus.FAILED,
                    "REVOKED": TaskStatus.CANCELLED,
                }
                status = state_map.get(res.state, TaskStatus.PROCESSING)
                meta = res.info if isinstance(res.info, dict) else {}
                now = datetime.now()
                c_task = Task(
                    task_id=task_id,
                    task_type="celery_task",
                    status=status,
                    created_at=now,
                    updated_at=now,
                    progress=meta.get("progress", 100 if status == TaskStatus.COMPLETED else 0),
                    message=meta.get("message", f"Task status: {res.state}"),
                    result=res.result if status == TaskStatus.COMPLETED and isinstance(res.result, dict) else None,
                    error=str(res.result) if status == TaskStatus.FAILED else None,
                    progress_detail=meta.get("detail", {}),
                )
                with self._task_lock:
                    self._tasks[task_id] = c_task
                return c_task
        except Exception:
            pass

        return None
    
    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        public_error: Optional[str] = None,
        progress_detail: Optional[Dict] = None,
        expected_execution_owner: Optional[str] = None,
    ):
        """Apply a partial update to a task, atomically with respect to Redis.

        Every field is optional and only supplied fields are written, so two
        writers touching different fields of the same task both survive. The
        previous implementation read the whole record, mutated it, and wrote it
        back whole; with the web process and two worker processes all writing,
        the slower writer's snapshot silently reverted the faster one's fields —
        including reverting a COMPLETED task to PROCESSING, which strands the
        client polling it.
        """
        changes = {
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "error": error,
            "public_error": public_error,
            "progress_detail": progress_detail,
        }
        changes = {k: v for k, v in changes.items() if v is not None}

        r = self._get_redis()
        if r is not None:
            task = self._update_in_redis(
                r,
                task_id,
                changes,
                expected_execution_owner=expected_execution_owner,
            )
            with self._task_lock:
                self._tasks[task_id] = task
            return

        if self._durable_redis_required():
            raise TaskStateUnavailable()

        # No Redis (or it just dropped): process-local update. Correct for the
        # single-process dev/test runtime; across processes the caller has
        # already been warned by _get_redis / _drop_redis.
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                if expected_execution_owner is not None:
                    raise TaskExecutionConflict("task_execution_not_found")
                task = self._new_placeholder(task_id, changes)
            else:
                if task.idempotency_key is not None:
                    raise TaskStateUnavailable()
                if (
                    expected_execution_owner is not None
                    and task.execution_owner != expected_execution_owner
                ):
                    raise TaskExecutionConflict("task_execution_fence_lost")
                self._apply(task, changes)
            self._tasks[task_id] = task
        self._save_to_redis(task)

    def _status_of(self, task_id: str) -> Optional[TaskStatus]:
        """Best-effort read of a task's current status for audit diffing.
        Returns None if the task isn't in this process's view."""
        # Try the process-local dict first (fast path), then Redis.
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is not None:
                return task.status
        loaded = self._load_from_redis(task_id)
        return loaded.status if loaded is not None else None

    @staticmethod
    def _apply(task: Task, changes: Dict[str, Any]) -> None:
        """Write supplied fields without changing an established terminal envelope."""
        if task.status in _TERMINAL_STATUSES:
            # A late delivery must not downgrade, cancel, or partially rewrite
            # an already terminal record. Ignore the whole transition so its
            # coupled progress/message/result/error fields remain consistent.
            return

        for name, value in changes.items():
            setattr(task, name, value)
        task.updated_at = datetime.now()

    @staticmethod
    def _new_placeholder(task_id: str, changes: Dict[str, Any]) -> Task:
        """Build a task for an id that has no record yet.

        A worker can legitimately report progress for a task whose record has
        already expired, so an update for an unknown id creates rather than
        drops it.
        """
        now = datetime.now()
        task = Task(
            task_id=task_id,
            task_type="unknown",
            status=changes.get("status", TaskStatus.PROCESSING),
            created_at=now,
            updated_at=now,
        )
        for name, value in changes.items():
            setattr(task, name, value)
        return task

    def _update_in_redis(
        self,
        client,
        task_id: str,
        changes: Dict[str, Any],
        *,
        expected_execution_owner: Optional[str] = None,
    ) -> Task:
        """Read-modify-write the record under WATCH or fail closed.

        WATCH/MULTI/EXEC turns the sequence into an optimistic transaction: if
        another process writes the key between the read and the exec, EXEC fails
        and the whole thing is retried against the newer value.
        """
        key = f"task:{task_id}"
        try:
            for _ in range(_MAX_UPDATE_ATTEMPTS):
                with client.pipeline() as pipe:
                    try:
                        pipe.watch(key)
                        raw = pipe.get(key)
                        reservation_state = None
                        if raw:
                            task = Task.from_dict(json.loads(raw))
                            if task.idempotency_key is not None:
                                reservation_key = self._idempotency_reservation_key(
                                    task.idempotency_key
                                )
                                pipe.watch(reservation_key)
                                reservation_state = (
                                    self._validate_reservation_for_task(pipe, task)
                                )
                            if (
                                expected_execution_owner is not None
                                and task.execution_owner
                                != expected_execution_owner
                            ):
                                raise TaskExecutionConflict(
                                    "task_execution_fence_lost"
                                )
                            self._apply(task, changes)
                        else:
                            if expected_execution_owner is not None:
                                raise TaskExecutionConflict(
                                    "task_execution_not_found"
                                )
                            task = self._new_placeholder(task_id, changes)

                        pipe.multi()
                        pipe.set(key, json.dumps(task.to_dict()), ex=TASK_TTL_SECONDS)
                        if reservation_state is not None:
                            reservation_key, raw_reservation = reservation_state
                            pipe.set(
                                reservation_key,
                                raw_reservation,
                                ex=TASK_TTL_SECONDS,
                            )
                        pipe.zadd(TASK_INDEX_KEY, {task_id: self._index_score(task)})
                        pipe.execute()
                        return task
                    except WatchError:
                        continue

            logger.warning(
                "Task %s update contended past %d attempts; refusing an "
                "unconditional fallback write",
                task_id,
                _MAX_UPDATE_ATTEMPTS,
            )
            raise TaskStateContentionError()
        except TaskStateError:
            raise
        except Exception as exc:
            self._drop_redis(exc)
            raise TaskStateUnavailable() from None
    
    def complete_task(
        self,
        task_id: str,
        result: Dict,
        *,
        execution_owner: Optional[str] = None,
    ):
        """Mark task as complete"""
        prior = self._status_of(task_id)
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result,
            expected_execution_owner=execution_owner,
        )
        # Only audit a real transition. If prior is None the task never
        # existed (update_task created a placeholder); auditing it would
        # fabricate a transition event for a phantom entity.
        current = self._status_of(task_id)
        if (
            prior is not None
            and prior != TaskStatus.COMPLETED
            and current is TaskStatus.COMPLETED
        ):
            _audit(
                action="task.completed",
                entity_type="task",
                entity_id=task_id,
                before={"status": prior.value},
                after={"status": TaskStatus.COMPLETED.value},
            )

    def fail_task(
        self,
        task_id: str,
        error: str,
        *,
        public_error: str = "task_failed",
        execution_owner: Optional[str] = None,
    ):
        """Mark task as failed"""
        prior = self._status_of(task_id)
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error,
            public_error=public_error,
            expected_execution_owner=execution_owner,
        )
        # Only audit a real transition for a task that actually existed
        # (see complete_task above).
        current = self._status_of(task_id)
        if (
            prior is not None
            and prior != TaskStatus.FAILED
            and current is TaskStatus.FAILED
        ):
            _audit(
                action="task.failed",
                entity_type="task",
                entity_id=task_id,
                before={"status": prior.value},
                after={"status": TaskStatus.FAILED.value, "public_error": public_error},
            )

    def cancel_task(
        self,
        task_id: str,
        *,
        result: Optional[Dict] = None,
        progress: Optional[int] = None,
    ) -> None:
        """Record a cooperative stop without mislabeling it as completion."""
        prior = self._status_of(task_id)
        self.update_task(
            task_id,
            status=TaskStatus.CANCELLED,
            progress=progress,
            message="Task cancelled",
            result=result,
        )
        current = self._status_of(task_id)
        if (
            prior is not None
            and prior != TaskStatus.CANCELLED
            and current is TaskStatus.CANCELLED
        ):
            _audit(
                action="task.cancelled",
                entity_type="task",
                entity_id=task_id,
                before={"status": prior.value},
                after={"status": TaskStatus.CANCELLED.value},
            )
    
    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """List tasks from Redis and memory."""
        tasks_map = {}

        # Load from Redis if available
        r = self._get_redis()
        if r:
            try:
                task_ids = r.zrevrange(TASK_INDEX_KEY, 0, -1)
                if task_ids:
                    # One MGET rather than one GET per id: the index can hold a
                    # day of tasks and this runs on an API request path.
                    stale = []
                    for tid, raw in zip(task_ids, r.mget(f"task:{t}" for t in task_ids)):
                        if raw:
                            try:
                                tasks_map[tid] = Task.from_dict(json.loads(raw))
                                continue
                            except (ValueError, KeyError, TypeError) as exc:
                                logger.warning("Discarding unreadable task %s: %s", tid, exc)
                        # The record expired (or is corrupt) but the index still
                        # points at it. Drop the pointer here as well as in
                        # cleanup, so a process that never runs cleanup does not
                        # accumulate dead ids.
                        stale.append(tid)
                    if stale:
                        r.zrem(TASK_INDEX_KEY, *stale)
            except Exception as e:
                self._drop_redis(e)

        # Merge with in-memory tasks
        with self._task_lock:
            for tid, t in self._tasks.items():
                if tid not in tasks_map:
                    tasks_map[tid] = t

        tasks = list(tasks_map.values())
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        return [
            task.to_public_dict()
            for task in sorted(
                tasks,
                key=lambda item: item.created_at,
                reverse=True,
            )
        ]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Retire stale terminal tasks from the in-memory dict and the
        Redis index. Returns the number of in-process tasks retired.

        Runs from a periodic Celery beat task (see ``cleanup_old_tasks_task``
        in app.tasks.simulation_tasks) rather than the former daemon thread.
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._task_lock:
            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in _TERMINAL_STATUSES
            ]
            for tid in old_ids:
                del self._tasks[tid]

        r = self._get_redis()
        if r:
            try:
                # Drop index entries older than the record TTL by score alone.
                # These cannot be loaded any more, so age is the only usable
                # signal — and it is the leak the old code could not close:
                # it only removed ids whose record it could still read, which
                # is exactly the set that had *not* expired.
                r.zremrangebyscore(
                    TASK_INDEX_KEY, "-inf", time.time() - TASK_TTL_SECONDS
                )

                # Then retire finished tasks that are past the caller's cutoff
                # but still within the TTL.
                task_ids = r.zrangebyscore(TASK_INDEX_KEY, "-inf", cutoff.timestamp())
                for tid in task_ids:
                    t = self._load_from_redis(tid)
                    if t is None or (
                        t.created_at < cutoff
                        and t.status in _TERMINAL_STATUSES
                    ):
                        r.delete(f"task:{tid}")
                        r.zrem(TASK_INDEX_KEY, tid)

                # Retire the unbounded pre-index key if a previous release left
                # one behind. Its members are ids only; the records they name
                # are indexed independently above, so nothing is lost.
                r.delete(_LEGACY_TASK_INDEX_KEY)
            except Exception as e:
                self._drop_redis(e)

        return len(old_ids)
