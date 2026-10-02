"""Pin the stub-audit invariant for ``backend/app/**``.

A scan on 2026-10-02 found 59 bare ``pass`` statements in ``backend/app/**``.
Every one was read in context and classified. None was an unfinished
implementation, so **this audit introduced zero ``raise NotImplementedError``
conversions** -- there were no abstract base contracts to convert. That is
asserted below rather than asserted in prose:

* ``test_no_stub_shaped_method_bodies`` fails if any method body is nothing but
  ``pass`` or ``...`` outside a ``typing.Protocol`` interface, which is the
  shape an abandoned implementation takes.
* ``test_not_implemented_error_only_inside_declared_abstract_contracts`` fails
  if a ``raise NotImplementedError`` appears anywhere that does not also declare
  the abstract contract it belongs to, so a future stub cannot be made "loud"
  without saying what must implement it.

What the review did produce was the rule this module enforces:

    a bare ``pass`` in ``backend/app/**`` must carry a trailing comment stating
    why the no-op is correct and under what condition it is reached.

An unexplained ``pass`` is a defect: a reader cannot distinguish a deliberate
best-effort swallow from an abandoned implementation. An explained one is a
design note. All 59 sites satisfy the rule, so the allowlist is empty -- it
exists so that the next unavoidable exception is a visible, reviewable act with
a written reason rather than a silent regression.

The pass scan is text-level rather than AST-level on purpose: a ``pass`` inside
an ``except`` block is the overwhelming majority of these sites and the only
place a silent swallow can hide, and reading it as text also catches a ``pass``
that is the entire body of an ``if`` used for readability.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"

# Bare ``pass`` sites permitted without a trailing rationale, keyed by
# "<repo-relative posix path>:<line>" with the reason as the value.
#
# Empty, and expected to stay empty. Of the 59 sites found by the 2026-10-02
# audit, 53 carried no rationale at all -- the defect class this module exists
# for -- and 6 had a rationale on the preceding comment line but not on the
# ``pass`` line itself, which left the rule unenforceable by a scan.
#
# A new entry must name a condition a reader can check. "Best effort" or "not
# applicable" is not a reason and will be rejected in review.
ALLOWED_UNEXPLAINED_PASS: dict[str, str] = {}

# ``pass``, optionally followed by a trailing comment. ``\b`` keeps this from
# matching identifiers that merely start with "pass".
_PASS_STATEMENT_RE = re.compile(r"^pass\b(.*)$")


def _app_sources() -> list[Path]:
    return [
        path
        for path in sorted(BACKEND_APP.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _is_pass_statement(line: str) -> bool:
    """True when the line's only statement is ``pass`` (comment allowed)."""
    match = _PASS_STATEMENT_RE.match(line.strip())
    if not match:
        return False
    remainder = match.group(1).strip()
    return remainder == "" or remainder.startswith("#")


def _carries_rationale(line: str) -> bool:
    match = _PASS_STATEMENT_RE.match(line.strip())
    return bool(match) and match.group(1).strip().startswith("#")


def _unexplained_passes(sources: list[tuple[Path, list[str]]]) -> list[str]:
    """Return one ``file:line`` string per ``pass`` with no trailing rationale."""
    found: list[str] = []
    for path, lines in sources:
        for number, line in enumerate(lines, 1):
            if not _is_pass_statement(line):
                continue
            if _carries_rationale(line):
                continue
            if f"{_rel(path)}:{number}" in ALLOWED_UNEXPLAINED_PASS:
                continue
            found.append(f"{_rel(path)}:{number}")
    return found


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()



def _tree(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover
        raise AssertionError(f"{_rel(path)} could not be parsed: {exc}") from exc


def _parents(tree: ast.AST) -> dict[int, ast.AST]:
    return {
        id(child): node
        for node in ast.walk(tree)
        for child in ast.iter_child_nodes(node)
    }


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _is_interface_class(node: ast.ClassDef) -> bool:
    """A declared abstract or structural contract, not a silent no-op holder."""
    return bool(_base_names(node) & {"ABC", "ABCMeta", "Protocol"})


def _has_abstract_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        "abstractmethod" in ast.unparse(decorator)
        for decorator in node.decorator_list
    )


def _declared_abstract(
    tree: ast.AST,
    node: ast.AST,
    parents: dict[int, ast.AST],
) -> bool:
    """True when ``node`` sits under a declared abstract/structural contract."""
    cursor = parents.get(id(node))
    while cursor is not None:
        if isinstance(cursor, ast.ClassDef) and _is_interface_class(cursor):
            return True
        cursor = parents.get(id(cursor))
    return False


