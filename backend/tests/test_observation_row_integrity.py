"""Pin the exception policy of the observation store's per-row ingest streams.

``_ingest_sqlite_platform_rows`` in ``app/services/simulation_observation_store.py``
reads a platform runtime database and writes the observation store. Each of its
three evidence streams is wrapped in a handler whose comment said it tolerated a
platform schema that "differs" -- a missing table or column.

All three caught ``sqlite3.Error``, which is the **base** class of
``sqlite3.IntegrityError``. A handler that exists to tolerate a missing column was
therefore also discarding constraint violations, rejected values, and malformed
records: the stream aborted, the row was never written, and nothing told the
caller, which could not tell a partial ingest from a complete one. That is the
same defect class as the swallowed ``commit()`` in ``follower_engine``.

These tests pin both halves of the correction, per stream:

* a missing table or column is still tolerated, and the tolerance is
  stream-local -- the sibling streams still ingest, which is what the original
  comment promised and the only thing the handler ever needed to guarantee;
* a constraint violation is no longer swallowed for any of the three streams.

A structural pin at the end fixes the two surviving ``except sqlite3.Error``
sites to the read-only ones that are still correct, so widening a stream handler
back to the base class fails here rather than silently again.
"""

from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

import pytest

from app.services.simulation_artifacts import observation_db_path
from app.services.simulation_observation_store import sync_observation_store

REPO_ROOT = Path(__file__).resolve().parents[2]
STORE_SOURCE = REPO_ROOT / "backend" / "app" / "services" / "simulation_observation_store.py"

VALID_USER = (
    "CREATE TABLE user (user_id INTEGER PRIMARY KEY, agent_id INTEGER,"
    " name TEXT, user_name TEXT);"
)
VALID_TRACE = "CREATE TABLE trace (user_id INTEGER, action TEXT, info TEXT, created_at TEXT);"
VALID_POST = "CREATE TABLE post (user_id INTEGER, content TEXT, created_at TEXT);"
VALID_COMMENT = (
    "CREATE TABLE comment (user_id INTEGER, post_id INTEGER, content TEXT, created_at TEXT);"
)

# Two of the three rows become `actions`; the INTERVIEW row becomes `interviews`.
TRACE_ROWS = (
    ("create_post", {"content": "Housing policy is escalating", "round_num": 3}, "2026-03-23T10:00:00"),
    ("interview", {"prompt": "What changed?", "response": "It intensified.", "round_num": 3}, "2026-03-23T11:00:00"),
    ("create_post", {"content": "A second thread starts here", "round_num": 4}, "2026-03-23T12:00:00"),
)
POST_ROWS = (
    ("Housing policy is escalating", "2026-03-23T10:00:00"),
    ("A second thread starts here", "2026-03-23T12:00:00"),
)
COMMENT_ROWS = (
    ("Students are reacting sharply.", "2026-03-23T10:05:00"),
    ("Another reply follows.", "2026-03-23T10:06:00"),
)

EVIDENCE_TABLES = ("actions", "interviews", "posts", "comments")


def _table_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    return {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}


def _insert_available(
    cursor: sqlite3.Cursor, table: str, available: set[str], values: dict
) -> None:
    """Insert only the columns the declared table actually has.

    A tolerance test needs a table with a *deliberately incomplete* shape; the
    fixture that fills it must not fail on the very column it removed.
    """
    columns = [name for name in values if name in available]
    if not columns:
        return
    placeholders = ", ".join(["?"] * len(columns))
    cursor.execute(
        f"INSERT INTO {table}({', '.join(columns)}) VALUES ({placeholders})",
        [values[name] for name in columns],
    )


def _write_source_db(path: Path, ddl: str) -> None:
    """Create a platform runtime database with the given table shapes."""
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.executescript(ddl)
        cursor.execute(
            "INSERT INTO user(user_id, agent_id, name, user_name) VALUES (1, 0, 'Alice', 'alice_001')"
        )
        trace_columns = _table_columns(cursor, "trace")
        for action, info, created_at in TRACE_ROWS:
            _insert_available(
                cursor,
                "trace",
                trace_columns,
                {
                    "user_id": 1,
                    "action": action,
                    "info": json.dumps(info),
                    "created_at": created_at,
                },
            )
        post_columns = _table_columns(cursor, "post")
        for content, created_at in POST_ROWS:
            _insert_available(
                cursor,
                "post",
                post_columns,
                {"user_id": 1, "content": content, "created_at": created_at},
            )
        comment_columns = _table_columns(cursor, "comment")
        for content, created_at in COMMENT_ROWS:
            _insert_available(
                cursor,
                "comment",
                comment_columns,
                {"user_id": 1, "content": content, "created_at": created_at},
            )
        conn.commit()
    finally:
        conn.close()


