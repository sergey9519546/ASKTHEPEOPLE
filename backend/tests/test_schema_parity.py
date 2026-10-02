"""Schema parity: `backend/migrations/versions/` is the only source of truth.

This file previously compared two schema definitions and recorded the known
divergences between them. There is now only one definition, so the comparison
is gone and what remains is stronger: **the ORM declares no tables at all**.

That is the end state ADR-0013 set. Migrations are canonical; the ORM stub was
removed rather than mirrored, because 198 columns of hand-maintained
duplication would have recreated a second source of truth with more places to
forget than the six tables it replaced.

What these tests protect:

* A new table added to `app/db/schema.py` is a regression, not progress. It
  re-creates the second source of truth, and the boot-time `create_all` that
  once materialized it is gone — so the table would be declared and never used.
* The migrations keep declaring what they are supposed to declare. If they were
  emptied by accident, "the ORM has no tables" would pass vacuously.
* The one thing the ORM must still export, `Base`, still exists and is
  importable, because two modules depend on it.

`KNOWN_ORM_ONLY` and `KNOWN_PK_MISMATCH` were removed with the stub. The
recorded divergences they documented no longer exist to be recorded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ORM_SCHEMA = REPO_ROOT / "backend" / "app" / "db" / "schema.py"
MIGRATIONS = REPO_ROOT / "backend" / "migrations" / "versions"

# Tables the migrations are expected to declare. Guards against the whole set
# being emptied, which would make every other assertion here pass vacuously.
EXPECTED_MIGRATION_TABLES = {
    "projects",
    "graphs",
    "ontologies",
    "simulations",
    "sources",
    "reports",
    "dw_runs",
    "dw_run_stages",
    "dw_run_events",
    "dw_sources",
    "dw_source_versions",
    "dw_source_segments",
    "dw_source_candidates",
    "dw_path_sets",
    "dw_paths",
    "dw_path_set_reviews",
}

ORM_TABLENAME_RE = re.compile(r"""__tablename__\s*=\s*["']([^"']+)["']""")
CREATE_TABLE_RE = re.compile(r"""create_table\(\s*["']([^"']+)["']""")


def _orm_tables() -> set[str]:
    return set(ORM_TABLENAME_RE.findall(ORM_SCHEMA.read_text(encoding="utf-8")))


def _migration_tables() -> set[str]:
    tables: set[str] = set()
    for path in sorted(MIGRATIONS.glob("*.py")):
        tables |= set(CREATE_TABLE_RE.findall(path.read_text(encoding="utf-8")))
    return tables


def test_migrations_still_declare_their_tables():
    found = _migration_tables()
    missing = EXPECTED_MIGRATION_TABLES - found
    assert not missing, (
        f"migrations no longer declare: {sorted(missing)}. Either a revision "
        "was removed by accident or EXPECTED_MIGRATION_TABLES is stale."
    )


def test_migration_chain_is_linear_and_has_one_head():
    """Three revisions, one head. A branch or a second head means two databases
    could exist, which is the ambiguity this whole exercise is closing."""
    revisions: dict[str, str | None] = {}
    for path in sorted(MIGRATIONS.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        rev = re.search(r"^revision:\s*str\s*=\s*'([^']+)'", src, re.M)
        down = re.search(r"^down_revision:.*=\s*(?:'([^']+)'|None)", src, re.M)
        if rev:
            revisions[rev.group(1)] = down.group(1) if down else None

    heads = [r for r, down in revisions.items() if down is None]
    assert len(heads) == 1, f"expected exactly one migration head, got {heads}"
    assert len(revisions) == 3, (
        f"expected 3 revisions, found {len(revisions)}; update this test and "
        "EXPECTED_MIGRATION_TABLES if a revision was added deliberately"
    )


def test_orm_declares_no_tables():
    """The invariant ADR-0013 established.

    A `__tablename__` here is a regression: migrations are canonical, and the
    boot path no longer calls `create_all`, so an ORM table would be declared,
    never created, and never queried.
    """
    declared = _orm_tables()
    assert not declared, (
        "app/db/schema.py must not declare tables. Migrations are the single "
        f"source of truth (ADR-0013). Found: {sorted(declared)}. Do not mirror "
        "the migrations here; that recreates the second source of truth."
    )


def test_orm_still_exports_base():
    """Two modules import `Base`: `app/db/__init__.py` for `drop_db`, and
    `migrations/env.py` as autogenerate's `target_metadata`. Removing it would
    break both."""
    import sys

    backend_root = REPO_ROOT / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from app.db.schema import Base

    assert Base is not None
    assert hasattr(Base, "metadata")


def test_base_metadata_is_empty():
    """Belt and braces: `Base.metadata.tables` is what `create_all` and
    `drop_all` operate on. It must be empty so neither can touch schema."""
    import sys

    backend_root = REPO_ROOT / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from app.db.schema import Base

    assert not Base.metadata.tables, (
        f"Base.metadata still declares {sorted(Base.metadata.tables)}; "
        "drop_all in app/db/__init__.py could then remove real tables"
    )


def test_schema_module_documents_why_it_is_empty():
    """The file must explain itself. An empty module with no rationale reads as
    an accident and gets 'helpfully' repopulated."""
    doc = ORM_SCHEMA.read_text(encoding="utf-8")
    assert "ADR-0013" in doc
    assert "source of truth" in doc
    assert "alembic upgrade head" in doc


def test_drop_db_is_not_on_a_runtime_path():
    """`drop_db` is the last consumer of `Base.metadata`. It must not be
    reachable from application startup, or removing create_all would have left
    a matching hazard behind."""
    runtime = REPO_ROOT / "backend" / "app"
    offenders: list[str] = []
    for path in sorted(runtime.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "__init__.py" and path.parent.name == "db":
            continue  # the definition itself
        if path.name == "schema.py":
            continue  # documents the removal and mentions drop_db by name
        if re.search(r"\bdrop_db\b", src):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert not offenders, (
        f"drop_db is referenced from runtime modules: {offenders}. It operates "
        "on Base.metadata and must not be callable outside tests."
    )


@pytest.mark.parametrize(
    "module",
    ["app.db", "app.db.schema"],
)
def test_db_modules_still_import(module: str):
    import importlib
    import sys

    backend_root = REPO_ROOT / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    assert importlib.import_module(module) is not None