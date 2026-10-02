"""Backend truth-term policing for ``backend/app/**`` (exec-plan T16).

The frontend has a standing gate: ``tools/lint_frontend_truth.mjs`` applies
``TERM_PATTERNS`` to every ``aria-label``/``title``/``placeholder``/``alt``/
``content`` value in ``frontend/src/**`` on every ``npm test``. Until this
module existed the backend had no equivalent, so the same prohibited phrase
could be rejected in the UI and shipped in an API response, a prompt template,
or generated persona prose.

Scope, and why it is not the whole of ``backend/app/**``
--------------------------------------------------------
A naive scan of every string literal produces 194 matches, 104 of which carry
no negation marker. Those 104 were each reviewed by hand on 2026-10-02. None is
a truth-contract violation. They fall into four groups, and the allowlist below
is exactly those four groups:

1. **The DO-NOT-WIRE theta-optimization island** (~61 hits). Cites a roadmap
   archived as superseded because it fit simulated output to observed human
   behaviour. Each module already carries a DO-NOT-WIRE warning; it is dead
   code, and the honest fix is deletion, not terminology policing.
2. **Field and column names** (~14 hits). ``calibration``, ``confidence``,
   ``forecast_status``, ``human_respondents``. These are the *schema* of the
   disclosure — the value is "not calibrated". A gate that banned the column
   name would ban the disclosure.
3. **Non-claim vocabulary** (~14 hits). The verb "Poll" in an instruction
   string, route paths such as ``/export/survey``, the prospective-theory
   probability-weighting function, and generated persona prose describing a
   synthetic character's cognitive style.
4. **The prohibition list itself** (``utils/llm_client.py``), which necessarily
   spells out the phrases it bans.

Anything not in the allowlist fails. A new module that introduces an outcome
claim is therefore a test failure, which is the point.

The allowlist is keyed on whole files, not on individual literals, because each
listed file was reviewed in full. The cost is deliberate: a new legitimate
string in an allowlisted file will not be caught, and adding a file to the
allowlist is a visible, reviewable act rather than a silent one.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"
FRONTEND_LINTER = REPO_ROOT / "tools" / "lint_frontend_truth.mjs"

# Files whose every match was reviewed on 2026-10-02. Value = the reason.
ALLOWED_FILES: dict[str, str] = {
    # 1. Dead theta-optimization island, already DO-NOT-WIRE'd — the island
    # was deleted in its entirety by ADR-0014 on 2026-10-02 (learning_loop,
    # multi_objective_loss, theta_optimizer, baseline_library,
    # outcome_fetcher, first_backtest, hybrid_simulator). The 61 hits it
    # produced no longer exist, so the allowance has nothing to allow.
    "app/services/calibration_metrics.py": "dead island: Brier/ECE scoring; publishing these would assert calibration",
    "app/services/constraint_engine.py": "dead island: no production importer",
    "app/services/game_theory.py": "dead island: Nash-equilibrium maths; no production importer",
    # 2. Disclosure schema: the field names ARE the truth contract.
    "app/services/claim_boundary.py": "disclosure constant; 'calibration' is the 'NOT CALIBRATED' value",
    "app/services/export_service.py": "CSV column names carrying the disclosure",
    "app/services/report_evidence.py": "evidence field/enum names",
    "app/services/role_normalizer.py": "role-confidence enum values",
    "app/services/simulation_config_generator.py": "config field name",
    "app/services/validation_engine.py": "validation field name",
    "app/utils/response.py": "truth-metadata wrapper docstring",
    # 3. Non-claim vocabulary.
    "app/services/prospect_theory.py": "prospect-theory probability-weighting maths (ADR-0001 names this module)",
    "app/services/big_five.py": "trait-distribution docstring",
    "app/services/oasis_profile_generator.py": "generated persona prose ('a participant in social discussions')",
    "app/services/trait_behavior_projection.py": "generated persona cognitive-style prose about synthetic agents",
    "app/services/simulation_ipc.py": "'Poll command directory' uses the verb",
    "app/services/simulation_preflight.py": "preflight field name and model-sampling caveat",
    "app/services/zep_tools.py": "synthetic-perspective probe docstring",
    "app/api/templates.py": "question frames for the user; 'participants' means people the user studies",
    "app/api/graph.py": "route docstring",
    "app/api/routes/prep_routes.py": "'Poll .../prepare/status' uses the verb",
    "app/api/routes/export_routes.py": "route path literal /export/survey",
    "app/api/routes/interview_routes.py": "route docstring",
    "app/services/report_agent.py": "report-system prompts that carry the disclosure itself",
    "app/domain/decision_lens.py": "denies 'people, respondents' across a sibling clause",
    "app/api/ws.py": "WebSocket docstring; 'poll' used as a verb",
    "app/api/routes/execution_routes.py": "'for frontend polling' uses the verb",
    "app/models/task.py": "task docstring; CAS loop described as polling",
    # 4. The prohibition list itself.
    "app/utils/llm_client.py": "_TRUTH_KEYWORDS_PROHIBITED must spell out what it bans",
}


def _term_regexes() -> list[re.Pattern[str]]:
    source = FRONTEND_LINTER.read_text(encoding="utf-8")
    block = re.search(r"const TERM_PATTERNS = \[(.*?)\];", source, re.S)
    assert block, "TERM_PATTERNS not found in tools/lint_frontend_truth.mjs"
    bodies = re.findall(r"/(.*?)/[gimsuy]*", block.group(1))
    assert bodies, "TERM_PATTERNS parsed as empty"
    return [re.compile(b, re.IGNORECASE) for b in bodies]


# A literal that negates the claim it names is the truth contract doing its
# job, not a violation. These are load-bearing: claim_boundary.py spells out
# "NOT CALIBRATED", possible_path.py enumerates the terms it refuses to emit,
# and simulation.py tells the interview model its answer "is not ... a
# prediction". Banning the vocabulary in those files would ban the disclosure.
NEGATION_RE = re.compile(
    r"\b(?:not|never|no|non|zero|without|nor|neither|must not|cannot|does not|"
    r"is not|are not|refuse\w*|reject\w*|forbid\w*|prohibit\w*|unsupported|"
    r"disclaim\w*|unverified|do not|don't)\b",
    re.IGNORECASE,
)
# Window before the match in which a negation must appear to count.
NEGATION_WINDOW = 48
# Negation is judged per clause, not per literal: these are disclosure prompts
# that run for hundreds of characters, and the negation is often several
# clauses away from the term it denies ("These are descriptive calculations
# over synthetic actions only. They do not measure people, constitute external
# validation, or provide calibrated evidence."). A character window either
# misses that or fires on an unrelated negation elsewhere in the prompt.
CLAUSE_SPLIT_RE = re.compile(r"[.;:\n]|(?:\s-\s)")


def _clause_around(text: str, index: int) -> str:
    """Return the clause containing character offset `index`."""
    start = 0
    for m in CLAUSE_SPLIT_RE.finditer(text):
        if m.start() > index:
            break
        start = m.end()
    end = len(text)
    m = CLAUSE_SPLIT_RE.search(text, index)
    if m:
        end = m.start()
    return text[start:end]


def _string_literals(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover
        pytest.fail(f"{path} could not be parsed: {exc}")
    return [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _violations() -> list[str]:
    patterns = _term_regexes()
    found: list[str] = []
    for path in sorted(BACKEND_APP.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel[len("backend/"):] in ALLOWED_FILES:
            continue
        for lineno, text in _string_literals(path):
            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue
                if NEGATION_RE.search(_clause_around(text, match.start())):
                    # The clause denies the claim it names. Allowed.
                    break
                flat = " ".join(text.split())
                found.append(
                    f"{rel}:{lineno} matched {match.group(0)!r} in {flat[:120]!r}"
                )
                break
    return found


def test_term_patterns_were_parsed():
    """Guard against a rename making every check below vacuous."""
    assert len(_term_regexes()) >= 20


def test_allowlist_paths_all_exist():
    """An allowlist entry that points at nothing is a lie: it looks like the
    file was reviewed when no such file remains."""
    missing = [
        rel
        for rel in ALLOWED_FILES
        if not (BACKEND_APP.parent / rel).exists()
    ]
    assert not missing, f"allowlist names files that do not exist: {missing}"


def test_every_allowlisted_file_has_a_reason():
    assert all(reason.strip() for reason in ALLOWED_FILES.values())


def test_no_prohibited_terms_in_unreviewed_backend_modules():
    violations = _violations()
    assert not violations, (
        "Outcome-claim vocabulary found in backend modules that are not on the "
        "reviewed allowlist. If the usage is legitimate, add the file to "
        "ALLOWED_FILES with a reason; if it is a real claim, fix the string.\n"
        + "\n".join(violations)
    )
