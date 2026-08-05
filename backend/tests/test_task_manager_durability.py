"""Cross-process durability behaviour of `TaskManager`.

Task state is written by the web process and by every Celery worker, so the
properties under test here are about what happens when more than one writer, or
an unhealthy Redis, is involved. All tests drive a fake client rather than a
live server: what matters is the command sequence the manager emits, and a real
Redis would make the contention cases timing-dependent.
"""

import json
import time

import pytest

from app.models.task import (
    _LEGACY_TASK_INDEX_KEY,
    REDIS_RETRY_INTERVAL_SECONDS,
    TASK_INDEX_KEY,
    TASK_TTL_SECONDS,
    Task,
    TaskManager,
    TaskStatus,
)

# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

class FakePipeline:
    """Enough of redis-py's pipeline for the paths TaskManager uses."""

    def __init__(self, store):
        self._store = store
        self._queued = []
        self._watching = None
        self._watch_version = None

    # -- context manager -------------------------------------------------- #
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    # -- immediate mode --------------------------------------------------- #
    def watch(self, key):
        self._watching = key
        self._watch_version = self._store.versions.get(key, 0)

    def get(self, key):
        if self._watching is not None:
            return self._store.get(key)
        self._queued.append(("get", (key,)))
        return self

    def multi(self):
        self._queued = []

    # -- queued mode ------------------------------------------------------ #
    def set(self, key, value, ex=None):
        self._queued.append(("set", (key, value, ex)))
        return self

    def zadd(self, key, mapping):
        self._queued.append(("zadd", (key, mapping)))
        return self

    def execute(self):
        from redis.exceptions import WatchError

        if self._watching is not None:
            current = self._store.versions.get(self._watching, 0)
            if current != self._watch_version:
                raise WatchError("key changed under WATCH")
        for name, args in self._queued:
            getattr(self._store, name)(*args)
        self._queued = []
        return []


class FakeRedis:
    """In-process stand-in with the subset of commands TaskManager issues."""

    def __init__(self):
        self.data = {}
        self.zsets = {}
        self.versions = {}
        self.ping_calls = 0

    def ping(self):
        self.ping_calls += 1
        return True

    def pipeline(self):
        return FakePipeline(self)

    def get(self, key):
        return self.data.get(key)

    def mget(self, keys):
        return [self.data.get(k) for k in keys]

    def set(self, key, value, ex=None):
        self.data[key] = value
        self.versions[key] = self.versions.get(key, 0) + 1

    def delete(self, key):
        self.data.pop(key, None)
        self.zsets.pop(key, None)
        self.versions[key] = self.versions.get(key, 0) + 1

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)

    def zrem(self, key, *members):
        z = self.zsets.get(key, {})
        for m in members:
            z.pop(m, None)

    def zrevrange(self, key, start, end):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1], reverse=True)
        ids = [k for k, _ in items]
        return ids[start:] if end == -1 else ids[start:end + 1]

    def zrangebyscore(self, key, lo, hi):
        lo = float("-inf") if lo == "-inf" else float(lo)
        hi = float("inf") if hi == "+inf" else float(hi)
        return [k for k, s in sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1])
                if lo <= s <= hi]

    def zremrangebyscore(self, key, lo, hi):
        for member in self.zrangebyscore(key, lo, hi):
            self.zsets[key].pop(member, None)


@pytest.fixture
def manager(monkeypatch):
    """A TaskManager with clean singleton state and no Redis."""
    tm = TaskManager()
    monkeypatch.setattr(tm, "_tasks", {}, raising=False)
    monkeypatch.setattr(tm, "_redis_client", None, raising=False)
    monkeypatch.setattr(tm, "_redis_retry_at", 0.0, raising=False)
    return tm


@pytest.fixture
def redis_manager(manager, monkeypatch):
    """A TaskManager wired to a FakeRedis."""
    fake = FakeRedis()
    monkeypatch.setattr(manager, "_redis_client", fake, raising=False)
    return manager, fake


