"""Cross-process durability behaviour of `TaskManager`.

Task state is written by the web process and by every Celery worker, so the
properties under test here are about what happens when more than one writer, or
an unhealthy Redis, is involved. All tests drive a fake client rather than a
live server: what matters is the command sequence the manager emits, and a real
Redis would make the contention cases timing-dependent.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.models.task import (
    _LEGACY_TASK_INDEX_KEY,
    REDIS_RETRY_INTERVAL_SECONDS,
    TASK_INDEX_KEY,
    TASK_TTL_SECONDS,
    Task,
    TaskManager,
    TaskStateUnavailable,
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
        self._watching = ()
        self._watch_versions = {}

    # -- context manager -------------------------------------------------- #
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    # -- immediate mode --------------------------------------------------- #
    def watch(self, *keys):
        self._watching = tuple(dict.fromkeys((*self._watching, *keys)))
        for key in keys:
            self._watch_versions.setdefault(
                key,
                self._store.versions.get(key, 0),
            )

    def get(self, key):
        if self._watching:
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

        with self._store.lock:
            for key, watched_version in self._watch_versions.items():
                current = self._store.versions.get(key, 0)
                if current != watched_version:
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
        self.lock = threading.RLock()

    def ping(self):
        self.ping_calls += 1
        return True

    def pipeline(self):
        return FakePipeline(self)

    def get(self, key):
        with self.lock:
            return self.data.get(key)

    def mget(self, keys):
        return [self.data.get(k) for k in keys]

    def set(self, key, value, ex=None):
        with self.lock:
            self.data[key] = value
            self.versions[key] = self.versions.get(key, 0) + 1

    def delete(self, key):
        with self.lock:
            self.data.pop(key, None)
            self.zsets.pop(key, None)
            self.versions[key] = self.versions.get(key, 0) + 1

    def zadd(self, key, mapping):
        with self.lock:
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


def _isolated_manager(fake: FakeRedis) -> TaskManager:
    """Build the independent state a second OS process would own."""
    manager = object.__new__(TaskManager)
    manager._tasks = {}
    manager._task_lock = threading.Lock()
    manager._redis_client = fake
    manager._redis_retry_at = 0.0
    return manager


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


def test_watch_exhaustion_never_falls_back_to_an_unconditional_write(
    redis_manager,
):
    """Contention must fail closed instead of clobbering terminal Redis state."""
    manager, fake = redis_manager
    task_id = manager.create_task("simulation_run")
    stale = Task.from_dict(json.loads(fake.data[f"task:{task_id}"]))
    manager.complete_task(task_id, {"winner": "newer-terminal-state"})
    manager._tasks[task_id] = stale

    class _AlwaysContendedPipeline(FakePipeline):
        def execute(self):
            if self._watching:
                from redis.exceptions import WatchError

                raise WatchError("continuous concurrent writer")
            return super().execute()

    fake.pipeline = lambda: _AlwaysContendedPipeline(fake)

    with pytest.raises(RuntimeError, match="^task_state_contention$"):
        manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=80,
        )

    stored = json.loads(fake.data[f"task:{task_id}"])
    assert stored["status"] == TaskStatus.COMPLETED.value
    assert stored["result"] == {"winner": "newer-terminal-state"}


def test_two_manager_instances_concurrently_share_one_durable_reservation(
    monkeypatch,
):
    """Two processes racing one key must receive exactly one task identity."""
    fake = FakeRedis()
    first_manager = _isolated_manager(fake)
    second_manager = _isolated_manager(fake)
    start = threading.Barrier(2)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)

    def _create(manager, candidate):
        start.wait(timeout=2)
        return manager.create_task(
            "report_generate",
            task_id=candidate,
            idempotency_key="report:simulation-1",
            metadata={"simulation_id": "simulation-1", "graph_id": "graph-1"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(_create, first_manager, "task-first")
        second_future = executor.submit(_create, second_manager, "task-second")
        returned = {first_future.result(), second_future.result()}

    assert len(returned) == 1
    task_id = returned.pop()
    assert task_id in {"task-first", "task-second"}
    assert json.loads(fake.data[f"task:{task_id}"])["task_id"] == task_id


def test_durable_idempotency_rejects_same_key_with_different_identity(
    monkeypatch,
):
    fake = FakeRedis()
    first_manager = _isolated_manager(fake)
    second_manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)

    first_manager.create_task(
        "report_generate",
        task_id="task-first",
        idempotency_key="report:shared-key",
        metadata={"simulation_id": "simulation-a", "graph_id": "graph-a"},
    )

    with pytest.raises(RuntimeError, match="^idempotency_key_conflict$"):
        second_manager.create_task(
            "report_generate",
            task_id="task-second",
            idempotency_key="report:shared-key",
            metadata={"simulation_id": "simulation-b", "graph_id": "graph-b"},
        )


def test_durable_reservation_recovers_when_its_task_record_expired(monkeypatch):
    fake = FakeRedis()
    first_manager = _isolated_manager(fake)
    recovering_manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)

    first_task = first_manager.create_task(
        "simulation_prepare",
        task_id="task-expired",
        idempotency_key="prepare:simulation-1",
        metadata={"simulation_id": "simulation-1"},
    )
    fake.delete(f"task:{first_task}")

    recovered_task = recovering_manager.create_task(
        "simulation_prepare",
        task_id="task-recovered",
        idempotency_key="prepare:simulation-1",
        metadata={"simulation_id": "simulation-1"},
    )

    assert recovered_task == "task-recovered"
    assert recovering_manager.find_in_flight_by_idempotency_key(
        "prepare:simulation-1"
    ) == recovered_task


def test_idempotent_task_update_fails_if_its_durable_reservation_is_missing(
    monkeypatch,
):
    fake = FakeRedis()
    manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)
    task_id = manager.create_task(
        "report_generate",
        task_id="task-reservation-lost",
        idempotency_key="report:reservation-lost",
        metadata={"simulation_id": "simulation-reservation-lost"},
    )
    reservation_key = manager._idempotency_reservation_key(
        "report:reservation-lost"
    )
    fake.delete(reservation_key)

    with pytest.raises(
        RuntimeError,
        match="^task_idempotency_state_invalid$",
    ):
        manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=10,
        )

    stored = json.loads(fake.data[f"task:{task_id}"])
    assert stored["status"] == TaskStatus.PENDING.value


def test_idempotent_task_never_updates_from_local_cache_when_redis_is_lost(
    monkeypatch,
):
    fake = FakeRedis()
    manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)
    task_id = manager.create_task(
        "report_generate",
        task_id="task-redis-lost",
        idempotency_key="report:redis-lost",
        metadata={"simulation_id": "simulation-redis-lost"},
    )
    manager._redis_client = None
    manager._redis_retry_at = time.monotonic() + 60

    with pytest.raises(RuntimeError, match="^task_state_unavailable$"):
        manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=10,
        )

    assert manager._tasks[task_id].status is TaskStatus.PENDING


def test_worker_claim_requires_the_task_semantic_reservation(monkeypatch):
    fake = FakeRedis()
    manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)
    task_id = manager.create_task(
        "report_generate",
        task_id="task-claim-reservation-lost",
        idempotency_key="report:claim-reservation-lost",
        metadata={"simulation_id": "simulation-claim-reservation-lost"},
    )
    fake.delete(
        manager._idempotency_reservation_key(
            "report:claim-reservation-lost"
        )
    )

    with pytest.raises(
        RuntimeError,
        match="^task_idempotency_state_invalid$",
    ):
        manager.claim_task_execution(
            task_id,
            "worker-owner",
            expected_task_type="report_generate",
        )

    assert json.loads(fake.data[f"task:{task_id}"])["status"] == "pending"


def test_worker_claim_rejects_the_wrong_semantic_idempotency_key(monkeypatch):
    fake = FakeRedis()
    manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)
    task_id = manager.create_task(
        "report_generate",
        task_id="task-wrong-semantic-key",
        idempotency_key="report_generate:different-simulation",
        metadata={
            "simulation_id": "simulation-expected",
            "report_id": "report-expected",
        },
    )

    with pytest.raises(
        RuntimeError,
        match="^task_execution_identity_mismatch$",
    ):
        manager.claim_task_execution(
            task_id,
            "worker-owner",
            expected_task_type="report_generate",
            expected_idempotency_key="report_generate:simulation-expected",
        )


def test_report_worker_fence_allows_only_one_concurrent_generation(monkeypatch):
    """A redelivery cannot enter the LLM boundary while its peer owns the task."""
    from app.models.project import ProjectManager
    from app.services.report_agent import ReportManager, ReportStatus
    from app.services.simulation_manager import SimulationManager
    from app.tasks import report_tasks

    fake = FakeRedis()
    manager = _isolated_manager(fake)
    monkeypatch.setattr("app.models.task._audit", lambda **_event: None)
    task_id = manager.create_task(
        "report_generate",
        task_id="task-report-fence",
        idempotency_key="report_generate:simulation-fence",
        metadata={
            "simulation_id": "simulation-fence",
            "report_id": "report-fence",
            "graph_id": "graph-fence",
        },
    )
    simulation = SimpleNamespace(
        simulation_id="simulation-fence",
        project_id="project-fence",
        graph_id="graph-fence",
    )
    project = SimpleNamespace(
        project_id="project-fence",
        graph_id="graph-fence",
        simulation_requirement="Assess the bounded fictional scenario.",
    )
    first_generation_entered = threading.Event()
    release_first_generation = threading.Event()
    generation_lock = threading.Lock()
    generation_calls = 0

    class _ReportAgent:
        def __init__(self, **_context) -> None:
            pass

        def generate_report(self, **request):
            nonlocal generation_calls
            with generation_lock:
                generation_calls += 1
                call_number = generation_calls
            if call_number == 1:
                first_generation_entered.set()
                assert release_first_generation.wait(timeout=3)
            return SimpleNamespace(
                report_id=request["report_id"],
                simulation_id=simulation.simulation_id,
                graph_id=project.graph_id,
                simulation_requirement=project.simulation_requirement,
                status=ReportStatus.COMPLETED,
            )

    monkeypatch.setattr(report_tasks, "TaskManager", lambda: manager)
    monkeypatch.setattr(report_tasks, "ReportAgent", _ReportAgent)
    monkeypatch.setattr(ReportManager, "get_report", lambda _report_id: None)
    monkeypatch.setattr(
        SimulationManager,
        "get_simulation",
        lambda _manager, _simulation_id: simulation,
    )
    monkeypatch.setattr(ProjectManager, "get_project", lambda _project_id: project)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            report_tasks.generate_report_task.run,
            simulation_id=simulation.simulation_id,
            report_id="report-fence",
            task_id=task_id,
        )
        assert first_generation_entered.wait(timeout=3)
        try:
            with pytest.raises(RuntimeError, match="^report_generation_in_progress$"):
                report_tasks.generate_report_task.run(
                    simulation_id=simulation.simulation_id,
                    report_id="report-fence",
                    task_id=task_id,
                )
        finally:
            release_first_generation.set()
        assert first.result(timeout=3) == {
            "success": True,
            "report_id": "report-fence",
        }

    assert generation_calls == 1
    persisted = manager.get_task(task_id)
    assert persisted.status is TaskStatus.COMPLETED
    assert persisted.result["report_id"] == "report-fence"
    assert "execution_owner" not in persisted.to_public_dict()


def test_completed_task_is_not_reverted_by_a_late_progress_update(redis_manager):
    """A straggler update must not un-finish a task and strand its poller."""
    manager, _fake = redis_manager
    task_id = manager.create_task("simulation_run")

    manager.complete_task(task_id, {"ok": True})
    manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=60)

    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    # Terminal status and its coupled progress envelope are immutable.
    assert task.progress == 100


def test_failed_task_is_not_reverted_either(manager):
    task_id = manager.create_task("simulation_run")
    manager.fail_task(task_id, "boom", public_error="run_failed")
    manager.update_task(task_id, status=TaskStatus.PENDING)
    assert manager.get_task(task_id).status == TaskStatus.FAILED


def test_terminal_to_terminal_transition_cannot_replace_completed_outcome(manager):
    """A late delivery cannot replace an already published success."""
    task_id = manager.create_task("simulation_run")
    result = {"ok": True}
    manager.complete_task(task_id, result)
    manager.fail_task(task_id, "post-hoc validation failed")
    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == result
    assert task.error is None
    assert task.public_error is None


def test_duplicate_completed_delivery_cannot_replace_terminal_result(manager):
    task_id = manager.create_task("simulation_run")
    manager.complete_task(task_id, {"winner": "first-delivery"})

    manager.complete_task(task_id, {"winner": "late-duplicate"})

    task = manager.get_task(task_id)
    assert task.status is TaskStatus.COMPLETED
    assert task.result == {"winner": "first-delivery"}


def test_late_partial_update_cannot_replace_terminal_result(manager):
    task_id = manager.create_task("simulation_run")
    manager.complete_task(task_id, {"winner": "first-delivery"})

    manager.update_task(task_id, result={"winner": "late-progress-writer"})

    task = manager.get_task(task_id)
    assert task.status is TaskStatus.COMPLETED
    assert task.result == {"winner": "first-delivery"}


def test_late_processing_update_cannot_rewrite_terminal_envelope(manager):
    task_id = manager.create_task("simulation_run")
    manager.complete_task(task_id, {"winner": "first-delivery"})
    completed = manager.get_task(task_id)
    terminal_snapshot = (
        completed.status,
        completed.progress,
        completed.message,
        completed.progress_detail,
        completed.result,
        completed.error,
        completed.public_error,
    )

    manager.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=11,
        message="late worker",
        progress_detail={"phase": "stale"},
        result={"winner": "late-delivery"},
    )

    persisted = manager.get_task(task_id)
    assert (
        persisted.status,
        persisted.progress,
        persisted.message,
        persisted.progress_detail,
        persisted.result,
        persisted.error,
        persisted.public_error,
    ) == terminal_snapshot


def test_corrupt_persisted_status_is_rejected() -> None:
    payload = Task(
        task_id="task-corrupt-status",
        task_type="simulation_run",
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ).to_dict()
    payload["status"] = "not-a-task-status"

    with pytest.raises(TaskStateUnavailable, match="task_status_invalid"):
        Task.from_dict(payload)


def test_explicit_redis_outage_rejects_non_idempotent_creation(
    manager,
    monkeypatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://configured-but-unavailable:6379/0")
    monkeypatch.setattr(manager, "_get_redis", lambda: None)

    with pytest.raises(TaskStateUnavailable, match="task_state_unavailable"):
        manager.create_task("graph_build")

    assert manager._tasks == {}


def test_explicit_redis_outage_rejects_local_task_update(
    manager,
    monkeypatch,
) -> None:
    task_id = manager.create_task("graph_build")
    monkeypatch.setenv("REDIS_URL", "redis://configured-but-unavailable:6379/0")
    monkeypatch.setattr(manager, "_get_redis", lambda: None)

    with pytest.raises(TaskStateUnavailable, match="task_state_unavailable"):
        manager.update_task(task_id, progress=50)

    assert manager.get_task(task_id).progress == 0


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


def test_idempotency_key_dedupes_in_flight_submissions(redis_manager):
    """A second create_task with the same idempotency_key while the first is
    still in flight returns the first task's id — no duplicate task created
    (ADR-0003)."""
    manager, _fake = redis_manager

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


def test_idempotency_key_allows_resubmit_after_terminal(redis_manager):
    """A task that reached COMPLETED does not block a fresh submission with
    the same key — the caller is explicitly re-running."""
    manager, _fake = redis_manager

    first = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-2",
    )
    manager.complete_task(first, {"ok": True})

    second = manager.create_task(
        "simulation_prepare",
        idempotency_key="client-key-2",
    )
    assert second != first
    assert len(manager._tasks) == 2


def test_find_in_flight_returns_none_for_unknown_or_missing_key(redis_manager):
    manager, _fake = redis_manager
    assert manager.find_in_flight_by_idempotency_key("nope") is None
    assert manager.find_in_flight_by_idempotency_key("") is None
    assert manager.find_in_flight_by_idempotency_key(None) is None


def test_fail_task_does_not_audit_or_create_phantom_for_unknown_id(monkeypatch, tmp_path):
    """Regression: fail_task/complete_task used to emit a transition audit event
    (and update_task created a placeholder) for a task_id that never existed —
    fabricating an event for a phantom entity. Only real transitions are audited."""
    from app.config import Config
    from app.services import audit_log

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    manager = TaskManager()
    manager._tasks.clear()

    # Fail a task that was never created.
    manager.fail_task("nonexistent_task_id", "ghost")

    # No audit event should exist for a phantom task.
    events = audit_log.find_events(entity_id="nonexistent_task_id")
    assert events == [], f"phantom task should not be audited, got {events}"


