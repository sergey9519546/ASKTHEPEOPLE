"""
Task Status Management
Used to track long-running tasks (like simulation, graph building, report generation)
Distributed task state manager backed by Redis / Celery result backend.
"""

import uuid
import json
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

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

_TERMINAL_STATUSES = frozenset()  # populated below, after TaskStatus exists


class TaskStatus(str, Enum):
    """Task Status Enum"""
    PENDING = "pending"          # Pending
    PROCESSING = "processing"    # Processing
    COMPLETED = "completed"      # Completed
    FAILED = "failed"            # Failed


# A task that has completed or failed is done. Later writes may still add
# detail, but they must not move it back to pending/processing.
_TERMINAL_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED})


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
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Convert to a client-safe dictionary without diagnostic error text."""
        payload = self.to_dict()
        if self.status == TaskStatus.FAILED:
            payload["error"] = self.public_error or "task_failed"
        else:
            payload["error"] = None
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
        except ValueError:
            status = TaskStatus.PENDING

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
        )


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

    def _save_to_redis(self, task: Task):
        """Write the task record and index it, in one round trip."""
        r = self._get_redis()
        if r is None:
            return
        try:
            pipe = r.pipeline()
            pipe.set(f"task:{task.task_id}", json.dumps(task.to_dict()), ex=TASK_TTL_SECONDS)
            pipe.zadd(TASK_INDEX_KEY, {task.task_id: self._index_score(task)})
            pipe.execute()
        except Exception as e:
            self._drop_redis(e)

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

    def create_task(
        self,
        task_type: str,
        metadata: Optional[Dict] = None,
        task_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Create and retain a task.

        If ``idempotency_key`` is supplied and an in-flight (PENDING or
        PROCESSING) task already exists with the same key, that task's id is
        returned instead of creating a new one. This dedupes double-submits
        (network retry, double-click) per ADR-0003. A task that has reached a
        terminal state (COMPLETED/FAILED) with the same key does NOT block a
        fresh submission — the caller is explicitly re-running.
        """
        # Idempotency dedup: look for a matching in-flight task first.
        if idempotency_key:
            with self._task_lock:
                for existing in self._tasks.values():
                    if (
                        existing.idempotency_key == idempotency_key
                        and existing.status
                        in (TaskStatus.PENDING, TaskStatus.PROCESSING)
                    ):
                        return existing.task_id

        task_id = task_id or str(uuid.uuid4())
        now = datetime.now()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            idempotency_key=idempotency_key,
        )

        with self._task_lock:
            self._tasks[task_id] = task
        self._save_to_redis(task)

        return task_id

    def find_in_flight_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[str]:
        """Return the task_id of an in-flight (PENDING/PROCESSING) task carrying
        ``idempotency_key``, or None.

        Used by route handlers to decide whether a submission is a duplicate
        of one already running, so they can skip enqueueing a second worker
        job (ADR-0003 idempotency keys). Only the process-local dict is
        consulted; cross-process dedup relies on the shared Redis snapshot
        that ``_save_to_redis`` writes, which a sibling worker's TaskManager
        loads on ``get_task``.
        """
        if not idempotency_key:
            return None
        with self._task_lock:
            for task in self._tasks.values():
                if (
                    task.idempotency_key == idempotency_key
                    and task.status
                    in (TaskStatus.PENDING, TaskStatus.PROCESSING)
                ):
                    return task.task_id
        return None
    
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
        progress_detail: Optional[Dict] = None
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
            task = self._update_in_redis(r, task_id, changes)
            if task is not None:
                with self._task_lock:
                    self._tasks[task_id] = task
                return

        # No Redis (or it just dropped): process-local update. Correct for the
        # single-process dev/test runtime; across processes the caller has
        # already been warned by _get_redis / _drop_redis.
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                task = self._new_placeholder(task_id, changes)
            else:
                self._apply(task, changes)
            self._tasks[task_id] = task
        self._save_to_redis(task)

    @staticmethod
    def _apply(task: Task, changes: Dict[str, Any]) -> None:
        """Write supplied fields onto `task`, refusing to un-finish it."""
        new_status = changes.get("status")
        if (
            new_status is not None
            and task.status in _TERMINAL_STATUSES
            and new_status not in _TERMINAL_STATUSES
        ):
            # A late in-flight progress update must not resurrect a finished
            # task. Its other fields still apply.
            changes = {k: v for k, v in changes.items() if k != "status"}

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
        self, client, task_id: str, changes: Dict[str, Any]
    ) -> Optional[Task]:
        """Read-modify-write the record under WATCH; None if Redis is unusable.

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
                        if raw:
                            task = Task.from_dict(json.loads(raw))
                            self._apply(task, changes)
                        else:
                            task = self._new_placeholder(task_id, changes)

                        pipe.multi()
                        pipe.set(key, json.dumps(task.to_dict()), ex=TASK_TTL_SECONDS)
                        pipe.zadd(TASK_INDEX_KEY, {task_id: self._index_score(task)})
                        pipe.execute()
                        return task
                    except WatchError:
                        continue

            logger.warning(
                "Task %s update contended past %d attempts; retrying without "
                "the transaction would risk losing a concurrent write",
                task_id,
                _MAX_UPDATE_ATTEMPTS,
            )
            return None
        except Exception as exc:
            self._drop_redis(exc)
            return None
    
    def complete_task(self, task_id: str, result: Dict):
        """Mark task as complete"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result
        )
    
    def fail_task(
        self,
        task_id: str,
        error: str,
        *,
        public_error: str = "task_failed",
    ):
        """Mark task as failed"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error,
            public_error=public_error,
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
        """Retire stale completed/failed tasks from the in-memory dict and the
        Redis index. Returns the number of in-process tasks retired.

        Runs from a periodic Celery beat task (see ``cleanup_old_tasks_task``
        in app.tasks.simulation_tasks) rather than the former daemon thread.
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._task_lock:
            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
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
                        and t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
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
