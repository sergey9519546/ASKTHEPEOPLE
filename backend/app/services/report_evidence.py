"""
Grounded report evidence generation from simulation observations.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List

from .simulation_artifacts import report_evidence_path
from .simulation_observation_store import sync_observation_store


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _section_query_seed(section_title: str, section_content: str) -> List[str]:
    seen = set()
    seeds = [section_title]
    tokens = []
    for token in (section_title + " " + section_content).replace("\n", " ").split():
        cleaned = token.strip(".,:;!?()[]{}\"'").lower()
        if len(cleaned) >= 5 and cleaned not in seen:
            seen.add(cleaned)
            tokens.append(cleaned)
        if len(tokens) >= 6:
            break
    seeds.extend(tokens[:3])
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
        claim_counter = 1
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
                        "claim_id": f"section_{section_index}_claim_{claim_counter}",
                        "source_type": "action",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["action_args_json"][:500],
                        "confidence": 0.72,
                    }
                )
                claim_counter += 1

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
                        "claim_id": f"section_{section_index}_claim_{claim_counter}",
                        "source_type": "post",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["content"][:500],
                        "confidence": 0.78,
                    }
                )
                claim_counter += 1

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
                        "claim_id": f"section_{section_index}_claim_{claim_counter}",
                        "source_type": "comment",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["content"][:500],
                        "confidence": 0.74,
                    }
                )
                claim_counter += 1

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
                        "claim_id": f"section_{section_index}_claim_{claim_counter}",
                        "source_type": "interview",
                        "platform": row["platform"],
                        "agent_id": row["agent_id"],
                        "round_num": row["round_num"],
                        "trace_ref": row["trace_ref"],
                        "excerpt": row["response"][:500],
                        "confidence": 0.68,
                    }
                )
                claim_counter += 1

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
                    "claim_id": f"section_{section_index}_claim_{claim_counter}",
                    "source_type": "round_summary",
                    "platform": "mixed",
                    "agent_id": None,
                    "round_num": summary_row["round_num"],
                    "trace_ref": f"round_summary:{summary_row['round_num']}",
                    "excerpt": summary_row["payload_json"][:500],
                    "confidence": 0.6,
                }
            )

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
                    "claim_id": f"section_{section_index}_claim_{claim_counter}",
                    "source_type": "scheduled_event",
                    "platform": scheduled_row["platform"],
                    "agent_id": None,
                    "round_num": scheduled_row["round_num"],
                    "trace_ref": f"scheduled:{scheduled_row['event_type']}:{scheduled_row['round_num']}",
                    "excerpt": scheduled_row["payload_json"][:500],
                    "confidence": 0.58,
                }
            )
            claim_counter += 1

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
                    "claim_id": f"section_{section_index}_claim_{claim_counter}",
                    "source_type": "bootstrap_event",
                    "platform": bootstrap_row["platform"],
                    "agent_id": None,
                    "round_num": bootstrap_row["round_num"],
                    "trace_ref": f"bootstrap:{bootstrap_row['event_type']}:{bootstrap_row['round_num']}",
                    "excerpt": bootstrap_row["payload_json"][:500],
                    "confidence": 0.58,
                }
            )

    conn.close()

    with open(report_evidence_path(report_dir), "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
    return evidence


def load_report_evidence(report_dir: str) -> List[Dict[str, Any]]:
    path = report_evidence_path(report_dir)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
