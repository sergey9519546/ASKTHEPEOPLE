"""
Task Status Management
Used to track long-running tasks (like simulation, graph building, report generation)
Distributed task state manager backed by Redis / Celery result backend.
"""

import uuid
import json
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('askthepeople.models.task')


class TaskStatus(str, Enum):
    """Task Status Enum"""
    PENDING = "pending"          # Pending
    PROCESSING = "processing"    # Processing
    COMPLETED = "completed"      # Completed
    FAILED = "failed"            # Failed


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
                    cls._instance._redis_checked = False
        return cls._instance

    def _get_redis(self):
        """Get or initialize Redis client connection if configured."""
        if not self._redis_checked:
            import os
            redis_url = os.environ.get('REDIS_URL') or getattr(Config, 'REDIS_URL', '') or getattr(Config, 'CELERY_BROKER_URL', '')
            if redis_url and not redis_url.startswith('memory://'):
                try:
                    import redis
                    r = redis.from_url(redis_url, socket_timeout=1.0, socket_connect_timeout=1.0, decode_responses=True)
                    r.ping()
                    self._redis_client = r
                except Exception as e:
                    logger.debug(f"Redis not available for TaskManager: {e}")
                    self._redis_client = None
            self._redis_checked = True
        return self._redis_client

    def _save_to_redis(self, task: Task):
        """Save task to Redis."""
        r = self._get_redis()
        if r is None:
            return
        try:
            key = f"task:{task.task_id}"
            r.set(key, json.dumps(task.to_dict()), ex=86400)
            r.sadd("tasks:all", task.task_id)
        except Exception as e:
            logger.debug(f"Failed to save task {task.task_id} to Redis: {e}")

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
            logger.debug(f"Failed to load task {task_id} from Redis: {e}")
        return None

    def create_task(
        self,
        task_type: str,
        metadata: Optional[Dict] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """Create and retain a task."""
        task_id = task_id or str(uuid.uuid4())
        now = datetime.now()
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )
        
        with self._task_lock:
            self._tasks[task_id] = task
        self._save_to_redis(task)
        
        return task_id
    
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
            if res and res.state:
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
        """Update task status in memory and Redis."""
        task = self.get_task(task_id)
        if task:
            with self._task_lock:
                task.updated_at = datetime.now()
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if message is not None:
                    task.message = message
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
                if public_error is not None:
                    task.public_error = public_error
                if progress_detail is not None:
                    task.progress_detail = progress_detail
                self._tasks[task_id] = task
            self._save_to_redis(task)
        else:
            # If task doesn't exist yet, create it with given updates
            now = datetime.now()
            task = Task(
                task_id=task_id,
                task_type="unknown",
                status=status or TaskStatus.PROCESSING,
                created_at=now,
                updated_at=now,
                progress=progress or 0,
                message=message or "",
                result=result,
                error=error,
                public_error=public_error,
                progress_detail=progress_detail or {},
            )
            with self._task_lock:
                self._tasks[task_id] = task
            self._save_to_redis(task)
    
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
                task_ids = r.smembers("tasks:all")
                for tid in task_ids:
                    t = self._load_from_redis(tid)
                    if t:
                        tasks_map[tid] = t
            except Exception as e:
                logger.debug(f"Failed to list tasks from Redis: {e}")

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
        """Clean up old tasks"""
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
                task_ids = r.smembers("tasks:all")
                for tid in task_ids:
                    t = self._load_from_redis(tid)
                    if t and t.created_at < cutoff and t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        r.delete(f"task:{tid}")
                        r.srem("tasks:all", tid)
            except Exception as e:
                logger.debug(f"Failed to cleanup old tasks in Redis: {e}")