def _function_is_stub_shaped(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = node.body
    if len(body) != 1:
        return False
    only = body[0]
    if isinstance(only, ast.Pass):
        return True
    return (
        isinstance(only, ast.Expr)
        and isinstance(only.value, ast.Constant)
        and only.value.value is Ellipsis
    )


def test_allowlist_entries_all_carry_a_checkable_reason():
    assert all(
        len(reason.strip()) >= 20 for reason in ALLOWED_UNEXPLAINED_PASS.values()
    )


def test_allowlist_entries_point_at_real_bare_pass_sites():
    """An allowlist key that no longer names a ``pass`` is stale, and a stale
    entry silently exempts whatever takes its place."""
    indexed = {
        f"{_rel(path)}:{number}"
        for path in _app_sources()
        for number, line in enumerate(_read(path), 1)
        if _is_pass_statement(line)
    }
    stale = sorted(set(ALLOWED_UNEXPLAINED_PASS) - indexed)
    assert not stale, f"ALLOWED_UNEXPLAINED_PASS names no pass statement: {stale}"


def test_no_unexplained_bare_pass_in_backend_app():
    violations = _unexplained_passes([(path, _read(path)) for path in _app_sources()])
    assert not violations, (
        "A bare `pass` in backend/app/** carries no trailing comment saying why "
        "the no-op is correct. Either the implementation is unfinished -- in "
        "which case implement it, or make the method raise "
        "NotImplementedError naming the subclass that must do so -- or the "
        "no-op is deliberate, in which case say so on the same line. Do not "
        "suppress this with an ALLOWED_UNEXPLAINED_PASS entry that no reader "
        "could check.\n" + "\n".join(violations)
    )


def test_the_scan_actually_detects_an_unexplained_pass():
    """Guard against the rule passing because the scan sees nothing."""
    probe = (REPO_ROOT / "backend" / "app" / "probe.py", ["def f():", "    try:", "        pass"])
    assert _unexplained_passes([probe]) == ["backend/app/probe.py:3"]
    annotated = (probe[0], ["def f():", "    try:", "        pass  # best effort"])
    assert _unexplained_passes([annotated]) == []
    assert not _is_pass_statement("    passenger = 1")


def test_pass_statements_are_still_present_to_scan():
    """The audit annotated 59 sites. If that count collapses, the rule above has
    lost its subject and is weaker than it reads."""
    total = sum(
        1 for path in _app_sources() for line in _read(path) if _is_pass_statement(line)
    )
    assert total >= 40, (
        f"only {total} pass statements remain in backend/app/**; the 2026-10-02 "
        "audit annotated 59. Investigate before accepting a drop."
    )


def test_no_stub_shaped_method_bodies():
    """A method whose whole body is ``pass``/``...`` outside a declared
    interface is an abstract contract with no base class, i.e. a silent no-op.
    There are no ABCs in this codebase, so introducing one without
    ``raise NotImplementedError`` reintroduces the defect this audit removed."""
    offenders: list[str] = []
    for path in _app_sources():
        tree = _tree(path)
        parents = _parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _function_is_stub_shaped(node):
                continue
            if _declared_abstract(tree, node, parents):
                continue
            if _has_abstract_decorator(node):
                continue
            offenders.append(f"{_rel(path)}:{node.lineno} {node.name}")
    assert not offenders, (
        "Stub-shaped method bodies outside a declared interface (ABC, Protocol, "
        "or @abstractmethod). Give them a body, or make them raise "
        "NotImplementedError naming the required implementation.\n"
        + "\n".join(offenders)
    )


def test_not_implemented_error_only_inside_declared_abstract_contracts():
    """This audit converted no stub to ``raise NotImplementedError`` because none
    qualified. Any such raise added later must arrive with the contract it
    belongs to, so a caller gets a loud failure naming what to implement rather
    than a bare no-op."""
    offenders: list[str] = []
    for path in _app_sources():
        tree = _tree(path)
        parents = _parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            rendered = ast.unparse(node.exc)
            if "NotImplementedError" not in rendered:
                continue
            if _declared_abstract(tree, node, parents):
                continue
            offenders.append(f"{_rel(path)}:{node.lineno} {rendered}")
    assert not offenders, (
        "raise NotImplementedError outside a declared abstract contract (an "
        "@abstractmethod method, or a class deriving ABC/Protocol). Without "
        "one it is indistinguishable from a stub.\n" + "\n".join(offenders)
    )


def test_no_disabled_conditional_blocks():
    """``if False:`` / ``if True:`` bodies are unreachable code that reads like
    live behaviour. Parsed as AST so a mention inside a docstring or prompt
    template does not trip this. ``while True:`` is excluded: a bounded retry
    or pagination loop is the idiom, not a disable switch."""
    offenders: list[str] = []
    for path in _app_sources():
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if isinstance(test, ast.Constant) and isinstance(test.value, bool):
                offenders.append(f"{_rel(path)}:{node.lineno} if {test.value}")
    assert not offenders, (
        "Constant-boolean `if` used as a disable switch.\n" + "\n".join(offenders)
    )


# Rationale pins. Keyed on a unique anchor line rather than a line number, so a
# refactor above the site does not invalidate them, and deliberately limited to
# the sites whose no-op a reader could plausibly mistake for a defect without
# having read the audit.
_RATIONALE_PINS: list[tuple[str, str, str]] = [
    ("backend/app/__init__.py", "with engine.connect():", "reachability probe"),
    (
        "backend/app/services/simulation_runtime_contract.py",
        "elif event_type in PERSONA_EVENT_TYPES:",
        "persona events were already applied",
    ),
    (
        "backend/app/services/simulation_runner.py",
        "os.unlink(temp_file)",
        "best-effort cleanup",
    ),
]


def _pass_statements_within(path: Path, anchor: str, window: int) -> list[str]:
    lines = _read(path)
    hits = [n for n, line in enumerate(lines) if anchor in line]
    assert len(hits) == 1, (
        f"{_rel(path)}: anchor {anchor!r} matched {len(hits)} lines, expected 1"
    )
    return [
        line
        for line in lines[hits[0] : hits[0] + window]
        if _is_pass_statement(line)
    ]


@pytest.mark.parametrize(
    ("rel_path", "anchor", "expected_fragment"),
    _RATIONALE_PINS,
    ids=[f"{pin[0].rsplit('/', 1)[-1]}:{pin[1][:20]}" for pin in _RATIONALE_PINS],
)
def test_key_no_op_sites_keep_their_rationale(rel_path, anchor, expected_fragment):
    path = REPO_ROOT / rel_path
    found = _pass_statements_within(path, anchor, window=8)
    assert found, f"expected a pass statement near {anchor!r} in {rel_path}"
    assert any(expected_fragment in line for line in found), (
        f"{rel_path}: the pass near {anchor!r} lost the rationale mentioning "
        f"{expected_fragment!r}"
    )