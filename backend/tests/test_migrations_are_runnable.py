"""Gate 3: migrations are runnable, and autogenerate is refused.

Two defects were measured on 2026-10-02 while closing the "a working
`alembic upgrade head` remains gate 3" item in exec-plan 08 fix 1. Both were
live, and one of them would have destroyed a database.

1. **`alembic upgrade head` could not run without production credentials.**
   `migrations/env.py` imported `app.db.schema` at module scope. Importing any
   `app.*` submodule executes `app/__init__.py`, which raises
   `RuntimeError: SECRET_KEY must be set in production` while the `Config`
   class body is evaluated. The migration tool therefore died before touching
   the database -- even against a throwaway SQLite file -- unless a production
   `SECRET_KEY` was exported. After ADR-0013 the import is unnecessary for
   `upgrade`/`downgrade`: `app/db/schema.py` declares `Base` and no tables.

2. **`alembic revision --autogenerate` generated a schema wipe.** Same
   stripping: `Base.metadata` is empty, so autogenerate diffs an empty target
   against a live database and reads every canonical table as removed. Run
   against a database migrated to head it produced a revision whose `upgrade()`
   was **16 `op.drop_table` and 43 `op.drop_index` calls**. It is the standard
   tool for the documented workflow ("adding a table means writing a new
   Alembic revision"), it reports success, and applying it erases the schema.

These tests pin the fix. They drive the real Alembic CLI in a subprocess so they
exercise `env.py` exactly as a deploy would, rather than importing it.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
VERSIONS = BACKEND / "migrations" / "versions"
RECORDED_HEAD = "b2c3d4e5f6a7"

# Credential-shaped variables. Each is popped before every Alembic invocation:
# their ABSENCE is the condition the fix has to survive.
SECRETS = ("SECRET_KEY", "APP_TOKEN", "LLM_API_KEY", "ZEP_API_KEY", "DEBUG")


def _alembic(*args: str, db: Path):
    env = dict(os.environ)
    for key in SECRETS:
        env.pop(key, None)
    env["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _tables(db: Path) -> set[str]:
    connection = sqlite3.connect(db)
    try:
        return {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            )
        }
    finally:
        connection.close()


@pytest.fixture()
def migrated_db(tmp_path: Path) -> Path:
    db = tmp_path / "gate3.db"
    result = _alembic("upgrade", "head", db=db)
    assert result.returncode == 0, (
        "alembic upgrade head failed with no credentials exported:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return db


def test_upgrade_head_runs_without_production_credentials(migrated_db: Path):
    """Regression test for defect 1.

    Before the fix the CLI aborted with `SECRET_KEY must be set in production`
    before it reached the database.
    """
    assert "alembic_version" in _tables(migrated_db)


def test_upgrade_head_creates_the_canonical_tables(migrated_db: Path):
    """Guards a vacuous pass: migrations that run but create nothing."""
    names = _tables(migrated_db)
    for expected in ("projects", "graphs", "simulations", "reports", "dw_runs", "dw_paths"):
        assert expected in names, f"{expected} missing from a migrated database"

    connection = sqlite3.connect(migrated_db)
    try:
        head = connection.execute("select version_num from alembic_version").fetchone()[0]
    finally:
        connection.close()
    assert head == RECORDED_HEAD, f"migrated to {head}, not the recorded head"


def test_upgrade_downgrade_round_trips(migrated_db: Path):
    """Both directions must work without credentials, or rollback is fiction."""
    down = _alembic("downgrade", "base", db=migrated_db)
    assert down.returncode == 0, f"stdout:\n{down.stdout}\nstderr:\n{down.stderr}"

    up = _alembic("upgrade", "head", db=migrated_db)
    assert up.returncode == 0, f"stdout:\n{up.stdout}\nstderr:\n{up.stderr}"
    assert "dw_paths" in _tables(migrated_db)


def test_autogenerate_is_refused_and_writes_nothing(migrated_db: Path):
    """Regression test for defect 2 -- the destructive one.

    Before the fix this exited 0, reported success, and left behind a revision
    whose `upgrade()` dropped every table in the database.
    """
    before = sorted(path.name for path in VERSIONS.glob("*.py"))

    result = _alembic(
        "revision", "--autogenerate", "-m", "must-be-refused", db=migrated_db
    )
    after = sorted(path.name for path in VERSIONS.glob("*.py"))

    assert result.returncode != 0, (
        "alembic revision --autogenerate succeeded. Under ADR-0013 the ORM "
        "metadata is empty, so the generated revision drops all 16 canonical "
        "tables."
    )
    assert after == before, f"a migration was written anyway: {set(after) - set(before)}"

    combined = result.stdout + result.stderr
    assert "disabled on purpose" in combined
    assert "hand-write" in combined or "hand write" in combined
    # The headline must be the real cause. Surfacing the credential gate first
    # sends the operator looking in entirely the wrong place. Compared with a
    # guard for the other ordering, because `find` returns -1 when absent and
    # that would otherwise fail this assertion for the wrong reason.
    assert combined.find("disabled on purpose") < combined.find("SECRET_KEY", 0, combined.find("SECRET_KEY") + 1) or "SECRET_KEY" not in combined


def test_env_py_does_not_import_app_at_module_scope():
    """Static guard for the same root cause.

    Hoisting the `app.db.schema` import back to the top of `env.py` would
    reinstate the credential dependency for every migration command, and the
    only symptom is a failure on a deploy machine.
    """
    source = (BACKEND / "migrations" / "env.py").read_text(encoding="utf-8")

    # Only COLUMN-ZERO imports are module scope. The lazy `from app.db...`
    # inside `_load_target_metadata()` is indented and is the point of the fix.
    module_level = [
        line
        for line in source.splitlines()
        if line.startswith(("import ", "from ")) and "app.db" in line
    ]
    assert module_level == [], (
        "migrations/env.py imports app.* at module scope: "
        f"{module_level}. That executes app/__init__.py and its credential "
        "gate, so migrations would require production secrets."
    )
    # And the lazy import has to still exist, or the metadata is never loaded
    # and autogenerate would be refused for the wrong reason even after someone
    # legitimately re-adds ORM declarations.
    assert "def _load_target_metadata" in source


def test_alembic_is_invoked_by_a_deploy_path():
    """Gate 3 is not closed until something actually runs the migrations.

    Schema creation being a manual step that no automation performs is the
    other open half of exec-plan 08 fix 1.
    """
    candidates = [
        REPO_ROOT / "package.json",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "backend" / "Dockerfile",
        REPO_ROOT / "Dockerfile.worker",
        REPO_ROOT / ".github" / "workflows" / "ci.yml",
        REPO_ROOT / "scripts" / "release" / "verify",
        REPO_ROOT / "scripts" / "release" / "migrate.sh",
    ]
    checked = [
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for path in candidates
        if path.exists()
    ]
    invoked = [
        name
        for name in checked
        if "alembic" in (REPO_ROOT / name).read_text(encoding="utf-8", errors="ignore")
    ]

    assert invoked, (
        "No deploy path, CI job, or release script invokes `alembic`, so schema "
        "creation is a manual step that nothing performs. Checked: "
        + ", ".join(checked)
    )