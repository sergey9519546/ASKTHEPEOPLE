"""Fail-closed contract check for the Task 5 durable-run implementation brief."""

from __future__ import annotations

import re
import sys
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / ".superpowers" / "sdd" / "task-5-brief.md"

RUN_STATES = (
    "DRAFT", "NEEDS_REVIEW", "BLOCKED", "READY", "QUEUED", "PREPARING",
    "EXTRACTING", "REVIEWING_CONDITIONS", "GENERATING_PROFILES",
    "CONSTRUCTING_SCENARIOS", "GENERATING_PATHS", "SYNTHESIZING",
    "VALIDATING_OUTPUT", "GENERATING_BRIEF", "STOP_REQUESTED", "STOPPED",
    "FAILED_RETRYABLE", "FAILED_TERMINAL", "COMPLETED", "ARCHIVED",
)
STAGES = RUN_STATES[5:14]
ACTIVE = ("QUEUED", *STAGES)
ATTEMPT_STATES = (
    "PENDING", "READY", "RUNNING", "VALIDATING", "SUCCEEDED", "RETRY_WAIT",
    "FAILED_TERMINAL", "CANCEL_REQUESTED", "CANCELLED",
)
DIRECT_RUN_EDGES = {
    ("DRAFT", "NEEDS_REVIEW"), ("NEEDS_REVIEW", "BLOCKED"),
    ("BLOCKED", "NEEDS_REVIEW"), ("NEEDS_REVIEW", "READY"),
    ("READY", "QUEUED"), ("QUEUED", "PREPARING"),
    ("PREPARING", "EXTRACTING"), ("EXTRACTING", "REVIEWING_CONDITIONS"),
    ("REVIEWING_CONDITIONS", "GENERATING_PROFILES"),
    ("GENERATING_PROFILES", "CONSTRUCTING_SCENARIOS"),
    ("CONSTRUCTING_SCENARIOS", "GENERATING_PATHS"),
    ("GENERATING_PATHS", "SYNTHESIZING"),
    ("SYNTHESIZING", "VALIDATING_OUTPUT"),
    ("VALIDATING_OUTPUT", "GENERATING_BRIEF"),
    ("GENERATING_BRIEF", "COMPLETED"), ("STOP_REQUESTED", "STOPPED"),
    ("FAILED_RETRYABLE", "QUEUED"),
    ("FAILED_RETRYABLE", "FAILED_TERMINAL"),
    ("COMPLETED", "ARCHIVED"), ("STOPPED", "ARCHIVED"),
    ("FAILED_TERMINAL", "ARCHIVED"),
}
EXPECTED_RUN_EDGES = frozenset({
    *DIRECT_RUN_EDGES,
    *((state, "STOP_REQUESTED") for state in ACTIVE),
    *((state, "FAILED_RETRYABLE") for state in STAGES),
})
EXPECTED_ATTEMPT_EDGES = frozenset({
    ("PENDING", "READY"), ("READY", "RUNNING"),
    ("RUNNING", "VALIDATING"), ("VALIDATING", "SUCCEEDED"),
    ("RUNNING", "RETRY_WAIT"), ("VALIDATING", "RETRY_WAIT"),
    ("RUNNING", "FAILED_TERMINAL"), ("VALIDATING", "FAILED_TERMINAL"),
    ("RUNNING", "CANCEL_REQUESTED"), ("CANCEL_REQUESTED", "CANCELLED"),
})


def fenced_lines_after(text: str, marker: str) -> tuple[str, ...]:
    marker_at = text.find(marker)
    if marker_at < 0:
        return ()
    match = re.search(r"```text\s*\n(.*?)\n```", text[marker_at:], re.DOTALL)
    if match is None:
        return ()
    return tuple(line.strip() for line in match.group(1).splitlines() if line.strip())


def parse_run_edges(text: str) -> frozenset[tuple[str, str]]:
    section = text[text.find("### Exact allowed transitions"):text.find("## Canonical stage-attempt")]
    edges = set(re.findall(
        r"(?m)^\| `([A-Z][A-Z_]*)` \| `([A-Z][A-Z_]*)` \|", section
    ))
    if "every active execution state" in section:
        edges.update((state, "STOP_REQUESTED") for state in ACTIVE)
    if "every stage state from `PREPARING` through `GENERATING_BRIEF`" in section:
        edges.update((state, "FAILED_RETRYABLE") for state in STAGES)
    return frozenset(edges)


def parse_attempt_edges(text: str) -> frozenset[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for line in fenced_lines_after(text, "Allowed attempt transitions are:"):
        states = tuple(part.strip() for part in line.split("->"))
        edges.update(pairwise(states))
    return frozenset(edges)


def main() -> int:
    errors: list[str] = []
    text = BRIEF.read_text(encoding="utf-8")
    if fenced_lines_after(text, "### States") != RUN_STATES:
        errors.append("exact 20-state vocabulary changed")
    if fenced_lines_after(text, "`RunStageCode` contains exactly") != STAGES:
        errors.append("exact nine-stage vocabulary changed")
    if fenced_lines_after(text, "`RunStageAttemptState` contains exactly") != ATTEMPT_STATES:
        errors.append("exact nine-state attempt vocabulary changed")
    run_edges = parse_run_edges(text)
    if len(run_edges) != 40 or run_edges != EXPECTED_RUN_EDGES:
        errors.append(f"closed 40-edge run graph changed: {sorted(run_edges)!r}")
    attempt_edges = parse_attempt_edges(text)
    if attempt_edges != EXPECTED_ATTEMPT_EDGES:
        errors.append(f"closed attempt graph changed: {sorted(attempt_edges)!r}")
    required = (
        "current_path_set_id", "approved_path_review_id", "current_path_set_sha256",
        "approved_path_review_sha256", "path_validator_bundle_version",
        "brief_gate_sha256", "RUN_STAGE_WORKER", "RUN_OUTBOX_DISPATCHER",
        "RUN_LEASE_REAPER", "WorkerRunCommandKind", "claim_run_dispatch_batch",
        "claim_expired_run_lease_batch", "run_stream_ticket_service.py",
        "shared Redis replay store", "Redis Lua", "compare-and-delete",
        "disabling the flag stops new canonical starts but preserves canonical reads",
        "`AGENTS.md`", "code comments", "generated documentation",
    )
    errors.extend(f"required contract lock missing: {lock}" for lock in required if lock not in text)
    forbidden = (
        "Prove the flag hides every durable route by default.",
        "next stage attempt number reserved",
        "purpose varchar(32) not null check (= 'RUN_STAGE_WORKER')",
        "Service transitions use only `run_stage:execute`",
        "atomically consumes the nonce with Redis `SET NX`",
    )
    errors.extend(f"stale contradictory contract remains: {item}" for item in forbidden if item in text)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Task 5 brief errors: {len(errors)}")
        return 1
    print("Task 5 brief contract: PASS")
    print("Run states: 20; run edges: 40; stages: 9; attempt states: 9; attempt edges: 10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
