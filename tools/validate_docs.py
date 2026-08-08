#!/usr/bin/env python3
"""Dependency-free structural validation for the ASKTHEPEOPLE docs package.

This validator extends the upstream `validate_docs.py` from the 2026-07-29
documentation system package with three project-specific changes:

1. **Scope to ``docs/`` only.** The original walks the whole repo; this
   copy is restricted to ``docs/`` so it cannot fire on the package
   metadata files at the repo root (``ASKTHEPEOPLE_GODMODE_BUILDPLAN.md``,
   ``INTEGRATION_GUIDE.md``, ``MANIFEST.md``, ``VALIDATION_REPORT.md``,
   ``CHECKSUMS.sha256``, ``TREE.txt``), which describe the package as
   frozen on 2026-07-29 and are referenced, not edited.

2. **Exclude ``archive/`` from front-matter and heading-jump checks.**
   ``docs/archive/legacy-2026-07-29/`` holds the prior flat-file docs
   that were archived during the doc-system integration. The original
   docs did not all carry the new front-matter or single-H1 contract,
   and the archive's job is to preserve history, not to comply with the
   new contract. A path that contains ``/archive/`` or starts with
   ``archive/`` is skipped from structural checks.

3. **Allow GitHub-style ``file:line`` link suffixes.** The original
   validator checked that every internal ``file`` link target exists;
   the new docs add ``:line`` references into ``backend/app/`` and
   ``docs/`` for traceability. The validator strips an optional
   ``:digits`` suffix before resolving the target.
"""
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


def fenced_lines_after(text: str, marker: str) -> tuple[str, ...]:
    """Return stripped non-empty lines in the first text fence after marker."""
    marker_at = text.find(marker)
    if marker_at == -1:
        return ()
    fence_at = text.find("```text\n", marker_at)
    if fence_at == -1:
        return ()
    content_at = fence_at + len("```text\n")
    fence_end = text.find("\n```", content_at)
    if fence_end == -1:
        return ()
    return tuple(line.strip() for line in text[content_at:fence_end].splitlines() if line.strip())


def mermaid_edges_after(text: str, marker: str) -> tuple[tuple[str, str], ...]:
    """Return ordered uppercase state edges in the first Mermaid fence."""
    marker_at = text.find(marker)
    if marker_at == -1:
        return ()
    fence_at = text.find("```mermaid\n", marker_at)
    if fence_at == -1:
        return ()
    content_at = fence_at + len("```mermaid\n")
    fence_end = text.find("\n```", content_at)
    if fence_end == -1:
        return ()
    return tuple(
        (match.group(1), match.group(2))
        for match in re.finditer(
            r"(?m)^\s*([A-Z][A-Z_]*)\s+-->\s+([A-Z][A-Z_]*)\b",
            text[content_at:fence_end],
        )
    )


def text_between(text: str, start_marker: str, end_marker: str) -> str:
    """Return a bounded document section, or an empty string if malformed."""
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        return ""
    return text[start:end]