# --------------------------------------------------------------------------- #
# Redis probe must recover, not latch off
# --------------------------------------------------------------------------- #

def test_redis_probe_retries_after_a_failed_connection(manager, monkeypatch):
    """A transient failure must not disable cross-process state permanently.

    The one-shot probe this replaces meant a single blip left the process
    in-memory only for its whole lifetime, so every async status poll 404'd
    until restart.
    """
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    attempts = []
    healthy = FakeRedis()

    class _Broken:
        def ping(self):
            raise ConnectionError("down")

    def _from_url(*a, **k):
        attempts.append(1)
        return _Broken() if len(attempts) == 1 else healthy

    import redis
    monkeypatch.setattr(redis, "from_url", _from_url)

    assert manager._get_redis() is None
    assert len(attempts) == 1

    # Inside the backoff window: no new attempt.
    assert manager._get_redis() is None
    assert len(attempts) == 1

    # Past it: probe again and recover.
    manager._redis_retry_at = time.monotonic() - 1
    assert manager._get_redis() is healthy
    assert len(attempts) == 2


def test_unconfigured_redis_does_not_warn_or_reconnect(manager, monkeypatch):
    """memory:// and unset are the intended local mode, not a fault."""
    monkeypatch.setenv("REDIS_URL", "memory://")
    assert manager._get_redis() is None
    assert manager._redis_retry_at > time.monotonic()


def test_failed_operation_drops_the_client_for_re_probing(redis_manager):
    manager, fake = redis_manager

    def _boom(*a, **k):
        raise ConnectionError("reset by peer")

    fake.get = _boom
    assert manager._load_from_redis("nope") is None
    assert manager._redis_client is None, "a broken client must be discarded"
    assert manager._redis_retry_at > time.monotonic()


# --------------------------------------------------------------------------- #
# Concurrent writers
# --------------------------------------------------------------------------- #

def test_concurrent_writers_do_not_lose_each_others_fields(redis_manager):
    """Two writers touching different fields must both survive.

    Read-modify-write of the whole record meant the slower writer's snapshot
    reverted the faster writer's field.
    """
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")

    manager.update_task(task_id, progress=40)
    manager.update_task(task_id, message="halfway")

    stored = json.loads(fake.data[f"task:{task_id}"])
    assert stored["progress"] == 40
    assert stored["message"] == "halfway"


def test_watch_conflict_is_retried_against_the_newer_value(redis_manager):
    """A write landing between the read and the exec must not be clobbered."""
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")

    real_get = FakePipeline.get
    state = {"injected": False}

    def _get_with_interleaved_write(self, key):
        value = real_get(self, key)
        if self._watching is not None and not state["injected"]:
            state["injected"] = True
            # Another process commits while this transaction is open.
            other = json.loads(fake.data[key])
            other["message"] = "written by the other process"
            fake.set(key, json.dumps(other))
        return value

    FakePipeline.get = _get_with_interleaved_write
    try:
        manager.update_task(task_id, progress=75)
    finally:
        FakePipeline.get = real_get

    stored = json.loads(fake.data[f"task:{task_id}"])
    assert state["injected"], "the test did not actually create a conflict"
    assert stored["progress"] == 75
    assert stored["message"] == "written by the other process", (
        "the retry must rebase onto the concurrent write, not overwrite it"
    )


def test_completed_task_is_not_reverted_by_a_late_progress_update(redis_manager):
    """A straggler update must not un-finish a task and strand its poller."""
    manager, _fake = redis_manager
    task_id = manager.create_task("simulation_run")

    manager.complete_task(task_id, {"ok": True})
    manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=60)

    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    # Non-status fields from the late update still apply.
    assert task.progress == 60


