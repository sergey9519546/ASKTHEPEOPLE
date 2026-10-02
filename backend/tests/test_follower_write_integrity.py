"""A follower write that did not land must not be reported as a write.

`follower_engine.apply_follower_round_in_proc` used to increment its counter
inside the insert loop and then swallow `except Exception` across the
`commit()` as well. A commit-time failure, a constraint violation, or a lock
timeout therefore all returned a non-zero row count for rows that never reached disk.

That is the worst shape of silent failure: the caller reads success. It was
found by the stub audit on 2026-10-02, which flagged the stated rationale
("tables differ slightly between platforms") as narrower than the handler it
justified -- it covers schema differences, not commit-time or integrity errors.

The tolerance is still correct for what it was written for, so it is kept and
narrowed rather than removed: a missing or mismatched column is an expected
platform difference and must not abort a run. What changed is that the commit
sits outside the tolerant scope, and the counter is only published once the
commit has succeeded.
"""

from __future__ import annotations

import sqlite3

import pytest


class _Conn:
    """Minimal db handle that records what was executed and when it committed."""

    def __init__(self, fail_commit: bool = False, fail_execute: bool = False):
        self.fail_commit = fail_commit
        self.fail_execute = fail_execute
        self.executed: list[str] = []
        self.commits = 0

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        if self.fail_execute:
            raise sqlite3.OperationalError("no such table: likes")
        self.executed.append(sql)
        return self

    def commit(self):
        if self.fail_commit:
            raise sqlite3.OperationalError("database is locked")
        self.commits += 1


ACTIONS = [
    {
        "agent_id": "u-1",
        "action_type": "LIKE_POST",
        "action_args": {"tweet_id": "t-1"},
        "timestamp": "2026-01-01T00:00:00Z",
    },
    {
        "agent_id": "u-1",
        "action_type": "REPOST",
        "action_args": {"tweet_id": "t-2"},
        "timestamp": "2026-01-01T00:00:01Z",
    },
]


def _patch_engine(monkeypatch, actions=ACTIONS):
    """Force FollowerEngine to emit exactly the given actions."""
    from app.services import follower_engine as fe

    class _Stub:
        def compute_round_actions(self, *a, **k):
            return list(actions)

    monkeypatch.setattr(fe, "FollowerEngine", _Stub)
    return fe


def _write(monkeypatch, conn):
    fe = _patch_engine(monkeypatch)
    return fe.apply_follower_round_in_proc(
        conn,
        [{"id": "u-1"}],  # followers
        [{"post_id": "t-1"}],  # round_actions; must be non-empty to proceed
        1,
        "twitter",
    )


class TestSuccessfulWriteIsCounted:
    def test_rows_are_counted_once_the_commit_succeeds(self, monkeypatch):
        conn = _Conn()
        assert _write(monkeypatch, conn) == 2
        assert conn.commits == 1
        assert len(conn.executed) == 2


class TestCommitFailureIsNeverReportedAsSuccess:
    def test_commit_failure_raises_instead_of_returning_a_count(self, monkeypatch):
        conn = _Conn(fail_commit=True)
        with pytest.raises(sqlite3.OperationalError):
            _write(monkeypatch, conn)
        # The point of the fix: the caller must not see 2 rows written.
        assert conn.commits == 0


class TestSchemaMismatchStaysTolerant:
    def test_missing_table_returns_zero_rather_than_raising(self, monkeypatch):
        # This is the case the original tolerance was written for, and it is a
        # real one: platform variants carry slightly different schemas.
        conn = _Conn(fail_execute=True)
        assert _write(monkeypatch, conn) == 0
        # Nothing was committed, so nothing may claim to have been committed.
        assert conn.commits == 0

    def test_no_input_short_circuits_without_touching_the_connection(self, monkeypatch):
        fe = _patch_engine(monkeypatch)
        assert fe.apply_follower_round_in_proc(None, [], [], 1, "twitter") == 0