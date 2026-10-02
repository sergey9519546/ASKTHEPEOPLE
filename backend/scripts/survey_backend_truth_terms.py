"""Survey: which backend/app/** string literals match the truth-contract TERM_PATTERNS?

Read-only. Prints every hit with its file:line so each can be reviewed and
classified by hand before any gate is written. Run from the repo root:

    python backend/scripts/survey_backend_truth_terms.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Windows consoles default to cp1252 and raise on characters like theta.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]

# Mirrors TERM_PATTERNS in tools/lint_frontend_truth.mjs. Keep the two in step;
# if one changes, change both.
TERM_PATTERNS = [
    r"predict(?:s|ed|ing|ion|ions|ive)?",
    r"forecast(?:s|ed|ing)?",
    r"consensus",
    r"probabilit(?:y|ies)",
    r"confidence",
    r"certainty",
    r"likelihood",
    r"calibrat(?:e|es|ed|ing|ion|ions)",
    r"representative",
    r"public[ -]opinion",
    r"digital twins?",
    r"majorit(?:y|ies)",
    r"minorit(?:y|ies)",
    r"popularity",
    r"perspective alignment",
    r"prevalence",
    r"population (?:estimate|measure|measurement|share)",
    r"(?:public|population|path) support",
    r"support (?:score|rate|share)",
    r"votes?",
    r"respondents?",
    r"participants?",
    r"sampl(?:e|es|ed|ing)",
    r"survey(?:s|ed|ing)?",
    r"polls?",
    r"evidence from (?:the )?graph",
    r"verified lineage",
]
COMBINED = re.compile(
    r"\b(?:" + "|".join(TERM_PATTERNS) + r")\b", re.IGNORECASE
)

NEGATION = re.compile(
    r"\b(?:not|never|no|non|0 zero|does not|must not|cannot|is not|are not|"
    r"without|nor|neither|refuses?|rejects?|forbid\w*|prohibit\w*|"
    r"unsupported|disclaim\w*|unverified)\b",
    re.IGNORECASE,
)


def string_literals(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
    return out


def main() -> int:
    targets = sorted(
        p
        for p in (REPO_ROOT / "backend" / "app").rglob("*.py")
        if "__pycache__" not in p.parts
    )
    total = 0
    with_negation = 0
    for path in targets:
        rel = path.relative_to(REPO_ROOT).as_posix()
        for lineno, text in string_literals(path):
            if not COMBINED.search(text):
                continue
            total += 1
            negated = bool(NEGATION.search(text))
            if negated:
                with_negation += 1
            flat = " ".join(text.split())
            print(f"{rel}:{lineno}\t{'NEG' if negated else 'HIT'}\t{flat[:150]}")
    print()
    print(f"string literals matching: {total}")
    print(f"  with a negation marker: {with_negation}")
    print(f"  WITHOUT negation (review each): {total - with_negation}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
