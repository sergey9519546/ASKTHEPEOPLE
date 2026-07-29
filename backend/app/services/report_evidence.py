"""
Post-hoc trace examples selected from synthetic simulation observations.

The selector uses keyword overlap after a report section has been generated.
The resulting records can help someone inspect the run, but they do not prove,
support, cite, or establish which artifact caused a report statement.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List

from .claim_boundary import (
    synthetic_activity_disclosure,
    synthetic_config_disclosure,
)
from .simulation_artifacts import report_evidence_path
from .simulation_observation_store import sync_observation_store


def _evidence_metadata(source_type: str) -> Dict[str, Any]:
    """Return the non-probabilistic interpretation contract for a trace."""
    if source_type in {"scheduled_event", "bootstrap_event"}:
        metadata = synthetic_config_disclosure()
        evidence_class = "configuration_assumption"
        record_type = "configuration_assumption"
        interpretation = (
            "Injected scenario condition; not an observed event or human response."
        )
    else:
        metadata = synthetic_activity_disclosure()
        evidence_class = "synthetic_observation"
        record_type = {
            "action": "generated_action",
            "post": "generated_post",
            "comment": "generated_comment",
            "interview": "generated_profile_response",
            "round_summary": "generated_round_summary",
        }.get(source_type, "generated_run_record")
        interpretation = (
            "Generated within this simulation run; not observed human behavior."
        )

    metadata.update(
        {
            "record_type": record_type,
            "evidence_class": evidence_class,
            "human_respondents": 0,
            "external_validation": False,
            "causal_evidence": False,
            "calibration": "not_calibrated",
            "interpretation": interpretation,
        }
    )
    if source_type == "interview":
        metadata.update(
            {
                "legacy_source_type_deprecated": True,
                "source_type_interpretation": (
                    "The legacy 'interview' value denotes a model-generated "
                    "profile response, not a human interview."
                ),
            }
        )
    return metadata


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _section_query_seed(section_title: str, section_content: str) -> List[str]:
    seeds = [section_title.strip()] if section_title and section_title.strip() else []
    tokens = []
    seen = {s.lower() for s in seeds}
    for token in (section_title + " " + section_content).replace("\n", " ").split():
        cleaned = token.strip(".,:;!?()[]{}\"'").lower()
        if len(cleaned) >= 5 and cleaned not in seen:
            tokens.append(cleaned)
            seen.add(cleaned)
        if len(tokens) >= 6:
            break
    for t in tokens[:3]:
        if t not in seeds:
            seeds.append(t)
    return [seed for seed in seeds if seed]


def build_report_evidence(
    report_id: str,
    report_dir: str,
    simulation_dir: str,
    outline: Any,
) -> List[Dict[str, Any]]:
    observation_db = sync_observation_store(simulation_dir)
    conn = _connect(observation_db)
    cursor = conn.cursor()

    evidence: List[Dict[str, Any]] = []
    for section_index, section in enumerate(getattr(outline, "sections", []), start=1):
        section_path = os.path.join(report_dir, f"section_{section_index:02d}.md")
        section_content = ""
        if os.path.exists(section_path):
            with open(section_path, "r", encoding="utf-8") as handle:
                section_content = handle.read()

        seeds = _section_query_seed(section.title, section_content)
        trace_counter = 1
        for seed in seeds[:3]:
            cursor.execute(
                """
                SELECT platform, round_num, agent_id, action_type, action_args_json, trace_ref
                FROM actions
                WHERE action_args_json LIKE ?
                ORDER BY timestamp DESC
                LIMIT 2
                """,
                (f"%{seed}%",),
            )
            for row in cursor.fetchall():
                evidence.append(
                    {
                        "section_index": section_index,
                        "trace_id": f"section_{section_index}_trace_{trace_counter}",
                        "source_type": "action",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["action_args_json"][:500],
                        **_evidence_metadata("action"),
                    }
                )
                trace_counter += 1

            cursor.execute(
                """
                SELECT platform, round_num, agent_id, content, trace_ref
                FROM posts
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (f"%{seed}%",),
            )
            for row in cursor.fetchall():
                evidence.append(
                    {
                        "section_index": section_index,
                        "trace_id": f"section_{section_index}_trace_{trace_counter}",
                        "source_type": "post",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["content"][:500],
                        **_evidence_metadata("post"),
                    }
                )
                trace_counter += 1

            cursor.execute(
                """
                SELECT platform, round_num, agent_id, content, trace_ref
                FROM comments
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (f"%{seed}%",),
            )
            for row in cursor.fetchall():
                evidence.append(
                    {
                        "section_index": section_index,
                        "trace_id": f"section_{section_index}_trace_{trace_counter}",
                        "source_type": "comment",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["content"][:500],
                        **_evidence_metadata("comment"),
                    }
                )
                trace_counter += 1

            cursor.execute(
                """
                SELECT platform, round_num, agent_id, response, trace_ref
                FROM interviews
                WHERE response LIKE ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (f"%{seed}%",),
            )
            for row in cursor.fetchall():
                evidence.append(
                    {
                        "section_index": section_index,
                        "trace_id": f"section_{section_index}_trace_{trace_counter}",
                        "source_type": "interview",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["response"][:500],
                        **_evidence_metadata("interview"),
                    }
                )
                trace_counter += 1

        cursor.execute(
            """
            SELECT round_num, payload_json
            FROM round_summaries
            ORDER BY round_num DESC
            LIMIT 1
            """
        )
        summary_row = cursor.fetchone()
        if summary_row:
            evidence.append(
                {
                    "section_index": section_index,
                    "trace_id": f"section_{section_index}_trace_{trace_counter}",
                    "source_type": "round_summary",
                    "platform": "mixed",
                    "agent_id": None,
                    "round_num": summary_row["round_num"],
                    "trace_ref": f"round_summary:{summary_row['round_num']}",
                    "excerpt": summary_row["payload_json"][:500],
                    **_evidence_metadata("round_summary"),
                }
            )
            trace_counter += 1

        cursor.execute(
            """
            SELECT platform, round_num, event_type, payload_json, timestamp
            FROM scheduled_events
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        scheduled_row = cursor.fetchone()
        if scheduled_row:
            evidence.append(
                {
                    "section_index": section_index,
                    "trace_id": f"section_{section_index}_trace_{trace_counter}",
                    "source_type": "scheduled_event",
                    "platform": scheduled_row["platform"],
                    "agent_id": None,
                    "round_num": scheduled_row["round_num"],
                    "trace_ref": f"scheduled:{scheduled_row['event_type']}:{scheduled_row['round_num']}",
                    "excerpt": scheduled_row["payload_json"][:500],
                    **_evidence_metadata("scheduled_event"),
                }
            )
            trace_counter += 1

        cursor.execute(
            """
            SELECT platform, round_num, event_type, payload_json, timestamp
            FROM bootstrap_events
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        bootstrap_row = cursor.fetchone()
        if bootstrap_row:
            evidence.append(
                {
                    "section_index": section_index,
                    "trace_id": f"section_{section_index}_trace_{trace_counter}",
                    "source_type": "bootstrap_event",
                    "platform": bootstrap_row["platform"],
                    "agent_id": None,
                    "round_num": bootstrap_row["round_num"],
                    "trace_ref": f"bootstrap:{bootstrap_row['event_type']}:{bootstrap_row['round_num']}",
                    "excerpt": bootstrap_row["payload_json"][:500],
                    **_evidence_metadata("bootstrap_event"),
                }
            )
            trace_counter += 1

    conn.close()

    with open(report_evidence_path(report_dir), "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
    return evidence


def load_report_evidence(report_dir: str) -> List[Dict[str, Any]]:
    path = report_evidence_path(report_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        records = json.load(handle)

    normalized: List[Dict[str, Any]] = []
    for index, record in enumerate(records if isinstance(records, list) else []):
        if not isinstance(record, dict):
            continue
        item = dict(record)
        deprecated_fields = []
        if "claim_id" in item:
            deprecated_fields.append("claim_id")
        legacy_id = str(item.pop("claim_id", "") or "")
        if "confidence" in item:
            deprecated_fields.append("confidence")
            item.pop("confidence", None)
        trace_id = str(item.get("trace_id", "") or "")
        if not trace_id:
            trace_id = legacy_id.replace("_claim_", "_trace_")
        item["trace_id"] = trace_id or f"legacy_trace_{index + 1}"
        item.update(_evidence_metadata(str(item.get("source_type", "") or "")))
        if deprecated_fields:
            item["legacy_schema_normalization"] = {
                "deprecated_fields_removed": deprecated_fields,
                "score_interpretation": (
                    "No probability, likelihood, or evidence-strength score "
                    "is provided."
                ),
            }
        normalized.append(item)
    return normalized
