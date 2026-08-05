"""Persistence invariants for the Project aggregate (Gate 3).

Covers the audit §5 P1 "Non-atomic file persistence" fix and the ADR-0008
source-hashing-at-ingest requirement. These are unit-level contracts on
ProjectManager; route-level behavior is covered by the input-policy and
claim-boundary suites.
"""

import io
from datetime import datetime

import pytest
from werkzeug.datastructures import FileStorage

from app.config import Config
from app.models.project import Project, ProjectManager, ProjectStatus


@pytest.fixture
def projects_dir(monkeypatch, tmp_path):
    """Point ProjectManager at an isolated tmp tree."""
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    # PROJECTS_DIR is computed at class-definition time from Config.UPLOAD_FOLDER;
    # rebind it so the tmp path is actually used.
    monkeypatch.setattr(
        ProjectManager, "PROJECTS_DIR", str(tmp_path / "projects")
    )
    return tmp_path / "projects"


def _make_project(projects_dir) -> Project:
    return ProjectManager.create_project(name="Atomic test")


def test_save_project_writes_atomically(projects_dir):
    """A successful save leaves a complete, valid JSON record; no temp file
    is left behind in the project directory."""
    project = _make_project(projects_dir)
    project.name = "updated"
    ProjectManager.save_project(project)

    meta = projects_dir / project.project_id / "project.json"
    assert meta.read_text(encoding="utf-8").startswith("{")

    # No leftover temp file from the atomic write.
    leftovers = [p.name for p in (projects_dir / project.project_id).iterdir()
                 if p.name.startswith(".tmp-")]
    assert leftovers == []

    # The persisted record reflects the update and round-trips.
    reloaded = ProjectManager.get_project(project.project_id)
    assert reloaded is not None
    assert reloaded.name == "updated"


def test_save_project_failure_leaves_previous_record_intact(projects_dir, monkeypatch):
    """If the write fails mid-way, the previously-saved canonical record must
    be unchanged — not a truncated/empty file. This is the core guarantee of
    the atomic (temp + os.replace) write."""
    project = _make_project(projects_dir)
    project.name = "first-good-version"
    ProjectManager.save_project(project)
    meta = projects_dir / project.project_id / "project.json"
    good_bytes = meta.read_bytes()

    # Force the final write to fail AFTER the temp file is written but BEFORE
    # os.replace completes, by making os.replace raise.
    project.name = "should-not-appear"

    real_replace = __import__("os").replace

    def raising_replace(src, dst, *args, **kwargs):
        # Only sabotage the rename onto the canonical meta path.
        if dst == str(meta):
            raise OSError("simulated mid-rename failure")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr("app.models.project.os.replace", raising_replace)

    with pytest.raises(OSError):
        ProjectManager.save_project(project)

    # Canonical record is byte-identical to the last good write.
    assert meta.read_bytes() == good_bytes
    reloaded = ProjectManager.get_project(project.project_id)
    assert reloaded.name == "first-good-version"
    # And the orphaned temp file was cleaned up.
    leftovers = [p.name for p in (projects_dir / project.project_id).iterdir()
                 if p.name.startswith(".tmp-")]
    assert leftovers == []


def test_save_extracted_text_is_atomic_and_readable(projects_dir):
    """save_extracted_text must use the atomic path too."""
    project = _make_project(projects_dir)
    ProjectManager.save_extracted_text(project.project_id, "line one\n")
    text_path = projects_dir / project.project_id / "extracted_text.txt"
    assert text_path.read_text(encoding="utf-8") == "line one\n"
    # No temp leftover.
    leftovers = [p.name for p in (projects_dir / project.project_id).iterdir()
                 if p.name.startswith(".tmp-")]
    assert leftovers == []


def test_save_file_to_project_records_sha256_content_hash(projects_dir):
    """Uploaded source bytes must be hashed (sha256) at ingest so the
    canonical record carries a content fingerprint for export provenance
    (ADR-0008). The hash must match the actual stored bytes."""
    project = _make_project(projects_dir)
    import hashlib

    payload = b"source material bytes for hashing"
    expected = hashlib.sha256(payload).hexdigest()

    info = ProjectManager.save_file_to_project(
        project.project_id,
        FileStorage(stream=io.BytesIO(payload), filename="source.txt"),
        "source.txt",
    )

    assert "content_hash" in info
    assert info["content_hash"] == expected
    assert len(info["content_hash"]) == 64
    # And the stored file matches the hashed bytes.
    with open(info["path"], "rb") as stored:
        assert stored.read() == payload


def test_distinct_uploads_get_distinct_hashes(projects_dir):
    """Two different payloads must produce two different hashes (sanity)."""
    project = _make_project(projects_dir)
    a = ProjectManager.save_file_to_project(
        project.project_id,
        FileStorage(stream=io.BytesIO(b"AAAA"), filename="a.txt"),
        "a.txt",
    )
    b = ProjectManager.save_file_to_project(
        project.project_id,
        FileStorage(stream=io.BytesIO(b"BBBB"), filename="b.txt"),
        "b.txt",
    )
    assert a["content_hash"] != b["content_hash"]