def test_failed_task_is_not_reverted_either(manager):
    task_id = manager.create_task("simulation_run")
    manager.fail_task(task_id, "boom", public_error="run_failed")
    manager.update_task(task_id, status=TaskStatus.PENDING)
    assert manager.get_task(task_id).status == TaskStatus.FAILED


def test_terminal_to_terminal_transition_is_allowed(manager):
    """COMPLETED -> FAILED is a real outcome change, not a revert."""
    task_id = manager.create_task("simulation_run")
    manager.complete_task(task_id, {"ok": True})
    manager.fail_task(task_id, "post-hoc validation failed")
    assert manager.get_task(task_id).status == TaskStatus.FAILED


# --------------------------------------------------------------------------- #
# Index hygiene
# --------------------------------------------------------------------------- #

def test_records_are_written_with_a_ttl_and_indexed_by_creation_time(redis_manager):
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")

    assert f"task:{task_id}" in fake.data
    assert task_id in fake.zsets[TASK_INDEX_KEY]


def test_index_entries_whose_record_expired_are_pruned(redis_manager):
    """The leak this closes: entries were only removed if still loadable.

    Expired records are exactly the ones that cannot be loaded, so the old
    cleanup could never remove them and the index grew forever.
    """
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")

    # Simulate Redis expiring the record while the index still points at it.
    del fake.data[f"task:{task_id}"]
    fake.zsets[TASK_INDEX_KEY][task_id] = time.time() - (TASK_TTL_SECONDS + 60)

    manager.cleanup_old_tasks(max_age_hours=24)
    assert task_id not in fake.zsets[TASK_INDEX_KEY]


def test_listing_prunes_index_entries_with_no_record(redis_manager):
    """A process that never runs cleanup must not accumulate dead ids either."""
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")
    del fake.data[f"task:{task_id}"]

    manager.list_tasks()
    assert task_id not in fake.zsets[TASK_INDEX_KEY]


def test_listing_uses_one_mget_rather_than_a_get_per_task(redis_manager):
    manager, fake = redis_manager
    for _ in range(5):
        manager.create_task("simulation_run")

    calls = {"mget": 0, "get": 0}
    real_mget, real_get = fake.mget, fake.get
    fake.mget = lambda keys: (calls.__setitem__("mget", calls["mget"] + 1), real_mget(keys))[1]
    fake.get = lambda key: (calls.__setitem__("get", calls["get"] + 1), real_get(key))[1]

    manager.list_tasks()
    assert calls["mget"] == 1
    assert calls["get"] == 0


def test_legacy_unbounded_index_key_is_retired_on_cleanup(redis_manager):
    manager, fake = redis_manager
    fake.data[_LEGACY_TASK_INDEX_KEY] = "leftover"

    manager.cleanup_old_tasks(max_age_hours=24)
    assert _LEGACY_TASK_INDEX_KEY not in fake.data


def test_ttl_constant_matches_the_documented_horizon():
    assert TASK_TTL_SECONDS == 86400
    assert REDIS_RETRY_INTERVAL_SECONDS > 0


# --------------------------------------------------------------------------- #
# In-memory path stays correct
# --------------------------------------------------------------------------- #

def test_update_for_unknown_id_creates_the_task(manager):
    """A worker may report progress for a record that already expired."""
    manager.update_task("orphan-id", progress=10, message="working")
    task = manager.get_task("orphan-id")
    assert task is not None
    assert task.progress == 10


def test_public_dict_still_hides_diagnostic_error_text(manager):
    task_id = manager.create_task("simulation_run")
    manager.fail_task(task_id, "C:\\private\\path.py line 42", public_error="run_failed")
    payload = manager.get_task(task_id).to_public_dict()
    assert payload["error"] == "run_failed"
    assert "private" not in json.dumps(payload)