def normalized_prose(text: str) -> str:
    """Collapse Markdown wrapping so prose locks are line-ending agnostic."""
    return re.sub(r"\s+", " ", text).strip()


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

    # Combined 2026-08-08 authority packet. These checks deliberately lock the
    # exact tenant boundary, provenance grammar, source graph, path-review
    # interpretation, comparison cardinality, and deferred-release boundary.
    authority_paths = {
        "truth": DOCS / "product" / "PRODUCT_TRUTH_CONTRACT.md",
        "data": DOCS / "architecture" / "data-model.md",
        "states": DOCS / "architecture" / "state-machines.md",
        "tenant_adr": DOCS / "architecture" / "adr" / "ADR-0009-multi-tenant-isolation.md",
        "persistence_adr": DOCS / "architecture" / "adr" / "ADR-0012-canonical-transactional-and-object-persistence.md",
        "privacy": DOCS / "privacy" / "DATA_MAP.md",
        "runbook": DOCS / "release" / "RUNBOOK.md",
        "acceptance": DOCS / "release" / "ACCEPTANCE.md",
        "design": DOCS / "superpowers" / "specs" / "2026-08-08-decision-chamber-experience-design.md",
    }
    authority = {
        name: path.read_text(encoding="utf-8") for name, path in authority_paths.items()
    }

    required_authority_fragments = {
        "truth": (
            "epistemic-ledger/v2",
            "Revision\ntraceability is never evidence.",
            "External-human-evidence relations and decision-owner-conclusion lineage are\n"
            "deferred to a later, separately reviewed contract version.",
        ),
        "data": (
            "`organization -> workspace -> project`",
            "RFC 9562 UUIDv7",
            "There is no dual-write mode.",
            "no canonical read or write\nfalls back to SQLite, filesystem JSON, Redis state",
        ),
        "states": (
            "`FAILED` is operational",
            "Every state except\n`DELETION_PENDING` and `DELETED` may enter `DELETION_PENDING`",
            "The run remains exactly `VALIDATING_OUTPUT`",
            "exact current\npath-set ID and SHA-256",
        ),
        "tenant_adr": (
            "`organization -> workspace -> project`",
            "immutable `ActorContext`",
            "enabled and forced",
        ),
        "persistence_adr": (
            "explicitly qualified PostgreSQL `core`\n  schema",
            "There is no dual-write mode.",
            "never\n  reads or writes SQLite, filesystem, Redis, or another legacy store",
        ),
        "privacy": (
            "Identity subject",
            "Organization membership",
            "Workspace membership",
            "Backfill batch/binding",
        ),
        "runbook": (
            "Railway remains the canonical deployment host",
            "comparison code performs zero writes",
            "A database outage in\ncanonical mode is an availability incident, not permission to fall back.",
        ),
        "acceptance": (
            "## Authority-packet acceptance",
            "The later comparison\n  contract accepts exactly two completed related runs",
            "Changed-condition injection, advanced intervention, external-human-\n  evidence import",
        ),
        "design": (
            "accepts **exactly two** completed related runs",
            "Viewport size never changes that cardinality.",
            "Changed-condition injection is not part of the first vertical slices.",
            "decision-owner conclusion and external-human-evidence import are later\nreleases",
        ),
    }
    for name, fragments in required_authority_fragments.items():
        for fragment in fragments:
            if fragment not in authority[name]:
                fail(
                    errors,
                    f"authority packet lock missing in {authority_paths[name].relative_to(ROOT)}: {fragment!r}",
                )

    version_locks = {
        "truth": 'version: "1.2.0"',
        "data": 'version: "1.2.0"',
        "states": 'version: "1.2.0"',
        "tenant_adr": 'version: "1.2.0"',
        "persistence_adr": 'version: "1.2.0"',
        "privacy": 'version: "1.2.0"',
        "runbook": 'version: "1.2.0"',
        "acceptance": 'version: "1.2.0"',
        "design": 'version: "1.0.2"',
    }
    for name, version in version_locks.items():
        if version not in authority[name].split("---", 2)[1]:
            fail(errors, f"authority packet version lock missing: {name} {version}")

    expected_core_tables = (
        "organizations", "users", "identity_subjects", "workspaces",
        "organization_memberships", "workspace_memberships", "projects",
        "schema_adoptions", "backfill_batches", "legacy_project_bindings",
        "persistence_cutovers", "audit_events",
    )
    core_tables = fenced_lines_after(
        authority["data"], "The TARGET canonical foundation lives in an explicitly qualified PostgreSQL"
    )
    if core_tables != expected_core_tables:
        fail(errors, f"canonical core foundation table set changed: {core_tables!r}")

    expected_roles = (
        "USER_STATEMENT", "DECISION", "SCOPE_CONSTRAINT", "SOURCE_ASSET",
        "SOURCE_SEGMENT", "EXTRACTION_CANDIDATE", "STARTING_CONDITION",
        "ASSUMPTION", "CRITICAL_UNCERTAINTY", "UNCERTAINTY_STATE",
        "DECISION_LENS", "SCENARIO_RULE", "POSSIBLE_PATH", "PATH_STEP",
        "CONSIDERATION", "CONFLICT", "MISSING_INFORMATION",
        "DISCONFIRMING_CONDITION", "VALIDATION_QUESTION",
        "RELATED_RUN_RECORD", "EXTERNAL_HUMAN_FINDING", "BRIEF_STATEMENT",
        "DECISION_OWNER_CONCLUSION",
    )
    roles = fenced_lines_after(authority["truth"], "The closed v2 role vocabulary is:")
    if roles != expected_roles:
        fail(errors, f"epistemic-ledger/v2 role vocabulary changed: {roles!r}")

    expected_relations = (
        "CONTAINS", "EXTRACTED_FROM", "ACCEPTED_AS", "REVISED_AS", "DEFINES",
        "INFORMS", "CONSTRAINS", "BRANCHES_ON", "APPLIES_LENS", "SEQUENCES",
        "SURFACES", "DISCONFIRMED_BY", "PRODUCES_QUESTION", "SUMMARIZES",
    )
    relations = fenced_lines_after(
        authority["truth"], "The closed v2 relation vocabulary is:"
    )
    if relations != expected_relations:
        fail(errors, f"epistemic-ledger/v2 relation vocabulary changed: {relations!r}")

    expected_triples = (
        ("SOURCE_ASSET", "CONTAINS", "SOURCE_SEGMENT"),
        ("EXTRACTION_CANDIDATE", "EXTRACTED_FROM", "SOURCE_SEGMENT"),
        ("EXTRACTION_CANDIDATE", "ACCEPTED_AS", "STARTING_CONDITION"),
        ("EXTRACTION_CANDIDATE", "REVISED_AS", "STARTING_CONDITION"),
        ("SOURCE_SEGMENT", "INFORMS", "STARTING_CONDITION"),
        ("USER_STATEMENT", "DEFINES", "DECISION"),
        ("STARTING_CONDITION", "CONSTRAINS", "SCENARIO_RULE"),
        ("POSSIBLE_PATH", "BRANCHES_ON", "ASSUMPTION"),
        ("POSSIBLE_PATH", "BRANCHES_ON", "UNCERTAINTY_STATE"),
        ("DECISION_LENS", "APPLIES_LENS", "PATH_STEP"),
        ("POSSIBLE_PATH", "SEQUENCES", "PATH_STEP"),
        ("POSSIBLE_PATH", "SURFACES", "CONSIDERATION"),
        ("POSSIBLE_PATH", "SURFACES", "CONFLICT"),
        ("POSSIBLE_PATH", "SURFACES", "MISSING_INFORMATION"),
        ("POSSIBLE_PATH", "DISCONFIRMED_BY", "DISCONFIRMING_CONDITION"),
        ("CONSIDERATION", "PRODUCES_QUESTION", "VALIDATION_QUESTION"),
        ("BRIEF_STATEMENT", "SUMMARIZES", "POSSIBLE_PATH"),
        ("BRIEF_STATEMENT", "SUMMARIZES", "CONSIDERATION"),
    )
    matrix_start = authority["truth"].find("Only these ordered")
    matrix_end = authority["truth"].find("All other triples are forbidden", matrix_start)
    matrix_text = authority["truth"][matrix_start:matrix_end]
    triples = tuple(
        match.groups()
        for match in re.finditer(
            r"(?m)^\| `([A-Z_]+)` \| `([A-Z_]+)` \| `([A-Z_]+)` \|",
            matrix_text,
        )
    )
    if triples != expected_triples:
        fail(errors, f"epistemic-ledger/v2 exact triple matrix changed: {triples!r}")

    expected_source_edges = (
        ("UPLOADING", "QUARANTINED"), ("UPLOADING", "FAILED"),
        ("QUARANTINED", "REJECTED"), ("QUARANTINED", "SCANNING"),
        ("SCANNING", "REJECTED"), ("SCANNING", "FAILED"),
        ("SCANNING", "PARSING"), ("PARSING", "FLAGGED"),
        ("PARSING", "NEEDS_REVIEW"), ("PARSING", "REJECTED"),
        ("PARSING", "FAILED"), ("FLAGGED", "NEEDS_REVIEW"),
        ("FLAGGED", "REJECTED"), ("NEEDS_REVIEW", "READY"),
        ("NEEDS_REVIEW", "REJECTED"), ("NEEDS_REVIEW", "FLAGGED"),
        ("UPLOADING", "DELETION_PENDING"),
        ("QUARANTINED", "DELETION_PENDING"),
        ("SCANNING", "DELETION_PENDING"),
        ("PARSING", "DELETION_PENDING"),
        ("FLAGGED", "DELETION_PENDING"),
        ("NEEDS_REVIEW", "DELETION_PENDING"),
        ("READY", "DELETION_PENDING"),
        ("REJECTED", "DELETION_PENDING"),
        ("FAILED", "DELETION_PENDING"),
        ("DELETION_PENDING", "DELETED"),
    )
    source_edges = mermaid_edges_after(
        authority["states"], "## Source-ingestion state machine"
    )
    if source_edges != expected_source_edges:
        fail(errors, f"closed source-ingestion transition graph changed: {source_edges!r}")

    expected_path_review_edges = (
        ("GENERATED", "INCOMPLETE"), ("GENERATED", "NEEDS_REVIEW"),
        ("NEEDS_REVIEW", "APPROVED"), ("NEEDS_REVIEW", "REJECTED"),
        ("NEEDS_REVIEW", "SUPERSEDED"), ("APPROVED", "SUPERSEDED"),
    )
    path_review_edges = mermaid_edges_after(
        authority["states"], "## Path-artifact review state machine"
    )
    if path_review_edges != expected_path_review_edges:
        fail(errors, f"path-artifact review transition graph changed: {path_review_edges!r}")

    expected_run_states = (
        "DRAFT", "NEEDS_REVIEW", "BLOCKED", "READY", "QUEUED", "PREPARING",
        "EXTRACTING", "REVIEWING_CONDITIONS", "GENERATING_PROFILES",
        "CONSTRUCTING_SCENARIOS", "GENERATING_PATHS", "SYNTHESIZING",
        "VALIDATING_OUTPUT", "GENERATING_BRIEF", "STOP_REQUESTED", "STOPPED",
        "FAILED_RETRYABLE", "FAILED_TERMINAL", "COMPLETED", "ARCHIVED",
    )
    run_state_union = re.search(
        r"(?ms)^type RunState =\s*(.*?);",
        authority["design"],
    )
    parsed_run_states = (
        tuple(re.findall(r'^\s*\| "([A-Z][A-Z_]*)"', run_state_union.group(1), re.MULTILINE))
        if run_state_union
        else ()
    )
    if parsed_run_states != expected_run_states:
        fail(errors, f"canonical 20-state RunState union changed: {parsed_run_states!r}")

    expected_run_edges = (
        ("DRAFT", "NEEDS_REVIEW"),
        ("NEEDS_REVIEW", "BLOCKED"),
        ("BLOCKED", "NEEDS_REVIEW"),
        ("NEEDS_REVIEW", "READY"),
        ("READY", "QUEUED"),
        ("QUEUED", "PREPARING"),
        ("PREPARING", "EXTRACTING"),
        ("EXTRACTING", "REVIEWING_CONDITIONS"),
        ("REVIEWING_CONDITIONS", "GENERATING_PROFILES"),
        ("GENERATING_PROFILES", "CONSTRUCTING_SCENARIOS"),
        ("CONSTRUCTING_SCENARIOS", "GENERATING_PATHS"),
        ("GENERATING_PATHS", "SYNTHESIZING"),
        ("SYNTHESIZING", "VALIDATING_OUTPUT"),
        ("VALIDATING_OUTPUT", "GENERATING_BRIEF"),
        ("GENERATING_BRIEF", "COMPLETED"),
        ("QUEUED", "STOP_REQUESTED"),
        ("PREPARING", "STOP_REQUESTED"),
        ("EXTRACTING", "STOP_REQUESTED"),
        ("REVIEWING_CONDITIONS", "STOP_REQUESTED"),
        ("GENERATING_PROFILES", "STOP_REQUESTED"),
        ("CONSTRUCTING_SCENARIOS", "STOP_REQUESTED"),
        ("GENERATING_PATHS", "STOP_REQUESTED"),
        ("SYNTHESIZING", "STOP_REQUESTED"),
        ("VALIDATING_OUTPUT", "STOP_REQUESTED"),
        ("GENERATING_BRIEF", "STOP_REQUESTED"),
        ("STOP_REQUESTED", "STOPPED"),
        ("PREPARING", "FAILED_RETRYABLE"),
        ("EXTRACTING", "FAILED_RETRYABLE"),
        ("REVIEWING_CONDITIONS", "FAILED_RETRYABLE"),
        ("GENERATING_PROFILES", "FAILED_RETRYABLE"),
        ("CONSTRUCTING_SCENARIOS", "FAILED_RETRYABLE"),
        ("GENERATING_PATHS", "FAILED_RETRYABLE"),
        ("SYNTHESIZING", "FAILED_RETRYABLE"),
        ("VALIDATING_OUTPUT", "FAILED_RETRYABLE"),
        ("GENERATING_BRIEF", "FAILED_RETRYABLE"),
        ("FAILED_RETRYABLE", "QUEUED"),
        ("FAILED_RETRYABLE", "FAILED_TERMINAL"),
        ("COMPLETED", "ARCHIVED"),
        ("STOPPED", "ARCHIVED"),
        ("FAILED_TERMINAL", "ARCHIVED"),
    )
    run_edges = mermaid_edges_after(authority["states"], "## Run state machine")
    if run_edges != expected_run_edges:
        fail(errors, f"closed ordered durable-run transition graph changed: {run_edges!r}")
    run_graph_states = {state for edge in run_edges for state in edge}
    if len(run_graph_states) != 20 or run_graph_states != set(expected_run_states):
        fail(errors, f"durable-run graph does not contain exactly the 20 locked states: {sorted(run_graph_states)!r}")

    comparison_section = text_between(
        authority["design"],
        "### 8.8 Scene 8 — Compare attempts",
        "### 8.9 Scene 9 — Read the decision brief",
    )
    comparison_prose = normalized_prose(comparison_section)
    comparison_policy = normalized_prose(text_between(
        comparison_section,
        "The later comparison bench",
        "Comparison aligns objects by stable semantic identifiers:",
    ))
    expected_comparison_policy = normalized_prose(
        """The later comparison bench accepts **exactly two** completed related runs.
        Viewport size never changes that cardinality. One, three, or more inputs
        are invalid and the future request schema must reject them with a bounded
        `422`. This scene remains unavailable until stable server-owned semantic
        identifiers, unambiguous predecessor rules, exact approved path-set/review
        hashes, and shared decision lineage exist for both runs."""
    )
    if comparison_policy != expected_comparison_policy:
        fail(errors, f"exact-two comparison policy changed: {comparison_policy!r}")
    if comparison_prose.count("**exactly two**") != 1:
        fail(errors, "comparison section must contain exactly one exact-two policy declaration")
    expected_comparison_prose = normalized_prose(
        """### 8.8 Scene 8 — Compare attempts

        The later comparison bench accepts **exactly two** completed related runs.
        Viewport size never changes that cardinality. One, three, or more inputs are
        invalid and the future request schema must reject them with a bounded `422`.
        This scene remains unavailable until stable server-owned semantic identifiers,
        unambiguous predecessor rules, exact approved path-set/review hashes, and
        shared decision lineage exist for both runs.

        Comparison aligns objects by stable semantic identifiers:

        - decision version;
        - changed assumptions;
        - uncertainty states;
        - interventions;
        - path branch reasons;
        - considerations;
        - validation questions.

        The view begins with a textual change ledger. A forked route plate is
        secondary. Shared history remains neutral; divergence uses a single red cut.
        No winner, score, ranking, or automated recommendation is shown."""
    )
    if comparison_prose != expected_comparison_prose:
        fail(errors, "bounded comparison scene changed outside the exact-two contract")

    included_section = text_between(
        authority["design"],
        "### 19.1 Included in the redesign",
        "### 19.2 Deferred until supporting architecture exists",
    )
    deferred_section = text_between(
        authority["design"],
        "### 19.2 Deferred until supporting architecture exists",
        "## 20. Acceptance criteria",
    )
    included_bullets = tuple(re.findall(r"(?m)^- (.+)$", included_section))
    expected_included_bullets = (
        "shared chamber shell;",
        "docket review and run-order experience;",
        "factual run stages;",
        "canonical path list and route plate;",
        "complete run-record inspector;",
        "brief-first follow-up;",
        "full state, responsive, and accessibility behavior;",
        "compatibility routing from current URLs.",
    )
    if included_bullets != expected_included_bullets:
        fail(errors, f"first-slice included capability list changed: {included_bullets!r}")
    expected_included_prose = normalized_prose(
        """### 19.1 Included in the redesign

        - shared chamber shell;
        - docket review and run-order experience;
        - factual run stages;
        - canonical path list and route plate;
        - complete run-record inspector;
        - brief-first follow-up;
        - full state, responsive, and accessibility behavior;
        - compatibility routing from current URLs."""
    )
    if normalized_prose(included_section) != expected_included_prose:
        fail(errors, "first-slice included capability section changed")

    deferred_bullets = tuple(re.findall(r"(?m)^- (.+)$", deferred_section))
    expected_deferred_bullets = (
        "externally imported human evidence with full method metadata;",
        "exactly-two-run semantic comparison;",
        "changed-condition injection and advanced run interventions;",
        "interactive research-handoff construction;",
        "decision-owner conclusions and AI-assisted conclusion editing;",
        "collaborative multi-user review and permissions;",
        "durable real-time annotations shared across users;",
        "calibrated cost and performance history;",
        "full playback from durable checkpoint snapshots;",
        "organization-level decision portfolio analytics.",
    )
    if deferred_bullets != expected_deferred_bullets:
        fail(errors, f"later-release deferred capability list changed: {deferred_bullets!r}")
    expected_deferred_prose = normalized_prose(
        """### 19.2 Deferred until supporting architecture exists

        - externally imported human evidence with full method metadata;
        - exactly-two-run semantic comparison;
        - changed-condition injection and advanced run interventions;
        - interactive research-handoff construction;
        - decision-owner conclusions and AI-assisted conclusion editing;
        - collaborative multi-user review and permissions;
        - durable real-time annotations shared across users;
        - calibrated cost and performance history;
        - full playback from durable checkpoint snapshots;
        - organization-level decision portfolio analytics.

        Deferred capabilities may be represented only as unavailable TARGET features;
        the interface must not imply that they already exist."""
    )
    if normalized_prose(deferred_section) != expected_deferred_prose:
        fail(errors, "later-release deferred capability section changed")

    later_release_section = text_between(
        authority["acceptance"],
        "### Later-release boundary",
        "### Honest status and approvals",
    )
    later_release_prose = normalized_prose(later_release_section)
    expected_later_release_prose = normalized_prose(
        """### Later-release boundary

        - [ ] No semantic comparison is enabled before non-null immutable semantic
          identities and unambiguous predecessor evidence exist. The later comparison
          contract accepts exactly two completed related runs and rejects every other
          count; viewport never changes the rule.
        - [ ] Changed-condition injection, advanced intervention, external-human-
          evidence import, interactive research-handoff construction, and
          decision-owner conclusion workflows remain unavailable until separate
          specifications, privacy/security review, tests, and release approvals land.
        - [ ] Capability responses, routes, UI, docs, analytics, exports, and support
          copy do not imply that any deferred capability exists."""
    )
    if later_release_prose != expected_later_release_prose:
        fail(errors, f"release exact-two/deferred-capability boundary changed: {later_release_prose!r}")

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
