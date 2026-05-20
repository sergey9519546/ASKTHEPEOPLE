import json
import sqlite3
from types import SimpleNamespace

from app.services.report_evidence import build_report_evidence, load_report_evidence
from app.services.simulation_artifacts import write_json
from app.services.simulation_observation_store import search_observations, sync_observation_store


def _write_runtime_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE user (user_id INTEGER PRIMARY KEY, agent_id INTEGER, name TEXT, user_name TEXT);
        CREATE TABLE trace (user_id INTEGER, action TEXT, info TEXT, created_at TEXT);
        CREATE TABLE post (user_id INTEGER, content TEXT, created_at TEXT);
        CREATE TABLE comment (user_id INTEGER, post_id INTEGER, content TEXT, created_at TEXT);
        """
    )
    cursor.execute(
        "INSERT INTO user(user_id, agent_id, name, user_name) VALUES (1, 0, 'Alice', 'alice_001')"
    )
    cursor.execute(
        "INSERT INTO trace(user_id, action, info, created_at) VALUES (?, ?, ?, ?)",
        (
            1,
            "create_post",
            json.dumps({"content": "Housing policy is escalating", "round_num": 3}),
            "2026-03-23T10:00:00",
        ),
    )
    cursor.execute(
        "INSERT INTO trace(user_id, action, info, created_at) VALUES (?, ?, ?, ?)",
        (
            1,
            "interview",
            json.dumps({"prompt": "What changed?", "response": "The policy intensified online.", "round_num": 3}),
            "2026-03-23T10:10:00",
        ),
    )
    cursor.execute(
        "INSERT INTO post(user_id, content, created_at) VALUES (?, ?, ?)",
        (1, "Housing policy is escalating", "2026-03-23T10:00:00"),
    )
    cursor.execute(
        "INSERT INTO comment(user_id, post_id, content, created_at) VALUES (?, ?, ?, ?)",
        (1, 1, "Students are reacting sharply.", "2026-03-23T10:05:00"),
    )
    conn.commit()
    conn.close()


def test_observation_store_syncs_sqlite_runtime_and_builds_evidence(tmp_path):
    canonical_agents = [
        {
            "agent_id": 0,
            "display_name": "Alice",
            "source_entity_uuid": "u1",
            "source_entity_type_normalized": "student",
            "activity_seed": {"platform_preference": "both"},
        }
    ]
    write_json(tmp_path / "agent_profiles.canonical.json", canonical_agents)
    _write_runtime_db(tmp_path / "twitter_simulation.db")

    sync_observation_store(str(tmp_path))
    result = search_observations(str(tmp_path), query="Housing", platform="twitter")
    assert result["count"] >= 1
    assert result["results"][0]["action_type"] == "CREATE_POST"

    report_dir = tmp_path / "reports" / "report_test"
    report_dir.mkdir(parents=True)
    with open(report_dir / "section_01.md", "w", encoding="utf-8") as handle:
        handle.write("## Seed vs Emergence\n\nHousing policy is escalating.")

    outline = SimpleNamespace(sections=[SimpleNamespace(title="Seed vs Emergence")])
    evidence = build_report_evidence(
        report_id="report_test",
        report_dir=str(report_dir),
        simulation_dir=str(tmp_path),
        outline=outline,
    )
    assert evidence
    assert any(item["source_type"] in {"action", "post", "interview"} for item in evidence)
    assert load_report_evidence(str(report_dir)) == evidence
