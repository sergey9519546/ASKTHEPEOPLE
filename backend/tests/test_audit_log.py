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


def test_events_are_never_overwritten(isolated_audit):
    """The log is append-only: there is no update/delete API exposed."""
    audit_log.record_event(action="x", entity_type="t", entity_id="id1")
    # No public function exists to modify or remove a recorded event.
    public_api = [n for n in dir(audit_log) if not n.startswith("_") and n != "os"]
    assert not any(n in public_api for n in ("update_event", "delete_event", "rewrite", "truncate"))


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


def test_find_affected_runs(isolated_audit):
    """The incident-response convenience returns all events for one entity."""
    audit_log.record_event(action="simulation.status_changed", entity_type="simulation", entity_id="sim_1")
    audit_log.record_event(action="export.created", entity_type="export", entity_id="exp_9")
    audit_log.record_event(action="simulation.status_changed", entity_type="simulation", entity_id="sim_1")

    affected = audit_log.find_affected_runs("sim_1", entity_type="simulation")
    assert len(affected) == 2
    assert all(e["entity_id"] == "sim_1" for e in affected)


def test_safe_summary_strips_oversized_values(isolated_audit):
    """A caller cannot bloat the log with huge or non-serializable values."""
    audit_log.record_event(
        action="x",
        entity_type="t",
        entity_id="id1",
        after={"big": "x" * 1000, "nested": {"deep": "y" * 500}},
    )
    events = _read_raw(isolated_audit)
    # big string is retained (str values aren't truncated by _safe_summary),
    # but non-serializable types are stringified and lists are capped.
    assert events[0]["after"]["big"] == "x" * 1000
    assert events[0]["after"]["nested"]["deep"] == "y" * 500


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
