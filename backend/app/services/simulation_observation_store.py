"""
Observation store builder for simulation artifacts.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

_IN_MEMORY_EVENT_QUEUES: Dict[str, List[Dict[str, Any]]] = {}
_EVENT_QUEUE_LOCK = threading.Lock()


def push_in_memory_event(simulation_id: str, event_data: Dict[str, Any]) -> None:
    """Push an injected event to the in-memory fallback event queue for simulation_id."""
    with _EVENT_QUEUE_LOCK:
        if simulation_id not in _IN_MEMORY_EVENT_QUEUES:
            _IN_MEMORY_EVENT_QUEUES[simulation_id] = []
        _IN_MEMORY_EVENT_QUEUES[simulation_id].append(event_data)


def pop_in_memory_events(simulation_id: str) -> List[Dict[str, Any]]:
    """Pop and return all pending in-memory injected events for simulation_id."""
    with _EVENT_QUEUE_LOCK:
        return _IN_MEMORY_EVENT_QUEUES.pop(simulation_id, [])


from .claim_boundary import synthetic_activity_disclosure
from .simulation_artifacts import (
    bootstrap_actions_path,
    canonical_agents_path,
    observation_db_path,
    read_json,
    scheduled_events_path,
)

_MAX_OBSERVATION_RECORDS = 100_000
_MAX_OBSERVATION_LINE_CHARS = 1_000_000
_MAX_OBSERVATION_FILE_CHARS = 256_000_000
_MAX_OBSERVATION_SEARCH_RESULTS = 200
_MAX_OBSERVATION_QUERY_CHARS = 500
_MAX_AGENT_RECORDS = 20_000
_MAX_OBSERVATION_TEXT_CHARS = 65_536
_MAX_AGENT_FILE_BYTES = 50 * 1024 * 1024


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.Error:
        pass
    return conn


def get_observation_db_journal_mode(simulation_dir: str) -> str:
    """Return the SQLite journal mode for the simulation's observation database."""
    db_path = observation_db_path(simulation_dir)
    if not os.path.exists(db_path):
        return ""
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        row = cursor.fetchone()
    finally:
        conn.close()
    return str(row[0]).lower() if row else ""


