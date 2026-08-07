"""Tests for the append-only audit log (Gate 3: ADR-0012, state-machines.md:405-406).

The audit log must: be append-only (no update/delete API), record every
state transition with actor/reason/timestamp/before/after, never raise on a
write failure, and support incident-response lookup (find_events /
find_affected_runs).
"""

import json
import os

import pytest

from app.config import Config
from app.services import audit_log


@pytest.fixture
def isolated_audit(monkeypatch, tmp_path):
    """Point the audit log at an isolated tmp tree."""
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    return tmp_path


def _read_raw(tmp_path):
    path = tmp_path / "audit" / "audit.log"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_record_event_writes_append_only_jsonl(isolated_audit):
    audit_log.record_event(
        action="project.created",
        entity_type="project",
        entity_id="proj_1",
        actor="system",
        after={"status": "created"},
    )
    audit_log.record_event(
        action="project.deleted",
        entity_type="project",
        entity_id="proj_1",
        reason="hard_delete",
    )
    events = _read_raw(isolated_audit)
    assert len(events) == 2
    assert events[0]["action"] == "project.created"
    assert events[1]["action"] == "project.deleted"
    # Each event carries the required transition fields (state-machines.md:405-406).
    for e in events:
        assert "timestamp" in e and e["timestamp"]
        assert "actor" in e
        assert "before" in e and "after" in e


def test_log_is_append_only_in_practice(isolated_audit):
    """The log only ever grows: recording a second event does not rewrite or
    truncate the first. This is a behavioral check (file grows, prior bytes
    preserved), not just an API-surface check."""
    audit_log.record_event(action="first", entity_type="t", entity_id="id1")
    first_bytes = (isolated_audit / "audit" / "audit.log").read_bytes()

    audit_log.record_event(action="second", entity_type="t", entity_id="id1")
    full_bytes = (isolated_audit / "audit" / "audit.log").read_bytes()

    # The first event's bytes are a prefix of the full file (append, not rewrite).
    assert full_bytes.startswith(first_bytes)
    assert len(full_bytes) > len(first_bytes)


def test_record_event_never_raises_on_write_failure(monkeypatch, tmp_path):
    """An audit failure must not break the operation being audited."""
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    # Force the open() to fail.
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    # Must not raise.
    audit_log.record_event(action="x", entity_type="t", entity_id="id1")


def test_find_events_filters_and_returns_newest_first(isolated_audit):
    for i in range(3):
        audit_log.record_event(action="task.completed", entity_type="task", entity_id=f"task_{i}")
    audit_log.record_event(action="project.created", entity_type="project", entity_id="proj_x")

    by_type = audit_log.find_events(entity_type="task")
    assert len(by_type) == 3
    # Newest first.
    assert by_type[0]["entity_id"] == "task_2"
    assert by_type[-1]["entity_id"] == "task_0"

    by_action = audit_log.find_events(action="project.created")
    assert len(by_action) == 1
    assert by_action[0]["entity_id"] == "proj_x"


def test_find_events_respects_limit(isolated_audit):
    for i in range(5):
        audit_log.record_event(action="x", entity_type="t", entity_id=f"id_{i}")
    assert len(audit_log.find_events(limit=2)) == 2


def test_find_events_returns_newest_n_not_oldest_n(isolated_audit):
    """Regression: find_events used to early-break at `limit`, returning the
    OLDEST N matches reversed — the wrong end of the log for incident
    response. It must scan the whole file and return the NEWEST N."""
    for i in range(10):
        audit_log.record_event(action="x", entity_type="t", entity_id="same")
    newest_two = audit_log.find_events(entity_id="same", limit=2)
    assert len(newest_two) == 2
    # Newest-first, and these are events #9 and #8 (the last appended), not #0/#1.
    # We can't read the index from the event (no counter), but we CAN prove the
    # selection is the tail by checking that a limit=2 result is a suffix of the
    # limit=10 result.
    all_ten = audit_log.find_events(entity_id="same", limit=10)
    assert all_ten[:2] == newest_two  # the newest 2 are the same regardless of limit


def test_find_affected_runs(isolated_audit):
    """The incident-response convenience returns all events for one entity."""
    audit_log.record_event(action="simulation.status_changed", entity_type="simulation", entity_id="sim_1")
    audit_log.record_event(action="export.created", entity_type="export", entity_id="exp_9")
    audit_log.record_event(action="simulation.status_changed", entity_type="simulation", entity_id="sim_1")

    affected = audit_log.find_affected_runs("sim_1", entity_type="simulation")
    assert len(affected) == 2
    assert all(e["entity_id"] == "sim_1" for e in affected)


def test_safe_summary_caps_lists_and_stringifies_objects(isolated_audit):
    """_safe_summary caps lists to 20 items and stringifies non-primitive
    objects — the actual transformations, not the str/int passthrough."""
    import datetime

    audit_log.record_event(
        action="x",
        entity_type="t",
        entity_id="id1",
        after={
            "long_list": list(range(25)),      # should cap to 20
            "an_object": datetime.datetime(2026, 1, 1),  # not JSON-native → str()
            "a_str": "kept",                    # passthrough
            "an_int": 42,                       # passthrough
        },
    )
    events = _read_raw(isolated_audit)
    after = events[0]["after"]
    # List capped to 20, not the full 25.
    assert len(after["long_list"]) == 20
    # Non-serializable object stringified (and JSON-safe), not dropped.
    assert isinstance(after["an_object"], str)
    assert "2026" in after["an_object"]
    # Primitives passthrough.
    assert after["a_str"] == "kept"
    assert after["an_int"] == 42


def test_record_event_never_raises_on_non_serializable_payload(isolated_audit):
    """A float('nan') survives _safe_summary (floats passthrough) but breaks
    json.dumps — record_event must catch that and NOT raise (the 'never
    raises' contract that models/task.py and models/project.py rely on)."""
    # Must not raise ValueError despite nan being non-JSON-compliant.
    audit_log.record_event(
        action="x", entity_type="t", entity_id="id1",
        after={"bad_float": float("nan")},
    )


def test_timestamps_are_iso8601_with_timezone(isolated_audit):
    audit_log.record_event(action="x", entity_type="t", entity_id="id1")
    events = _read_raw(isolated_audit)
    ts = events[0]["timestamp"]
    # datetime.fromisoformat parses it cleanly (ISO-8601) and carries a tz.
    from datetime import datetime
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


# --- Wiring: project + task lifecycle emit the right events ---


def test_project_create_delete_are_audited(monkeypatch, tmp_path):
    from app.models.project import ProjectManager

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects"))

    p = ProjectManager.create_project(name="Wired")
    actions = [e["action"] for e in audit_log.find_events(entity_id=p.project_id)]
    assert actions == ["project.created"]

    ProjectManager.delete_project(p.project_id)
    actions = [e["action"] for e in audit_log.find_events(entity_id=p.project_id)]
    assert "project.deleted" in actions


def test_task_lifecycle_audited(monkeypatch, tmp_path):
    from app.models.task import TaskManager, TaskStatus

    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))

    tm = TaskManager()
    tm._tasks.clear()
    tid = tm.create_task("simulation_run", metadata={"simulation_id": "sim_1"})
    assert [e["action"] for e in audit_log.find_events(entity_id=tid)] == ["task.created"]

    tm.fail_task(tid, "boom")
    actions = [e["action"] for e in audit_log.find_events(entity_id=tid)]
    assert actions[0] == "task.failed"  # newest first
    assert actions[-1] == "task.created"
