"""Startup must not create schema (exec-plan T4, ADR-0012, ADR-0013).

`create_app` used to call `init_db(engine)`, which called
`Base.metadata.create_all`. That contradicted ADR-0012 ("web and worker startup
never call `create_all`") and was actively harmful: it materialized the ORM
stub's `projects` table, which has no `project_id` column, while the only live
canonical-store repository queries `WHERE project_id = :project_id`.

These tests pin the removal. They are deliberately behavioural rather than
source-scanning: they exercise `create_app` and observe the database, so a
reintroduced `create_all` fails regardless of how it is spelled.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def record_create_all(monkeypatch):
    """Record any schema creation attempt during boot, without raising.

    Raising does not work here: `create_app` wraps the database block in
    `except Exception` and falls back to filesystem storage, so an
    AssertionError raised from inside `create_all` is swallowed and the test
    passes. The call therefore has to be observed, not signalled.
    """
    from app.db.schema import Base

    calls: list[dict] = []

    def _record(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(Base.metadata, "create_all", _record, raising=False)
    return calls


def test_create_app_does_not_create_schema(record_create_all):
    """Boot the real application factory and observe whether it creates schema."""
    from app import create_app

    assert create_app() is not None
    assert record_create_all == [], (
        "startup called Base.metadata.create_all, which ADR-0012 forbids "
        f"(web and worker startup never call create_all). Calls: {record_create_all}"
    )


def test_drop_all_is_not_on_the_boot_path(record_create_all):
    """The sibling hazard: a drop_all/create_all pair during startup would
    still mean startup owns the schema lifecycle."""
    from app import create_app

    create_app()
    assert not record_create_all


def test_init_db_is_refused(tmp_path: Path):
    """The old entry point must fail loudly rather than silently work.

    A surviving caller would otherwise reintroduce the divergence the removal
    was meant to close.
    """
    from app.db import get_engine, init_db

    engine = get_engine(f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    with pytest.raises(RuntimeError) as excinfo:
        init_db(engine)
    message = str(excinfo.value)
    assert "alembic" in message.lower()
    assert "ADR-0013" in message