def _declare_destination_table(simulation_dir: Path, ddl: str) -> None:
    """Declare one observation table before the store does.

    ``ensure_observation_store`` issues ``CREATE TABLE IF NOT EXISTS``, so a table
    declared here survives and the ingest writes into *this* shape. That is how an
    integrity violation is made reachable at all: the shipped evidence tables carry
    an autoincrement primary key and no UNIQUE, NOT NULL, or CHECK constraint, so
    a constraint violation has to be introduced deliberately -- which is exactly
    what a future schema change would do.
    """
    conn = sqlite3.connect(observation_db_path(str(simulation_dir)))
    try:
        conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def _row_counts(simulation_dir: Path, tables=EVIDENCE_TABLES) -> dict[str, int]:
    conn = sqlite3.connect(observation_db_path(str(simulation_dir)))
    try:
        cursor = conn.cursor()
        return {
            table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }
    finally:
        conn.close()


def _constrained(table: str) -> str:
    """The shipped column list for an evidence table, plus a UNIQUE(platform).

    Every row an evidence stream writes carries the same ``platform`` value, so a
    second row collides. This is the duplicate-key case the old base-class handler
    was also silently discarding.
    """
    shipped = {
        "actions": (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, round_num INTEGER,"
            " agent_id INTEGER, agent_name TEXT, action_type TEXT, action_args_json TEXT,"
            " timestamp TEXT, trace_ref TEXT, is_bootstrap INTEGER DEFAULT 0,"
            " is_scheduled INTEGER DEFAULT 0"
        ),
        "comments": (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, round_num INTEGER,"
            " agent_id INTEGER, agent_name TEXT, content TEXT, timestamp TEXT,"
            " trace_ref TEXT"
        ),
        "posts": (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, round_num INTEGER,"
            " agent_id INTEGER, agent_name TEXT, content TEXT, timestamp TEXT,"
            " trace_ref TEXT"
        ),
        "interviews": (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, round_num INTEGER,"
            " agent_id INTEGER, agent_name TEXT, prompt TEXT, response TEXT,"
            " timestamp TEXT, trace_ref TEXT"
        ),
    }
    return f"CREATE TABLE {table} ({shipped[table]}, UNIQUE(platform))"


# --------------------------------------------------------------------------
# Tolerance is retained, and it is stream-local.
# --------------------------------------------------------------------------


def test_missing_trace_column_is_tolerated_and_the_sibling_streams_still_ingest(tmp_path):
    """The trace stream loses its column; actions/interviews stay empty and the
    post and comment streams -- which run after it -- are unaffected."""
    _write_source_db(
        tmp_path / "twitter_simulation.db",
        VALID_USER
        + "CREATE TABLE trace (user_id INTEGER, action TEXT, info TEXT);"
        + VALID_POST
        + VALID_COMMENT,
    )

    sync_observation_store(str(tmp_path))

    assert _row_counts(tmp_path) == {
        "actions": 0,
        "interviews": 0,
        "posts": 2,
        "comments": 2,
    }


def test_missing_post_column_is_tolerated_and_the_sibling_streams_still_ingest(tmp_path):
    _write_source_db(
        tmp_path / "twitter_simulation.db",
        VALID_USER + VALID_TRACE + "CREATE TABLE post (user_id INTEGER, content TEXT);" + VALID_COMMENT,
    )

    sync_observation_store(str(tmp_path))

    assert _row_counts(tmp_path) == {
        "actions": 2,
        "interviews": 1,
        "posts": 0,
        "comments": 2,
    }


def test_missing_comment_column_is_tolerated_and_the_sibling_streams_still_ingest(tmp_path):
    _write_source_db(
        tmp_path / "twitter_simulation.db",
        VALID_USER + VALID_TRACE + VALID_POST + "CREATE TABLE comment (user_id INTEGER, content TEXT);",
    )

    sync_observation_store(str(tmp_path))

    assert _row_counts(tmp_path) == {
        "actions": 2,
        "interviews": 1,
        "posts": 2,
        "comments": 0,
    }


