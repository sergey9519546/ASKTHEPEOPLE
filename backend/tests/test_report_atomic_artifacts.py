"""Atomic report artifact writes (exec-plan T27).

`ReportManager.save_section` and `ReportManager.assemble_full_report` are both
correctly fenced -- each is called inside `self._generation_write_guard()`, so
`TaskExecutionFence.checkpoint()` has already refused a lapsed lease or a
superseded fencing token before either runs.

What the fence does not cover is *atomicity*. Both wrote with:

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

`'w'` truncates the destination before the first byte is written. A crash, a
provider timeout, or an operator kill between the truncate and the final flush
leaves a **truncated** artifact on disk -- a section file or a whole report that
reads as complete to anything that checks for existence or file size, and is
silently missing its tail to everything that reads it.

There is a second, narrower window: `write_guard` calls `checkpoint()` and then
yields, so a takeover that lands between the check and the write is not
observed. Atomic replace does not close that window -- only a compare-and-swap
at commit time would -- but it does guarantee that whichever worker wins the
race, the file on disk is one worker's *complete* content rather than a
half-written mixture.

These tests assert the recovery property directly by making the write fail
after the destination has been chosen.
"""

import os

import pytest

from app.services.report_agent import ReportManager, ReportSection


@pytest.fixture()
def report_id(tmp_path, monkeypatch):
    """A report rooted in a temp dir, with no fence (fencing is tested elsewhere)."""
    monkeypatch.setattr(ReportManager, "_get_report_folder", classmethod(
        lambda cls, rid: str(tmp_path)
    ))
    monkeypatch.setattr(ReportManager, "_get_report_markdown_path", classmethod(
        lambda cls, rid: os.path.join(str(tmp_path), "report.md")
    ))
    monkeypatch.setattr(ReportManager, "_ensure_report_folder", classmethod(
        lambda cls, rid: None
    ))
    return tmp_path


def _section(text):
    return ReportSection(title="Heading", content=text)


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class _WriteFailsAfterTruncate:
    """Wraps a real file object and fails the first write.

    The underlying `open(..., 'w')` has already run, so the destination has
    already been truncated. This is what makes the test meaningful: patching
    `open` itself to raise would skip the truncate entirely and the test would
    pass against the buggy implementation.
    """

    def __init__(self, real):
        self._real = real

    def write(self, data):
        raise OSError("simulated crash after truncate")

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, *exc):
        return self._real.__exit__(*exc)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _break_staged_writes(monkeypatch):
    """Make the staged write raise, after the staging file exists.

    `_atomic_write_text` stages through ``os.fdopen``, so this patches that.
    Failing the write *after* the staging handle is open is what makes the test
    meaningful: it exercises the window between "staged content exists" and
    "os.replace publishes it".
    """
    real_fdopen = os.fdopen

    def patched(fd, *args, **kwargs):
        return _WriteFailsAfterTruncate(real_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(os, "fdopen", patched)


def test_section_write_leaves_no_file_when_write_fails(report_id, monkeypatch):
    """A first-ever section write that fails must leave no artifact at all."""
    _break_staged_writes(monkeypatch)

    with pytest.raises(OSError):
        ReportManager.save_section("r1", 1, _section("body"))

    section_files = [p for p in os.listdir(str(report_id)) if p.startswith("section_")]
    assert section_files == [], f"partial section file survived: {section_files}"


def test_existing_section_survives_a_failed_rewrite(report_id, monkeypatch):
    """The important case: a failed rewrite must not destroy the previous one."""
    ReportManager.save_section("r1", 1, _section("original complete content"))
    target = os.path.join(str(report_id), "section_01.md")
    original = _read(target)
    assert "original complete content" in original

    _break_staged_writes(monkeypatch)

    with pytest.raises(OSError):
        ReportManager.save_section("r1", 1, _section("replacement that never lands"))

    assert _read(target) == original, (
        "the previous section was truncated by a failed rewrite; the write is "
        "not atomic"
    )


def test_no_staging_debris_is_left_behind(report_id, monkeypatch):
    """A failed write must not leave its staging file behind."""
    ReportManager.save_section("r1", 1, _section("original"))
    _break_staged_writes(monkeypatch)

    with pytest.raises(OSError):
        ReportManager.save_section("r1", 1, _section("replacement"))

    leftovers = [p for p in os.listdir(str(report_id)) if p.startswith(".tmp-")]
    assert leftovers == [], f"staging debris left behind: {leftovers}"


def test_atomic_write_replaces_content_in_full(report_id):
    """The ordinary success path still overwrites completely."""
    ReportManager.save_section("r1", 1, _section("first"))
    ReportManager.save_section("r1", 1, _section("second"))
    target = os.path.join(str(report_id), "section_01.md")
    assert _read(target).strip() == "## Heading\n\nsecond"
    assert "first" not in _read(target)


def test_write_is_visible_immediately_after_return(report_id):
    """Atomic replace must not defer visibility -- readers see new content at once."""
    ReportManager.save_section("r1", 1, _section("visible"))
    target = os.path.join(str(report_id), "section_01.md")
    assert os.path.exists(target)
    assert _read(target).strip() == "## Heading\n\nvisible"