def ensure_observation_store(simulation_dir: str) -> str:
    os.makedirs(simulation_dir, exist_ok=True)
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

        CREATE TABLE IF NOT EXISTS injected_events (
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

        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            round_num INTEGER,
            synthesis_text TEXT,
            importance_score REAL,
            timestamp TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _iter_jsonl(
    path: str,
    max_records: int = _MAX_OBSERVATION_RECORDS,
) -> Iterable[Dict[str, Any]]:
    """Yield a bounded number of bounded-size JSONL records."""
    if not os.path.exists(path):
        return
    yielded = 0
    chars_read = 0
    with open(path, "r", encoding="utf-8") as handle:
        while yielded < max_records and chars_read < _MAX_OBSERVATION_FILE_CHARS:
            line = handle.readline(_MAX_OBSERVATION_LINE_CHARS + 1)
            if not line:
                break
            chars_read += len(line)
            if len(line) > _MAX_OBSERVATION_LINE_CHARS:
                # Drain the remainder of this oversized record in bounded
                # pieces so it can never be parsed or retained.
                while line and not line.endswith("\n"):
                    line = handle.readline(_MAX_OBSERVATION_LINE_CHARS + 1)
                    chars_read += len(line)
                    if chars_read >= _MAX_OBSERVATION_FILE_CHARS:
                        break
                continue
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yielded += 1
                yield row


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
            db_cursor.execute(
                """
                SELECT user_id, agent_id,
                       substr(name, 1, ?) AS name,
                       substr(user_name, 1, ?) AS user_name
                FROM user LIMIT ?
                """,
                (512, 512, _MAX_AGENT_RECORDS),
            )
            for row in db_cursor:
                user_lookup[row["user_id"]] = {
                    "agent_id": row["agent_id"],
                    "agent_name": row["name"] or row["user_name"] or f"Agent_{row['user_id']}",
                }
        except sqlite3.Error:
            user_lookup = {}

    if ingest_actions and _table_exists(db_cursor, "trace"):
        try:
            db_cursor.execute(
                """
                SELECT rowid, user_id,
                       substr(action, 1, 256) AS action,
                       substr(info, 1, ?) AS info,
                       created_at
                FROM trace ORDER BY rowid ASC LIMIT ?
                """,
                (_MAX_OBSERVATION_TEXT_CHARS, _MAX_OBSERVATION_RECORDS),
            )
            for row in db_cursor:
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
            db_cursor.execute(
                """
                SELECT rowid, user_id, substr(content, 1, ?) AS content, created_at
                FROM post ORDER BY created_at ASC LIMIT ?
                """,
                (_MAX_OBSERVATION_TEXT_CHARS, _MAX_OBSERVATION_RECORDS),
            )
            for row in db_cursor:
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
            db_cursor.execute(
                """
                SELECT rowid, user_id, substr(content, 1, ?) AS content, created_at
                FROM comment ORDER BY created_at ASC LIMIT ?
                """,
                (_MAX_OBSERVATION_TEXT_CHARS, _MAX_OBSERVATION_RECORDS),
            )
            for row in db_cursor:
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
    cursor.execute("DELETE FROM reflections")

    agent_path = canonical_agents_path(simulation_dir)
    agents = (
        read_json(agent_path, default=[])
        if os.path.exists(agent_path) and os.path.getsize(agent_path) <= _MAX_AGENT_FILE_BYTES
        else []
    )
    for agent in agents[:_MAX_AGENT_RECORDS] if isinstance(agents, list) else []:
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

    injected_path = os.path.join(simulation_dir, "injected_events.jsonl")
    for row in _iter_jsonl(injected_path):
        cursor.execute(
            """
            INSERT INTO injected_events(platform, round_num, event_type, payload_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row.get("platform"),
                row.get("round_num", 0),
                row.get("event_type"),
                json.dumps(row.get("payload", row), ensure_ascii=False),
                row.get("timestamp"),
            ),
        )

    if run_state:
        for summary in run_state.get("rounds", [])[:10_000]:
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


def record_injected_event(
    simulation_dir: str,
    platform: str,
    round_num: int,
    event_type: str,
    payload: Dict[str, Any],
    timestamp: Optional[str] = None,
) -> None:
    """Record an injected scenario event into simulation_observations.db."""
    db_path = ensure_observation_store(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()
    ts = timestamp or datetime.now().isoformat()
    payload_json = json.dumps(payload, ensure_ascii=False)
    cursor.execute(
        """
        INSERT INTO injected_events(platform, round_num, event_type, payload_json, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (platform, round_num, event_type, payload_json, ts),
    )
    conn.commit()
    conn.close()


def search_observations(
    simulation_dir: str,
    query: str = "",
    platform: Optional[str] = None,
    agent_id: Optional[int] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    query = str(query or "")[:_MAX_OBSERVATION_QUERY_CHARS]
    if platform not in {None, "", "twitter", "reddit"}:
        raise ValueError("platform must be twitter or reddit")
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, _MAX_OBSERVATION_SEARCH_RESULTS))

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
        sql += (
            " AND (action_args_json LIKE ? ESCAPE '\\'"
            " OR agent_name LIKE ? ESCAPE '\\'"
            " OR action_type LIKE ? ESCAPE '\\')"
        )
        escaped_query = (
            query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped_query}%"
        params.extend([pattern, pattern, pattern])

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = [
        {**dict(row), **synthetic_activity_disclosure()}
        for row in cursor.fetchall()
    ]
    conn.close()
    return {"query": query, "count": len(rows), "results": rows}


def add_reflection(
    simulation_dir: str,
    agent_name: str,
    round_num: int,
    synthesis_text: str,
    importance_score: float,
    timestamp: Optional[str] = None,
) -> None:
    """Record an agent's periodic memory reflection synthesis."""
    db_path = ensure_observation_store(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()
    ts = timestamp or datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO reflections(agent_name, round_num, synthesis_text, importance_score, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (agent_name, round_num, synthesis_text, importance_score, ts),
    )
    conn.commit()
    conn.close()


def get_relevant_memories(
    simulation_dir: str,
    agent_name: str,
    current_round: int,
    query_text: str = "",
    limit: int = 5,
    w_r: float = 1.0,
    w_i: float = 1.0,
    w_v: float = 1.0,
) -> List[Dict[str, Any]]:
    """Retrieve memories using a weighted sum of Recency, Importance, and (simulated) Relevance."""
    db_path = ensure_observation_store(simulation_dir)
    conn = _connect(db_path)
    cursor = conn.cursor()
    
    # Simple lexical relevance if query_text is provided, otherwise 0
    query_pattern = f"%{query_text}%" if query_text else ""
    
    cursor.execute(
        """
        SELECT id, round_num, synthesis_text, importance_score, timestamp,
               (? / (1.0 + (? - round_num))) AS recency_score,
               (CASE WHEN ? != '' AND synthesis_text LIKE ? THEN ? ELSE 0 END) AS relevance_score
        FROM reflections
        WHERE agent_name = ?
        """,
        (w_r, current_round, query_pattern, query_pattern, w_v, agent_name)
    )
    
    rows = []
    for row in cursor.fetchall():
        d = dict(row)
        # Score = w_r * Recency + w_i * Importance + w_v * Relevance
        d["total_score"] = d["recency_score"] + (w_i * d["importance_score"]) + d["relevance_score"]
        rows.append(d)
        
    conn.close()
    
    # Sort by total_score descending
    rows.sort(key=lambda x: x["total_score"], reverse=True)
    return rows[:limit]

