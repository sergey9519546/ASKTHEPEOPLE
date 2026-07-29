#!/usr/bin/env python3
"""Dependency-free structural validation for the ASKTHEPEOPLE docs package."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED = [
    "docs/README.md",
    "docs/SOURCES.md",
    "docs/product/PRODUCT_TRUTH_CONTRACT.md",
    "docs/product/METHODOLOGY.md",
    "docs/product/USE_POLICY.md",
    "docs/product/TERMINOLOGY.md",
    "docs/product/SUCCESS_METRICS.md",
    "docs/design/DIRECTION_C.md",
    "docs/design/ROUTE_GRAMMAR.md",
    "docs/design/ACCESSIBILITY.md",
    "docs/design/CONTENT_SYSTEM.md",
    "docs/design/assets/ASKTHEPEOPLE_Civic_Wayfinding_Reference.png",
    "docs/architecture/index.md",
    "docs/architecture/data-model.md",
    "docs/architecture/state-machines.md",
    "docs/architecture/adr/README.md",
    "docs/ai/PROMPT_REGISTRY.md",
    "docs/ai/EVALS.md",
    "docs/ai/MODEL_RELEASES.md",
    "docs/ai/FAILURE_MODES.md",
    "docs/security/THREAT_MODEL.md",
    "docs/security/SOURCE_INGESTION.md",
    "docs/security/INCIDENT_RESPONSE.md",
    "docs/privacy/DATA_MAP.md",
    "docs/privacy/RETENTION.md",
    "docs/privacy/SUBPROCESSORS.md",
    "docs/exec-plans/README.md",
    "docs/release/ACCEPTANCE.md",
    "docs/release/RUNBOOK.md",
]

PLACEHOLDER_RE = re.compile(
    r"(?m)^\s*(?:[-*]\s*)?(?:TODO|FIXME|XXX)(?:\s*:|\s*$)|lorem ipsum|<\s*(your|insert)[^>]*>",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\](?!:)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:", re.MULTILINE)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            fail(errors, f"missing required path: {rel}")

    # Scope structural checks to the doc system. The repository also contains
    # many .md files outside docs/ (legacy audits, .agents notes, vendor
    # READMEs inside node_modules and .venv, generated source-extraction
    # markdown, etc.) that the doc validator must not police. The
    # docs/archive/ subtree is excluded as well — it is "retained for audit
    # only" per docs/README.md and is not subject to the normative rules.
    markdown_files = sorted(
        p for p in DOCS.rglob("*.md")
        if not any(part == "archive" for part in p.relative_to(DOCS).parts)
    )
    for path in markdown_files:
        rel = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            fail(errors, f"not UTF-8: {rel}: {exc}")
            continue

        # Normative docs under docs/ use machine-readable ownership metadata.
        if DOCS in path.parents:
            if not text.startswith("---\n"):
                fail(errors, f"missing YAML front matter: {rel}")
            else:
                end = text.find("\n---\n", 4)
                if end == -1:
                    fail(errors, f"unclosed YAML front matter: {rel}")
                else:
                    front = text[4:end]
                    for field in ("title:", "status:", "version:", "owner:", "last_reviewed:"):
                        if field not in front:
                            fail(errors, f"front matter missing {field} in {rel}")

        # Ignore fenced code when checking heading structure.
        in_code = False
        headings: list[tuple[int, int, str]] = []
        fences = 0
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.startswith("```") or line.startswith("~~~"):
                in_code = not in_code
                fences += 1
                continue
            if in_code:
                continue
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                headings.append((line_no, len(match.group(1)), match.group(2)))
        if fences % 2:
            fail(errors, f"unbalanced fenced code block: {rel}")
        h1s = [h for h in headings if h[1] == 1]
        # The integrated GODMODE plan is intentionally a book-like master file
        # with multiple Part-level H1 headings. Normative modular docs use one H1.
        if path.name != "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md" and len(h1s) != 1:
            fail(errors, f"expected exactly one H1 in {rel}; found {len(h1s)}")
        previous = 0
        for line_no, level, title in headings:
            if previous and level > previous + 1:
                fail(errors, f"heading jump H{previous}->H{level}: {rel}:{line_no} {title}")
            previous = level

        for match in PLACEHOLDER_RE.finditer(text):
            fail(errors, f"placeholder token in {rel}: {match.group(0)!r}")

        refs = set(FOOTNOTE_REF_RE.findall(text))
        defs = set(FOOTNOTE_DEF_RE.findall(text))
        for name in sorted(refs - defs):
            fail(errors, f"undefined footnote [^{name}] in {rel}")
        for name in sorted(defs - refs):
            warnings.append(f"unused footnote [^{name}] in {rel}")

        for match in LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            # Strip optional Markdown title: path "title".
            target = raw_target.split(" ", 1)[0].strip("<>")
            if not target or target.startswith(("#", "https://", "http://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0])
            # Strip a `:line` or `:line-line` suffix (GitHub-style code
            # references like `../../backend/app/foo.py:25-30`). URLs have
            # already been filtered out above, so splitting on `:` is safe
            # for relative paths here.
            if ":" in target:
                target = target.split(":", 1)[0]
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(errors, f"relative link escapes package: {rel} -> {raw_target}")
                continue
            if not resolved.exists():
                fail(errors, f"broken relative link: {rel} -> {raw_target}")

    # ADR numbers and index completeness.
    adr_files = sorted((DOCS / "architecture" / "adr").glob("ADR-*.md"))
    numbers: dict[str, Path] = {}
    index_text = (DOCS / "architecture" / "adr" / "README.md").read_text(encoding="utf-8")
    for path in adr_files:
        match = re.match(r"ADR-(\d{4})-", path.name)
        if not match:
            fail(errors, f"malformed ADR filename: {path.name}")
            continue
        number = match.group(1)
        if number in numbers:
            fail(errors, f"duplicate ADR number {number}: {numbers[number].name}, {path.name}")
        numbers[number] = path
        if path.name not in index_text:
            fail(errors, f"ADR missing from index: {path.name}")

    # Critical truth strings must remain in the authority documents.
    truth = (DOCS / "product" / "PRODUCT_TRUTH_CONTRACT.md").read_text(encoding="utf-8")
    method = (DOCS / "product" / "METHODOLOGY.md").read_text(encoding="utf-8")
    truth_requirements = {
        "zero-human disclosure": ("0 human respondents", "human respondents: 0", "human_respondent_count"),
        "forecast boundary": ("not a forecast",),
        "machine-readable origin": ("output_origin",),
        "external human evidence origin": ("external_human_evidence",),
        "source-role boundary": ("source material shapes starting conditions",),
    }
    truth_lower = truth.lower()
    for label, variants in truth_requirements.items():
        if not any(variant in truth_lower for variant in variants):
            fail(errors, f"critical truth requirement missing: {label}")
    for phrase in (
        "not a synthetic survey",
        "External validity",
        "disconfirming",
        "Human-validation handoff",
    ):
        if phrase.lower() not in method.lower():
            fail(errors, f"critical methodology phrase missing: {phrase}")

    total_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in markdown_files)
    total_words = sum(len(p.read_text(encoding="utf-8").split()) for p in markdown_files)
    print(f"Markdown files: {len(markdown_files)}")
    print(f"ADR files: {len(adr_files)}")
    print(f"Lines: {total_lines}")
    print(f"Words: {total_words}")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print(f"Errors: {len(errors)}", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Errors: 0")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
