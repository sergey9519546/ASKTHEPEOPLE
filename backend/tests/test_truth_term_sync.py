"""Truth-terminology sync between the backend and the frontend linter.

The repository has two independent lists of outcome-claim vocabulary:

* ``tools/lint_frontend_truth.mjs`` — ``TERM_PATTERNS``, 26 patterns, applied
  to ``frontend/src/**`` attribute values on every ``npm test``.
* ``backend/app/utils/llm_client.py`` — ``_TRUTH_KEYWORDS_PROHIBITED``, a
  handful of plain strings, applied to every LLM response by
  ``_audit_response``.

Nothing enforced that the two agree. They had already drifted: the frontend
caught 26 terms and the backend caught 5, so an LLM response asserting
"calibrated" or "representative" or "survey" passed the backend audit and was
rejected by the frontend linter. These tests fail the moment that drift
returns.

The backend's list is intentionally a strict subset. It is not widened here:
a term the backend does not yet police is a gap to close deliberately, not one
to paper over by copying a regex into a string tuple. This module asserts
*coverage*, not equality.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_LINTER = REPO_ROOT / "tools" / "lint_frontend_truth.mjs"
LLM_CLIENT = REPO_ROOT / "backend" / "app" / "utils" / "llm_client.py"
CLAIM_BOUNDARY = REPO_ROOT / "backend" / "app" / "services" / "claim_boundary.py"

# The five Truth Rail facts from tools/lint_frontend_truth.mjs, paired with the
# backend disclosure that carries the same claim. Each backend value must
# appear in GENERATED_OUTPUT_DISCLOSURE_TEXT.
RAIL_TO_BACKEND_DISCLOSURE = {
    "HUMAN RESPONDENTS: 0": "0 HUMAN RESPONDENTS",
    "NOT A FORECAST": "NOT A FORECAST",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontend_term_regexes() -> list[re.Pattern[str]]:
    """Compile the JS linter's TERM_PATTERNS as Python regexes.

    These patterns are plain word-boundary plus optional-suffix forms with no
    lookbehind or named groups, so the syntax is identical in both engines and
    an exact match test is available. Testing the real pattern beats matching
    on a prefix: ``\\bpolls?\\b`` does not match "polling", which a
    string-prefix comparison would have wrongly called covered.
    """
    source = _read(FRONTEND_LINTER)
    block = re.search(r"const TERM_PATTERNS = \[(.*?)\];", source, re.S)
    assert block, "TERM_PATTERNS not found in tools/lint_frontend_truth.mjs"
    bodies = re.findall(r"/(.*?)/[gimsuy]*", block.group(1))
    assert bodies, "TERM_PATTERNS parsed as empty"
    return [re.compile(body, re.IGNORECASE) for body in bodies]


def _backend_prohibited_terms() -> list[str]:
    source = _read(LLM_CLIENT)
    block = re.search(
        r"_TRUTH_KEYWORDS_PROHIBITED = \((.*?)\n\)", source, re.S
    )
    assert block, "_TRUTH_KEYWORDS_PROHIBITED not found in llm_client.py"
    return re.findall(r'"([^"]+)"', block.group(1))


def _backend_disclosure_text() -> str:
    source = _read(CLAIM_BOUNDARY)
    block = re.search(
        r"GENERATED_OUTPUT_DISCLOSURE_TEXT = \((.*?)\n\)", source, re.S
    )
    assert block, "GENERATED_OUTPUT_DISCLOSURE_TEXT not found in claim_boundary.py"
    return " ".join(re.findall(r'"([^"]*)"', block.group(1)))


def test_frontend_linter_has_term_patterns():
    """Guard the parser itself: if TERM_PATTERNS is renamed or emptied this
    module would otherwise pass vacuously."""
    assert len(_frontend_term_regexes()) >= 20


def test_backend_prohibited_terms_are_non_empty():
    assert _backend_prohibited_terms(), "backend prohibited list is empty"


@pytest.mark.parametrize("term", _backend_prohibited_terms())
def test_backend_prohibited_term_is_caught_by_frontend(term: str):
    """Every term the backend polices must also be caught by the frontend
    linter. If the frontend pattern does not match the term, the same text is
    rejected in an LLM response and accepted in the UI, which is the opposite
    of a single consistent truth contract.
    """
    patterns = _frontend_term_regexes()
    assert any(p.search(term) for p in patterns), (
        f"backend prohibits {term!r} but no frontend TERM_PATTERN matches it; "
        f"the two lists have drifted"
    )


def test_backend_disclosure_carries_the_rail_facts():
    disclosure = _backend_disclosure_text().upper()
    for rail_fact, backend_text in RAIL_TO_BACKEND_DISCLOSURE.items():
        assert backend_text.upper() in disclosure, (
            f"{rail_fact} has no counterpart in "
            f"claim_boundary.GENERATED_OUTPUT_DISCLOSURE_TEXT"
        )


def test_backend_disclosure_negates_every_outcome_claim():
    """The disclosure is a list of disclaimers, so each claim word must be
    governed by a negation. A bare 'CALIBRATED' would assert the opposite of
    what the product guarantees. The negation is searched over the preceding
    few words because the real strings interleave an article ("NOT A
    FORECAST") and a separator ("·")."""
    disclosure = _backend_disclosure_text().upper()
    claims = ("CALIBRATED", "PUBLIC OPINION", "CAUSAL ESTIMATE", "FORECAST")
    negation = re.compile(r"\b(?:NOT|NO|NEVER|0)\b")
    for claim in claims:
        assert claim in disclosure, f"{claim!r} missing from the disclosure"
        for match in re.finditer(re.escape(claim), disclosure):
            window = disclosure[max(0, match.start() - 24) : match.start()]
            assert negation.search(window), (
                f"{claim!r} in the disclosure is not negated; "
                f"context was ...{window!r}"
            )
