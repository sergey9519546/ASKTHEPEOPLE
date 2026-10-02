import csv
import json

from app.services.oasis_profile_generator import OasisAgentProfile
from app.services.simulation_artifacts import (
    build_canonical_agents,
    save_prepare_artifacts,
    write_exports_from_canonical,
)
from app.services.zep_entity_reader import EntityNode


def _entity(uuid, name, label, summary, related_edges=None, related_nodes=None):
    return EntityNode(
        uuid=uuid,
        name=name,
        labels=["Entity", label],
        summary=summary,
        attributes={},
        related_edges=related_edges or [],
        related_nodes=related_nodes or [],
    )


def _profile(user_id, user_name, name, bio, persona, profession):
    return OasisAgentProfile(
        user_id=user_id,
        user_name=user_name,
        name=name,
        bio=bio,
        persona=persona,
        profession=profession,
        age=28,
        gender="female",
        mbti="INTJ",
        country="United States",
        interested_topics=["policy", "housing"],
    )


def test_prepare_artifacts_and_exact_oasis_exports(tmp_path):
    entities = [
        _entity(
            "u1",
            "Alice",
            "Student",
            "Student organizer covering housing issues.",
            related_edges=[{"edge_name": "supports", "fact": "supports tenant union", "target_node_uuid": "u2"}],
        ),
        _entity(
            "u2",
            "City Desk",
            "MediaOutlet",
            "Local media desk following campus policy.",
            related_edges=[{"edge_name": "covers", "fact": "covers housing policy", "target_node_uuid": "u1"}],
        ),
    ]
    profiles = [
        _profile(0, "alice_001", "Alice", "Public-facing bio", "Detailed private persona", "student"),
        _profile(1, "city_desk_002", "City Desk", "Desk bio", "Reporter persona", "journalist"),
    ]

    artifacts = save_prepare_artifacts(str(tmp_path), entities, profiles)
    assert len(artifacts["canonical_agents"]) == 2
    assert artifacts["canonical_agents"][0]["source_entity_type_normalized"] == "student"
    assert artifacts["relationship_bootstrap"]
    graph_record = artifacts["canonical_agents"][0]["graph_records"][0]
    assert graph_record["record_origin"] == "graph_record_origin_unverified"
    assert graph_record["external_validation"] is False
    assert graph_record["causal_evidence"] is False
    assert artifacts["canonical_agents"][0]["source_facts_deprecated"] is True

    relationship = artifacts["relationship_bootstrap"][0]
    assert relationship["assumption_basis"] == "neutral_fictional_default"
    assert relationship["relationship_behavior_inferred"] is False
    assert relationship["record_origin"] == "graph_record_origin_unverified"
    assert relationship["external_validation"] is False
    assert relationship["causal_evidence"] is False

    export_info = write_exports_from_canonical(str(tmp_path), artifacts["canonical_agents"])

    with open(export_info["twitter_path"], "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["user_id"] == "0"
    # Same framing as the reddit persona below — both platforms must describe
    # the same entity the same way. Kept on one line for the CSV format.
    assert "Detailed private persona" in rows[0]["user_char"]
    assert "[Scenario assumption" in rows[0]["user_char"]
    assert "\n" not in rows[0]["user_char"]
    assert list(rows[0].keys()) == ["user_id", "name", "username", "user_char", "description"]

    with open(export_info["reddit_path"], "r", encoding="utf-8") as handle:
        reddit_profiles = json.load(handle)
    assert reddit_profiles[0]["realname"] == "Alice"
    # Persona now includes constraint framing (student role → limited resources).
    # The base persona is still there, plus the structural constraint text.
    assert "Detailed private persona" in reddit_profiles[0]["persona"]
    assert "[Scenario assumption" in reddit_profiles[0]["persona"]
    assert "profession" in reddit_profiles[0]

    canonical = build_canonical_agents(entities, profiles)
    assert canonical[1]["platform_overrides"]["twitter"]["quote_bias"] >= 0


def test_relationship_wording_does_not_change_behavioral_controls(tmp_path):
    entities = [
        _entity(
            "u1",
            "Profile A",
            "Community",
            "Fictional profile seed.",
            related_edges=[
                {
                    "edge_name": "supports",
                    "fact": "Profile A supports Profile B.",
                    "target_node_uuid": "u2",
                }
            ],
        ),
        _entity(
            "u2",
            "Profile B",
            "Community",
            "Fictional profile seed.",
            related_edges=[
                {
                    "edge_name": "opposes",
                    "fact": "Profile B opposes Profile A.",
                    "target_node_uuid": "u1",
                }
            ],
        ),
    ]
    profiles = [
        _profile(0, "profile_a", "Profile A", "Bio A", "Persona A", "community"),
        _profile(1, "profile_b", "Profile B", "Bio B", "Persona B", "community"),
    ]

    relationships = save_prepare_artifacts(
        str(tmp_path),
        entities,
        profiles,
    )["relationship_bootstrap"]

    assert len(relationships) == 2
    assert {item["follow_seed"] for item in relationships} == {0.7}
    assert {item["affinity_score"] for item in relationships} == {0.65}
    assert {item["interaction_bias"] for item in relationships} == {0.65}


# --- run manifest: per-call prompt provenance ----------------------------- #


def test_run_manifest_records_every_prompt_call(tmp_path):
    """ADR-0004 requires a SHA-256 record per model call; it must reach disk.

    These records were built by the generator and then discarded, so the audit
    trail the rule requires did not exist.
    """
    from app.services.simulation_artifacts import (
        read_json,
        run_manifest_path,
        write_run_manifest,
    )

    records = [
        {
            "model": "test-model",
            "prompt_id": "profile_generation",
            "prompt_version": "v1",
            "prompt_sha256": "a" * 64,
            "system_prompt_sha256": "b" * 64,
            "user_prompt_sha256": "c" * 64,
            "output_sha256": "d" * 64,
            "tools_bound": [],
            "structured_output": True,
            "truth_audit": {"passed": True},
            "recorded_at": "2026-10-02T00:00:00",
        },
        {"model": "test-model", "output_sha256": "e" * 64},
    ]
    result = write_run_manifest(str(tmp_path), records)
    assert result["written"] is True

    payload = read_json(run_manifest_path(str(tmp_path)))
    assert payload["prompt_call_count"] == 2
    assert len(payload["prompt_calls"]) == 2
    assert payload["prompt_calls"][0]["prompt_sha256"] == "a" * 64
    assert payload["schema_version"] == 1


def test_run_manifest_with_no_calls_is_still_written(tmp_path):
    from app.services.simulation_artifacts import (
        read_json,
        run_manifest_path,
        write_run_manifest,
    )

    assert write_run_manifest(str(tmp_path), [])["written"] is True
    assert read_json(run_manifest_path(str(tmp_path)))["prompt_call_count"] == 0


def test_prompt_records_are_drained_not_replayed():
    """A second manifest write must not duplicate the first one's rows."""
    import threading

    from app.services.oasis_profile_generator import OasisProfileGenerator

    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)

    generator._prompt_records = [{"output_sha256": "a" * 64}]
    generator._prompt_records_lock = threading.Lock()

    first = generator.drain_prompt_records()
    second = generator.drain_prompt_records()
    assert len(first) == 1
    assert second == []
