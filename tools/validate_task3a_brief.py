"""Fail-closed structural checks for the Task 3A persistence authority packet."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / ".superpowers" / "sdd" / "task-3a-tenant-persistence-brief.md"
DATA_MODEL = ROOT / "docs" / "architecture" / "data-model.md"
RETENTION = ROOT / "docs" / "privacy" / "RETENTION.md"
DATA_MAP = ROOT / "docs" / "privacy" / "DATA_MAP.md"

EXPECTED_EVENT_REASON_PAIRS = (
    ("SCHEMA_ADOPTION_RECORDED", "SCHEMA_ADOPTION_VERIFIED"),
    ("ROLE_TOPOLOGY_VERIFIED", "ROLE_TOPOLOGY_MATCHED"),
    ("AUDIT_PARTITION_EXPIRY_APPROVED", "RETENTION_EXPIRY_APPROVED"),
    ("AUDIT_PARTITION_EXPIRED", "RETENTION_EXPIRY_COMPLETED"),
)

REQUIRED_LOCKS = (
    "retention-policy/v1",
    "(retention_class, expires_at, id)",
    "audit_events_audit_long",
    "audit_events_deletion_evidence_long",
    "deletion_failed_from_state",
    "core.enforce_identity_subject_transition()",
    "core.enforce_deletion_transition()",
    "7d2c1a9e4b60_core_tenancy_foundation.py",
    "a6150cf0e9d2_core_tenancy_rls_bootstrap.py",
    "test_audit_scope_type_reason_metadata_complement_and_row_immutability_are_closed",
    "DRY_RUN_VERIFIED -> APPLIED|FAILED",
    "deletion state/time/failed-origin only through the exact deletion trigger",
    "one-way policy-derived `expires_at` shortening",
    "core.enforce_persistence_cutover_transition()",
    "rolled_forward_evidence_sha256",
)

FORBIDDEN_LOCKS = (
    "AUDIT_EXPIRY_APPROVED",
    "FAILED -> ELIGIBILITY_CHECK",
    "ELIGIBILITY_CHECK|FAILED",
    "id uuid PK`, non-null organization ID",
)


def _matrix_pairs(text: str) -> tuple[tuple[str, str], ...]:
    section_start = text.find("The closed v1 audit event/metadata matrix is:")
    section_end = text.find("No extra key", section_start)
    if section_start < 0 or section_end < 0:
        return ()
    section = text[section_start:section_end]
    return tuple(
        (event, reason)
        for event, reason in re.findall(
            r"\| `([A-Z][A-Z_]*)` \| `([A-Z][A-Z_]*)` \| `SYSTEM` \|",
            section,
        )
    )


def main() -> int:
    errors: list[str] = []
    documents = {
        "brief": BRIEF.read_text(encoding="utf-8"),
        "data-model": DATA_MODEL.read_text(encoding="utf-8"),
        "retention": RETENTION.read_text(encoding="utf-8"),
        "data-map": DATA_MAP.read_text(encoding="utf-8"),
    }
    combined = "\n".join(documents.values())

    actual_pairs = _matrix_pairs(documents["brief"])
    if actual_pairs != EXPECTED_EVENT_REASON_PAIRS:
        errors.append(f"audit event/reason matrix changed: {actual_pairs!r}")
    for event, reason in EXPECTED_EVENT_REASON_PAIRS:
        authority_documents = (
            documents["brief"],
            documents["data-model"],
            documents["data-map"],
        )
        if any(event not in text or reason not in text for text in authority_documents):
            errors.append(f"event/reason authority missing: {event}/{reason}")
    for lock in REQUIRED_LOCKS:
        if lock not in combined:
            errors.append(f"required Task3a lock missing: {lock}")
    for lock in FORBIDDEN_LOCKS:
        if lock in combined:
            errors.append(f"stale Task3a contradiction remains: {lock}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Task 3A authority errors: {len(errors)}")
        return 1
    print("Task 3A authority contract: PASS")
    print("Audit event/reason pairs: 4; retention policy versions: 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
