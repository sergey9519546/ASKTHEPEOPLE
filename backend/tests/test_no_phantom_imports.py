"""No module may import a module that does not exist (exec-plan hygiene).

This bug class had no detection at the time it was found. Two instances were
located by hand while working on the schema divergence —
`backend/scripts/migrate_json_to_postgres.py` imported `app.db.database`, and
`backend/app/optimization/learning_loop.py` imported `app.db.models`; neither
target ever existed, and both would fail with a bare `ModuleNotFoundError` far
from the cause if executed. Both files were deleted in ADR-0014 (the second
was part of the dead theta-optimization island and carried a DO-NOT-WIRE
warning citing an archived roadmap), so the allowance map below is empty and
is kept in place to guard the pattern, not to grandfather anyone.

The check is **static**: it parses each file's AST and resolves every absolute
`app.*` import against the filesystem. Importing every module for real would
be a stronger check but would execute Celery app construction, database engine
creation, and other import-time side effects, which makes such a test
order-dependent and environment-sensitive.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
APP_PACKAGE = BACKEND_ROOT / "app"

# Files allowed to import a module that does not exist, with the reason.
#
# Empty since ADR-0014: both predecessors of this map (the broken one-shot
# migration script and the dead optimization island) were deleted rather than
# allowed indefinitely. The map stays so the mechanism remains visible and so
# the staleness guard below has something to iterate.
KNOWN_UNRESOLVED: dict[str, str] = {}


def _module_exists(dotted: str) -> bool:
    """True if `app.some.module` resolves to a file or package on disk."""
    parts = dotted.split(".")
    if parts[0] != "app":
        # Only `app.*` is resolvable relative to BACKEND_ROOT.
        return True
    base = BACKEND_ROOT.joinpath(*parts)
    return base.with_suffix(".py").is_file() or (
        base.is_dir() and (base / "__init__.py").is_file()
    )


def _absolute_imports(path: Path) -> list[str]:
    """Every `from app... import ...` target in the file.

    Relative imports are skipped: they are resolved by the module system at
    runtime and cannot be checked this way without executing the package.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover
        pytest.fail(f"{path} could not be parsed: {exc}")
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative
            if node.module and node.module.split(".")[0] == "app":
                found.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "app":
                    found.append(alias.name)
    return found


def _scan_targets() -> list[tuple[Path, list[str]]]:
    targets = sorted(APP_PACKAGE.rglob("*.py")) + sorted(
        (BACKEND_ROOT / "scripts").glob("*.py")
    )
    return [(p, _absolute_imports(p)) for p in targets if "__pycache__" not in p.parts]


def test_scanner_found_modules():
    """Guard against a silently broken scanner. If parsing regressed, every
    other assertion here would pass vacuously."""
    scanned = _scan_targets()
    assert len(scanned) > 100, f"only scanned {len(scanned)} files"
    assert any(imports for _, imports in scanned), "no imports were extracted"


def test_no_module_imports_a_module_that_does_not_exist():
    """The check. Every `app.*` import must resolve on disk, outside the
    recorded allowances.

    `test_known_unresolved_allowlist_is_not_stale` keeps those allowances from
    outliving the problem, so tolerating them here cannot silently become
    tolerating anything.
    """
    problems: list[str] = []
    for path, imports in _scan_targets():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in KNOWN_UNRESOLVED:
            continue
        for dotted in imports:
            if _module_exists(dotted):
                continue
            problems.append(f"{rel} imports {dotted}, which does not exist")
    assert not problems, (
        "module(s) import a target that does not exist; each fails with a bare "
        "ModuleNotFoundError far from the cause:\n" + "\n".join(problems)
    )


def test_known_unresolved_allowlist_is_not_stale():
    """If a file is deleted or repaired, its allowance must be removed rather
    than left to imply a problem that no longer exists."""
    stale: list[str] = []
    for rel in KNOWN_UNRESOLVED:
        if not (REPO_ROOT / rel).is_file():
            stale.append(f"{rel} no longer exists; remove it from KNOWN_UNRESOLVED")
            continue
        path = REPO_ROOT / rel
        if all(_module_exists(d) for d in _absolute_imports(path)):
            stale.append(
                f"{rel} no longer imports a missing module; remove it from "
                "KNOWN_UNRESOLVED"
            )
    assert not stale, "\n".join(stale)


def test_known_unresolved_entries_have_reasons():
    assert all(reason.strip() for reason in KNOWN_UNRESOLVED.values())


def test_app_package_root_exists():
    """The resolution anchor. If this moves, every check above is meaningless."""
    assert (APP_PACKAGE / "__init__.py").is_file()