def test_absent_platform_tables_are_tolerated(tmp_path):
    """No trace, post, or comment table at all. The store requires none of them."""
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER)

    sync_observation_store(str(tmp_path))

    assert _row_counts(tmp_path) == {
        "actions": 0,
        "interviews": 0,
        "posts": 0,
        "comments": 0,
    }


# --------------------------------------------------------------------------
# Constraint violations are no longer swallowed.
# --------------------------------------------------------------------------


def test_integrity_error_in_the_trace_stream_reaches_the_caller(tmp_path):
    _declare_destination_table(tmp_path, _constrained("actions"))
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER + VALID_TRACE + VALID_POST + VALID_COMMENT)

    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        sync_observation_store(str(tmp_path))

    assert "UNIQUE constraint failed" in str(excinfo.value)


def test_integrity_error_in_the_post_stream_reaches_the_caller(tmp_path):
    _declare_destination_table(tmp_path, _constrained("posts"))
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER + VALID_TRACE + VALID_POST + VALID_COMMENT)

    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        sync_observation_store(str(tmp_path))

    assert "UNIQUE constraint failed" in str(excinfo.value)


def test_integrity_error_in_the_comment_stream_reaches_the_caller(tmp_path):
    _declare_destination_table(tmp_path, _constrained("comments"))
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER + VALID_TRACE + VALID_POST + VALID_COMMENT)

    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        sync_observation_store(str(tmp_path))

    assert "UNIQUE constraint failed" in str(excinfo.value)


def test_a_rejected_row_is_never_reported_as_a_successful_sync(tmp_path):
    """The caller cannot mistake a partial ingest for a complete one: a store that
    refuses a row raises instead of returning a database path."""
    _declare_destination_table(tmp_path, _constrained("posts"))
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER + VALID_TRACE + VALID_POST + VALID_COMMENT)

    with pytest.raises(sqlite3.IntegrityError):
        sync_observation_store(str(tmp_path))


def test_the_store_remains_readable_after_a_rejected_row(tmp_path):
    """The exception is raised, not swallowed into a half-written file, so the
    committed destination state is still inspectable by the caller."""
    _declare_destination_table(tmp_path, _constrained("posts"))
    _write_source_db(tmp_path / "twitter_simulation.db", VALID_USER + VALID_TRACE + VALID_POST + VALID_COMMENT)

    with pytest.raises(sqlite3.IntegrityError):
        sync_observation_store(str(tmp_path))

    # No uncommitted rows from the aborted ingest are visible.
    assert _row_counts(tmp_path, ("posts",))["posts"] == 0


# --------------------------------------------------------------------------
# Structural pins: why the base class was the defect, and where it may stay.
# --------------------------------------------------------------------------


def test_integrity_error_is_a_subclass_of_the_class_the_handlers_used_to_catch():
    """The defect in one assertion: what these handlers caught swallowed every
    constraint violation, and what they catch now does not."""
    assert issubclass(sqlite3.IntegrityError, sqlite3.Error)
    assert not issubclass(sqlite3.IntegrityError, sqlite3.OperationalError)


def _handlers_catching(qualified_name: str) -> list[str]:
    """The enclosing function of every ``except <qualified_name>`` in the store.

    Keyed on the function name rather than a line number, so an unrelated edit
    above a handler does not invalidate the pin.
    """
    tree = ast.parse(STORE_SOURCE.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler) and child.type is not None:
                if ast.unparse(child.type) == qualified_name:
                    found.append(node.name)
    return found


def test_the_three_row_ingest_streams_catch_operational_error_not_the_base_class():
    assert _handlers_catching("sqlite3.OperationalError") == [
        "_ingest_sqlite_platform_rows"
    ] * 3


def test_the_base_class_is_confined_to_the_two_read_only_sites():
    """Both remaining sites are read-only and lose no evidence:

    * ``_connect`` -- the WAL journal-mode probe, an optimisation.
    * the ``user`` lookup in the ingest, which degrades to an empty actor map and
      renames agents rather than dropping rows.

    A new base-class handler anywhere else means a row can vanish again.
    """
    assert _handlers_catching("sqlite3.Error") == [
        "_connect",
        "_ingest_sqlite_platform_rows",
    ]