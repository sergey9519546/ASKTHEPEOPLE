"""
Observation store builder for simulation artifacts.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, Iterable, List, Optional

from .simulation_artifacts import (
    bootstrap_actions_path,
    canonical_agents_path,
    observation_db_path,
    read_json,
    scheduled_events_path,
)


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_observation_store(simulation_dir: str) -> str:
    db_path = observation_db_path(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_index (
            agent_id INTEGER PRIMARY KEY,
            agent_name TEXT,
            entity_uuid TEXT,
            normalized_role TEXT,
            platform_preference TEXT
        );

        CREATE TABLE IF NOT EXISTS rounds (
            round_num INTEGER PRIMARY KEY,
            simulated_hour INTEGER,
            twitter_actions INTEGER DEFAULT 0,
            reddit_actions INTEGER DEFAULT 0,
            started_at TEXT,
            ended_at TEXT
        );

        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            agent_id INTEGER,
            agent_name TEXT,
            action_type TEXT,
            action_args_json TEXT,
            timestamp TEXT,
            trace_ref TEXT,
            is_bootstrap INTEGER DEFAULT 0,
            is_scheduled INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            agent_id INTEGER,
            agent_name TEXT,
            content TEXT,
            timestamp TEXT,
            trace_ref TEXT
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            agent_id INTEGER,
            agent_name TEXT,
            content TEXT,
            timestamp TEXT,
            trace_ref TEXT
        );

        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            agent_id INTEGER,
            prompt TEXT,
            response TEXT,
            timestamp TEXT,
            trace_ref TEXT
        );

        CREATE TABLE IF NOT EXISTS bootstrap_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            event_type TEXT,
            payload_json TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS scheduled_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            round_num INTEGER,
            event_type TEXT,
            payload_json TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS round_summaries (
            round_num INTEGER PRIMARY KEY,
            payload_json TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _action_type_name(action: str) -> str:
    return (action or "").strip().upper()


def _ingest_sqlite_platform(
    cursor: sqlite3.Cursor,
    simulation_dir: str,
    platform: str,
    ingest_actions: bool,
) -> None:
    db_path = os.path.join(simulation_dir, f"{platform}_simulation.db")
    if not os.path.exists(db_path):
        return

    conn = _connect(db_path)
    db_cursor = conn.cursor()

    user_lookup: Dict[Any, Dict[str, Any]] = {}
    if _table_exists(db_cursor, "user"):
        try:
            db_cursor.execute("SELECT user_id, agent_id, name, user_name FROM user")
            for row in db_cursor.fetchall():
                user_lookup[row["user_id"]] = {
                    "agent_id": row["agent_id"],
                    "agent_name": row["name"] or row["user_name"] or f"Agent_{row['user_id']}",
                }
        except sqlite3.Error:
            user_lookup = {}

    if ingest_actions and _table_exists(db_cursor, "trace"):
        try:
            db_cursor.execute("SELECT rowid, user_id, action, info, created_at FROM trace ORDER BY rowid ASC")
            for row in db_cursor.fetchall():
                try:
                    info = json.loads(row["info"]) if row["info"] else {}
                except json.JSONDecodeError:
                    info = {"raw": row["info"]}

                actor = user_lookup.get(row["user_id"], {})
                agent_id = actor.get("agent_id")
                agent_name = actor.get("agent_name", f"Agent_{row['user_id']}")
                round_num = info.get("round") or info.get("round_num") or 0
                action_type = _action_type_name(row["action"])
                action_args = info.get("action_args", info) if isinstance(info, dict) else {"raw": info}
                trace_ref = f"{platform}:trace:{row['rowid']}"

                if action_type == "INTERVIEW":
                    cursor.execute(
                        """
                        INSERT INTO interviews(platform, round_num, agent_id, prompt, response, timestamp, trace_ref)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            platform,
                            round_num,
                            agent_id,
                            action_args.get("prompt", ""),
                            action_args.get("response") or json.dumps(action_args, ensure_ascii=False),
                            row["created_at"],
                            trace_ref,
                        ),
                    )
                    continue

                cursor.execute(
                    """
                    INSERT INTO actions(platform, round_num, agent_id, agent_name, action_type, action_args_json, timestamp, trace_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        round_num,
                        agent_id,
                        agent_name,
                        action_type,
                        json.dumps(action_args, ensure_ascii=False),
                        row["created_at"],
                        trace_ref,
                    ),
                )
        except sqlite3.Error:
            pass

    if _table_exists(db_cursor, "post"):
        try:
            db_cursor.execute("SELECT rowid, * FROM post ORDER BY created_at ASC")
            for row in db_cursor.fetchall():
                actor = user_lookup.get(row["user_id"], {})
                cursor.execute(
                    """
                    INSERT INTO posts(platform, round_num, agent_id, agent_name, content, timestamp, trace_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        0,
                        actor.get("agent_id"),
                        actor.get("agent_name", f"Agent_{row['user_id']}"),
                        row["content"],
                        row["created_at"],
                        f"{platform}:post:{row['rowid']}",
                    ),
                )
        except sqlite3.Error:
            pass

    if _table_exists(db_cursor, "comment"):
        try:
            db_cursor.execute("SELECT rowid, * FROM comment ORDER BY created_at ASC")
            for row in db_cursor.fetchall():
                actor = user_lookup.get(row["user_id"], {})
                cursor.execute(
                    """
                    INSERT INTO comments(platform, round_num, agent_id, agent_name, content, timestamp, trace_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        0,
                        actor.get("agent_id"),
                        actor.get("agent_name", f"Agent_{row['user_id']}"),
                        row["content"],
                        row["created_at"],
                        f"{platform}:comment:{row['rowid']}",
                    ),
                )
        except sqlite3.Error:
            pass

    conn.close()


def sync_observation_store(simulation_dir: str, run_state: Optional[Dict[str, Any]] = None) -> str:
    db_path = ensure_observation_store(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM agent_index")
    cursor.execute("DELETE FROM rounds")
    cursor.execute("DELETE FROM actions")
    cursor.execute("DELETE FROM posts")
    cursor.execute("DELETE FROM comments")
    cursor.execute("DELETE FROM interviews")
    cursor.execute("DELETE FROM bootstrap_events")
    cursor.execute("DELETE FROM scheduled_events")
    cursor.execute("DELETE FROM round_summaries")

    for agent in read_json(canonical_agents_path(simulation_dir), default=[]):
        cursor.execute(
            """
            INSERT INTO agent_index(agent_id, agent_name, entity_uuid, normalized_role, platform_preference)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                agent.get("agent_id"),
                agent.get("display_name"),
                agent.get("source_entity_uuid"),
                agent.get("source_entity_type_normalized"),
                agent.get("activity_seed", {}).get("platform_preference", "both"),
            ),
        )

    def ingest_platform(platform: str) -> None:
        action_path = os.path.join(simulation_dir, platform, "actions.jsonl")
        _ingest_sqlite_platform(cursor, simulation_dir, platform, ingest_actions=not os.path.exists(action_path))

        for index, row in enumerate(_iter_jsonl(action_path)):
            if row.get("event_type") == "round_start":
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO rounds(round_num, simulated_hour, started_at)
                    VALUES (?, ?, ?)
                    """,
                    (row.get("round"), row.get("simulated_hour"), row.get("timestamp")),
                )
                continue
            if row.get("event_type") == "round_end":
                cursor.execute(
                    """
                    INSERT INTO rounds(round_num, ended_at, twitter_actions, reddit_actions)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(round_num) DO UPDATE SET
                        ended_at=excluded.ended_at,
                        twitter_actions=CASE WHEN ?='twitter' THEN excluded.twitter_actions ELSE rounds.twitter_actions END,
                        reddit_actions=CASE WHEN ?='reddit' THEN excluded.reddit_actions ELSE rounds.reddit_actions END
                    """,
                    (
                        row.get("round"),
                        row.get("timestamp"),
                        row.get("actions_count", 0) if platform == "twitter" else 0,
                        row.get("actions_count", 0) if platform == "reddit" else 0,
                        platform,
                        platform,
                    ),
                )
                continue
            if row.get("event_type"):
                continue

            action_args_json = json.dumps(row.get("action_args", {}), ensure_ascii=False)
            trace_ref = f"{platform}:actions:{index}"
            cursor.execute(
                """
                INSERT INTO actions(platform, round_num, agent_id, agent_name, action_type, action_args_json, timestamp, trace_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    platform,
                    row.get("round"),
                    row.get("agent_id"),
                    row.get("agent_name"),
                    row.get("action_type"),
                    action_args_json,
                    row.get("timestamp"),
                    trace_ref,
                ),
            )

            action_type = (row.get("action_type") or "").upper()
            content = row.get("action_args", {}).get("content")
            if action_type in {"CREATE_POST", "QUOTE_POST"} and content:
                cursor.execute(
                    """
                    INSERT INTO posts(platform, round_num, agent_id, agent_name, content, timestamp, trace_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (platform, row.get("round"), row.get("agent_id"), row.get("agent_name"), content, row.get("timestamp"), trace_ref),
                )
            elif action_type == "CREATE_COMMENT" and content:
                cursor.execute(
                    """
                    INSERT INTO comments(platform, round_num, agent_id, agent_name, content, timestamp, trace_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (platform, row.get("round"), row.get("agent_id"), row.get("agent_name"), content, row.get("timestamp"), trace_ref),
                )

    ingest_platform("twitter")
    ingest_platform("reddit")

    for index, row in enumerate(_iter_jsonl(bootstrap_actions_path(simulation_dir))):
        cursor.execute(
            """
            INSERT INTO bootstrap_events(platform, round_num, event_type, payload_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row.get("platform"),
                row.get("round_num", 0),
                row.get("event_type"),
                json.dumps(row, ensure_ascii=False),
                row.get("timestamp"),
            ),
        )
        if row.get("event_type") == "post":
            cursor.execute(
                """
                INSERT INTO actions(platform, round_num, agent_id, agent_name, action_type, action_args_json, timestamp, trace_ref, is_bootstrap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    row.get("platform"),
                    row.get("round_num", 0),
                    row.get("agent_id"),
                    row.get("agent_name"),
                    "CREATE_POST",
                    json.dumps({"content": row.get("content")}, ensure_ascii=False),
                    row.get("timestamp"),
                    f"bootstrap:{index}",
                ),
            )
            cursor.execute(
                """
                INSERT INTO posts(platform, round_num, agent_id, agent_name, content, timestamp, trace_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("platform"),
                    row.get("round_num", 0),
                    row.get("agent_id"),
                    row.get("agent_name"),
                    row.get("content"),
                    row.get("timestamp"),
                    f"bootstrap:{index}",
                ),
            )

    for row in _iter_jsonl(scheduled_events_path(simulation_dir)):
        cursor.execute(
            """
            INSERT INTO scheduled_events(platform, round_num, event_type, payload_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row.get("platform"),
                row.get("round_num"),
                row.get("event_type"),
                json.dumps(row, ensure_ascii=False),
                row.get("timestamp"),
            ),
        )

    if run_state:
        for summary in run_state.get("rounds", []):
            cursor.execute(
                """
                INSERT OR REPLACE INTO round_summaries(round_num, payload_json)
                VALUES (?, ?)
                """,
                (summary.get("round_num"), json.dumps(summary, ensure_ascii=False)),
            )

    conn.commit()
    conn.close()
    return db_path


def search_observations(
    simulation_dir: str,
    query: str = "",
    platform: Optional[str] = None,
    agent_id: Optional[int] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    db_path = sync_observation_store(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()

    sql = """
        SELECT platform, round_num, agent_id, agent_name, action_type, action_args_json, timestamp, trace_ref
        FROM actions
        WHERE 1=1
    """
    params: List[Any] = []

    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if agent_id is not None:
        sql += " AND agent_id = ?"
        params.append(agent_id)
    if query:
        sql += " AND (action_args_json LIKE ? OR agent_name LIKE ? OR action_type LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern])

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"query": query, "count": len(rows), "results": rows}