def test_storage_paths_are_absolute_even_when_configured_relative(monkeypatch):
    """A relative UPLOAD_FOLDER must not leave storage paths cwd-dependent.

    The web process and the Celery worker are separate processes; a relative
    base would also make safe_join's containment check resolve against whatever
    cwd each happened to start in.
    """
    import importlib

    monkeypatch.setenv("UPLOAD_FOLDER", "relative/uploads")
    import app.config as config_module

    reloaded = importlib.reload(config_module)
    try:
        import os

        assert os.path.isabs(reloaded.Config.UPLOAD_FOLDER)
        assert os.path.isabs(reloaded.Config.OASIS_SIMULATION_DATA_DIR)
    finally:
        # Restore the module other tests hold references to.
        monkeypatch.delenv("UPLOAD_FOLDER", raising=False)
        importlib.reload(config_module)


def test_round_trip_through_redis_preserves_fields(redis_manager):
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run", metadata={"simulation_id": "sim_1"})
    manager.update_task(task_id, progress=33, progress_detail={"stage": "profiles"})

    reloaded = Task.from_dict(json.loads(fake.data[f"task:{task_id}"]))
    assert reloaded.metadata == {"simulation_id": "sim_1"}
    assert reloaded.progress_detail == {"stage": "profiles"}
    assert reloaded.progress == 33


def test_cleanup_old_tasks_returns_retired_count():
    """cleanup_old_tasks reports how many finished tasks it retired, so the
    periodic beat job can log a meaningful number (ADR-0003 durable cleanup)."""
    from datetime import datetime, timedelta

    manager = TaskManager()
    manager._tasks.clear()

    # One stale completed task (older than the cutoff) and one fresh one.
    stale = manager.create_task("old")
    manager._tasks[stale].status = TaskStatus.COMPLETED
    manager._tasks[stale].created_at = datetime.now() - timedelta(hours=48)

    fresh = manager.create_task("fresh")
    manager._tasks[fresh].status = TaskStatus.COMPLETED

    removed = manager.cleanup_old_tasks(max_age_hours=24)
    assert removed == 1
    assert stale not in manager._tasks
    assert fresh in manager._tasks


def test_cleanup_old_tasks_beat_schedule_registered():
    """The stale-task cleanup runs as a Celery beat job, not a daemon thread.
    The beat schedule must be registered on the celery app so `celery beat`
    actually fires it (ADR-0003)."""
    from app.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "cleanup-old-stale-tasks" in schedule
    entry = schedule["cleanup-old-stale-tasks"]
    assert entry["task"] == "tasks.cleanup_old_tasks"
    # Hourly cadence matches the former daemon-thread interval.
    assert entry["schedule"] == 3600.0
    assert entry["kwargs"]["max_age_hours"] == 24


def test_idempotency_key_dedupes_in_flight_submissions():
    """A second create_task with the same idempotency_key while the first is
    still in flight returns the first task's id — no duplicate task created
    (ADR-0003)."""
    manager = TaskManager()
    manager._tasks.clear()

    first = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-1",
    )
    # Still in flight (PENDING): second submission with the same key dedupes.
    second = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-1",
    )
    assert second == first
    # Only one task record exists.
    assert len(manager._tasks) == 1

    # find_in_flight_by_idempotency_key surfaces the same id.
    found = manager.find_in_flight_by_idempotency_key("client-key-1")
    assert found == first


def test_idempotency_key_allows_resubmit_after_terminal():
    """A task that reached COMPLETED does not block a fresh submission with
    the same key — the caller is explicitly re-running."""
    manager = TaskManager()
    manager._tasks.clear()

    first = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-2",
    )
    manager._tasks[first].status = TaskStatus.COMPLETED

    second = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-2",
    )
    assert second != first
    assert len(manager._tasks) == 2


def test_find_in_flight_returns_none_for_unknown_or_missing_key():
    manager = TaskManager()
    manager._tasks.clear()
    assert manager.find_in_flight_by_idempotency_key("nope") is None
    assert manager.find_in_flight_by_idempotency_key("") is None
    assert manager.find_in_flight_by_idempotency_key(None) is None


