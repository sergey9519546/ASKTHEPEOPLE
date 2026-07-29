import json
import sqlite3
from types import SimpleNamespace

import pytest

from app.services.report_evidence import (
    _evidence_metadata,
    build_report_evidence,
    load_report_evidence,
)
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
    assert all(item["human_respondents"] == 0 for item in evidence)
    assert all(item["external_validation"] is False for item in evidence)
    assert all(item["causal_evidence"] is False for item in evidence)
    assert all(item["calibration"] == "not_calibrated" for item in evidence)
    assert all("confidence" not in item for item in evidence)
    assert all("trace_id" in item for item in evidence)
    assert all("claim_id" not in item for item in evidence)
    assert len({item["trace_id"] for item in evidence}) == len(evidence)
    assert load_report_evidence(str(report_dir)) == evidence


def test_legacy_claim_keys_are_exposed_as_trace_ids(tmp_path):
    report_dir = tmp_path / "reports" / "report_legacy"
    report_dir.mkdir(parents=True)
    with open(report_dir / "report_evidence.json", "w", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "claim_id": "section_1_claim_2",
                    "source_type": "post",
                    "excerpt": "A generated post",
                    "confidence": 0.82,
                }
            ],
            handle,
        )

    records = load_report_evidence(str(report_dir))
    assert len(records) == 1
    record = records[0]
    assert record["trace_id"] == "section_1_trace_2"
    assert record["source_type"] == "post"
    assert record["excerpt"] == "A generated post"
    assert record["record_type"] == "generated_post"
    assert record["record_origin"] == "synthetic_simulation"
    assert record["human_respondents"] == 0
    assert record["external_validation"] is False
    assert record["causal_evidence"] is False
    assert record["calibration"] == "not_calibrated"
    assert "claim_id" not in record
    assert "confidence" not in record
    assert record["legacy_schema_normalization"] == {
        "deprecated_fields_removed": ["claim_id", "confidence"],
        "score_interpretation": (
            "No probability, likelihood, or evidence-strength score is provided."
        ),
    }


def test_legacy_interview_source_type_is_explicitly_synthetic():
    metadata = _evidence_metadata("interview")

    assert metadata["record_type"] == "generated_profile_response"
    assert metadata["legacy_source_type_deprecated"] is True
    assert metadata["human_respondents"] == 0
    assert metadata["observed_human_behavior"] is False
    assert metadata["causal_evidence"] is False
    assert "not a human interview" in metadata["source_type_interpretation"]


def test_observation_search_clamps_query_and_result_size(tmp_path):
    action_dir = tmp_path / "twitter"
    action_dir.mkdir()
    with open(action_dir / "actions.jsonl", "w", encoding="utf-8") as handle:
        for index in range(250):
            handle.write(json.dumps({
                "round": 1,
                "agent_id": index,
                "agent_name": f"Agent {index}",
                "action_type": "CREATE_POST",
                "action_args": {"content": f"bounded observation {index}"},
                "timestamp": f"2026-03-23T10:{index % 60:02d}:00",
            }) + "\n")

    result = search_observations(
        str(tmp_path),
        query="x" * 1000,
        limit=10_000,
    )
    assert result["query"] == "x" * 500
    assert result["count"] == 0

    all_result = search_observations(str(tmp_path), limit=10_000)
    assert all_result["count"] == 200

    with pytest.raises(ValueError, match="platform"):
        search_observations(str(tmp_path), platform="invalid")
