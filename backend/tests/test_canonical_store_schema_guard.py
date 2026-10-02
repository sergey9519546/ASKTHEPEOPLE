"""Flag-enabled-but-unmigrated must fail loudly (exec-plan T6).

With a single schema definition (ADR-0013), the remaining way to lose data
silently is enabling a feature flag against a database that exists, is
reachable, and was never migrated. That used to surface as a raw driver
``UndefinedTable`` at the first query, naming a SQL fragment and giving no
indication that a migration had not been run.

These tests assert the replacement: a named exception that lists the missing
tables and the remediation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import CanonicalSchemaMissing, missing_tables, require_tables  # noqa: E402


def _engine_with(tmp_path: Path, *tables: str):
    """A reachable SQLite database containing exactly the named tables."""
    path = tmp_path / "canonical.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as conn:
        for table in tables:
            conn.execute(text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY)"))
    return engine


def test_missing_tables_reports_absent_only(tmp_path: Path):
    engine = _engine_with(tmp_path, "projects", "sources")
    assert missing_tables(engine, {"projects", "sources", "dw_runs"}) == {"dw_runs"}


def test_require_tables_passes_when_all_present(tmp_path: Path):
    engine = _engine_with(tmp_path, "projects", "sources")
    require_tables(engine, {"projects", "sources"})  # must not raise


def test_require_tables_raises_naming_table_and_remedy(tmp_path: Path):
    """The whole point: the message must name the missing table and say what
    to do, because the operator hitting it sees a reachable database."""
    engine = _engine_with(tmp_path)  # no tables at all
    with pytest.raises(CanonicalSchemaMissing) as excinfo:
        require_tables(engine, {"projects", "sources", "ontologies"})

    message = str(excinfo.value)
    for table in ("projects", "sources", "ontologies"):
        assert table in message, f"{table} not named in: {message}"
    assert "alembic upgrade head" in message
    assert "never migrated" in message or "was never migrated" in message


def test_repositories_declare_only_real_migration_tables():
    """The `_REQUIRED_TABLES` sets were read from each repository's SQL.

    A table added to a query without updating the set leaves the guard quiet;
    a table removed from the query while left in the set makes it noisy. This
    asserts every declared name is a table some migration actually creates.
    """
    from app.db import missing_tables
    from app.services.project_repository import ProjectRepository
    from app.services.source_repository import SourceRepository

    migrations = ROOT / "backend" / "migrations" / "versions"
    import re

    created = set()
    for path in sorted(migrations.glob("*.py")):
        created |= set(
            re.findall(
                r"""create_table\(\s*['"]([a-z_][a-z0-9_]*)['"]""",
                path.read_text(encoding="utf-8"),
            )
        )
    assert created, "no migration tables parsed; the guard would pass vacuously"

    for repository in (ProjectRepository, SourceRepository):
        declared = set(repository._REQUIRED_TABLES)
        unknown = declared - created
        assert not unknown, (
            f"{repository.__name__}._REQUIRED_TABLES names tables no "
            f"migration creates: {sorted(unknown)}"
        )


def test_repository_raises_when_schema_absent(tmp_path: Path, monkeypatch):
    """End to end through the repository accessor: a flag-enabled store whose
    tables were never created raises CanonicalSchemaMissing, not
    UndefinedTable.

    The engine is left as None on purpose. The schema check runs once, on
    acquisition, rather than per query — re-checking on every call would be
    wasteful — so a pre-built engine legitimately skips it.
    """
    from app.config import Config
    from app.services.project_repository import ProjectRepository

    db_path = tmp_path / "unmigrated.db"
    create_engine(f"sqlite:///{db_path.as_posix()}").dispose()  # reachable, no tables

    monkeypatch.setattr(Config, "DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(ProjectRepository, "_engine", None, raising=False)

    with pytest.raises(CanonicalSchemaMissing) as excinfo:
        ProjectRepository._get_engine()

    message = str(excinfo.value)
    assert "projects" in message
    assert "alembic upgrade head" in message