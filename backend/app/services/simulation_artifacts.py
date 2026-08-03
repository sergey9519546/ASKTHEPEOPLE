"""
Shared simulation artifact builders and validators.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, Sequence

from .claim_boundary import graph_record_disclosure
from .oasis_profile_generator import OasisAgentProfile
from .role_normalizer import build_entity_type_registry, normalize_entity_type
from .zep_entity_reader import EntityNode


CANONICAL_AGENTS_FILENAME = "agent_profiles.canonical.json"
ENTITY_TYPE_REGISTRY_FILENAME = "entity_type_registry.json"
RELATIONSHIP_BOOTSTRAP_FILENAME = "agent_relationship_bootstrap.json"
PREFLIGHT_FILENAME = "preflight.json"
RUN_MANIFEST_FILENAME = "run_manifest.json"
BOOTSTRAP_ACTIONS_FILENAME = "bootstrap_actions.jsonl"
SCHEDULED_EVENTS_FILENAME = "scheduled_events_applied.jsonl"
OBSERVATION_DB_FILENAME = "simulation_observations.db"
REPORT_EVIDENCE_FILENAME = "report_evidence.json"

TWITTER_FIELDS = ["user_id", "name", "username", "user_char", "description"]
REDDIT_REQUIRED_FIELDS = [
    "realname",
    "username",
    "bio",
    "persona",
    "age",
    "gender",
    "mbti",
    "country",
]
REDDIT_OPTIONAL_FIELDS = ["profession", "interested_topics"]


def append_jsonl(path: str, row: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def canonical_agents_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, CANONICAL_AGENTS_FILENAME)


def entity_type_registry_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, ENTITY_TYPE_REGISTRY_FILENAME)


def relationship_bootstrap_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, RELATIONSHIP_BOOTSTRAP_FILENAME)


def preflight_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, PREFLIGHT_FILENAME)


def run_manifest_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, RUN_MANIFEST_FILENAME)


def bootstrap_actions_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, BOOTSTRAP_ACTIONS_FILENAME)


def scheduled_events_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, SCHEDULED_EVENTS_FILENAME)


def observation_db_path(simulation_dir: str) -> str:
    return os.path.join(simulation_dir, OBSERVATION_DB_FILENAME)


def report_evidence_path(report_dir: str) -> str:
    return os.path.join(report_dir, REPORT_EVIDENCE_FILENAME)


def _normalize_gender(value: str | None) -> str:
    if not value:
        return "other"
    normalized = value.strip().lower()
    if normalized in {"male", "m"}:
        return "male"
    if normalized in {"female", "f"}:
        return "female"
    return "other"


def _build_platform_overrides(role_info: Dict[str, Any]) -> Dict[str, Any]:
    """Return neutral fictional controls; role metadata is structural only."""
    twitter = {
        "repost_bias": 0.35,
        "quote_bias": 0.25,
        "post_brevity": "medium",
        "follow_bias": 0.45,
        "assumption_basis": "neutral_fictional_default",
    }
    reddit = {
        "comment_depth_bias": 0.55,
        "threading_bias": 0.55,
        "search_bias": 0.4,
        "vote_bias": 0.5,
        "assumption_basis": "neutral_fictional_default",
    }

    return {
        "twitter": twitter,
        "reddit": reddit,
        "methodology": {
            "human_respondents": 0,
            "role_behavior_inferred": False,
            "disclosure": (
                "Neutral fictional platform controls; no role-based behavior, "
                "platform preference, public opinion, or forecast is inferred."
            ),
        },
    }


def _build_activity_seed(role_info: Dict[str, Any]) -> Dict[str, Any]:
    """Return a neutral fictional activity seed for every structural role."""
    return {
        "base_activity_level": 0.55,
        "reaction_style": "measured",
        "conflict_tolerance": 0.45,
        "authority_sensitivity": 0.4,
        "novelty_seeking": 0.45,
        "platform_preference": "both",
        "assumption_basis": "neutral_fictional_default",
        "human_respondents": 0,
        "role_behavior_inferred": False,
        "disclosure": (
            "Neutral fictional activity controls; role labels do not supply "
            "behavioral evidence or representative patterns."
        ),
    }


def _build_graph_records(entity: EntityNode) -> list[Dict[str, Any]]:
    results: list[Dict[str, Any]] = []
    seen = set()

    def add_record(kind: str, text: str, ref: str) -> None:
        normalized = (text or "").strip()
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        results.append(
            {
                "kind": kind,
                "text": normalized,
                "ref": ref,
                **graph_record_disclosure(normalized),
            }
        )

    add_record("summary", entity.summary, f"entity:{entity.uuid}")
    for index, edge in enumerate(entity.related_edges[:18]):
        add_record(
            "edge_record",
            edge.get("fact") or edge.get("edge_name") or "",
            f"edge:{entity.uuid}:{index}",
        )
    for related in entity.related_nodes[:10]:
        add_record(
            "related_entity_record",
            related.get("summary") or related.get("name") or "",
            f"node:{related.get('uuid', '')}",
        )
    return results


def _build_source_facts(entity: EntityNode) -> list[Dict[str, Any]]:
    """Deprecated compatibility alias for disclosed graph records."""
    return _build_graph_records(entity)


def build_canonical_agents_from_profiles(
    profiles: Sequence[OasisAgentProfile],
) -> list[Dict[str, Any]]:
    """Build canonical agents from profiles alone (no EntityNode required).

    Used for archetype-expanded variant agents that have no backing EntityNode.
    Output shape is identical to build_canonical_agents() but with empty graph
    records and neutral role defaults.
    """
    neutral_role_info = normalize_entity_type("entity")
    canonical: list[Dict[str, Any]] = []
    for agent_id, profile in enumerate(profiles):
        role_info = normalize_entity_type(profile.source_entity_type or "entity") if profile.source_entity_type else neutral_role_info
        canonical.append(
            {
                "agent_id": agent_id,
                "source_entity_uuid": profile.source_entity_uuid,
                "source_entity_type_raw": profile.source_entity_type or "entity",
                "source_entity_type_normalized": role_info["normalized_role"],
                "display_name": profile.name,
                "username": profile.user_name,
                "public_bio": (profile.bio or profile.name).replace("\n", " ").strip(),
                "internal_persona": (profile.persona or profile.bio or profile.name).replace("\n", " ").strip(),
                "profession": profile.profession or role_info["normalized_role"],
                "age": profile.age or 30,
                "gender": _normalize_gender(profile.gender),
                # effective_mbti() derives the code from Big Five traits when
                # present, so personality is not silently flattened to the
                # placeholder on the path that feeds OASIS.
                "mbti": profile.effective_mbti(),
                # Substantive personality representation. None when not
                # source-derived; never fabricated.
                "big_five": profile.big_five,
                "country": profile.country or "Unknown",
                "interested_topics": profile.interested_topics or [],
                "stance_seed": "neutral",
                "activity_seed": _build_activity_seed(role_info),
                "platform_overrides": _build_platform_overrides(role_info),
                "graph_records": [],
                # Deprecated compatibility alias; records remain fully disclosed.
                "source_facts": [],
                "source_facts_deprecated": True,
            }
        )
    return canonical


def build_canonical_agents(
    entities: Sequence[EntityNode],
    profiles: Sequence[OasisAgentProfile],
) -> list[Dict[str, Any]]:
    canonical: list[Dict[str, Any]] = []
    for agent_id, (entity, profile) in enumerate(zip(entities, profiles)):
        role_info = normalize_entity_type(entity.get_entity_type())
        graph_records = _build_graph_records(entity)
        canonical.append(
            {
                "agent_id": agent_id,
                "source_entity_uuid": entity.uuid,
                "source_entity_type_raw": entity.get_entity_type() or "Unknown",
                "source_entity_type_normalized": role_info["normalized_role"],
                "display_name": profile.name,
                "username": profile.user_name,
                "public_bio": (profile.bio or f"{profile.name}").replace("\n", " ").strip(),
                "internal_persona": (profile.persona or profile.bio or profile.name).replace("\n", " ").strip(),
                "profession": profile.profession or role_info["normalized_role"],
                "age": profile.age or 30,
                "gender": _normalize_gender(profile.gender),
                # effective_mbti() derives the code from Big Five traits when
                # present, so personality is not silently flattened to the
                # placeholder on the path that feeds OASIS.
                "mbti": profile.effective_mbti(),
                # Substantive personality representation. None when not
                # source-derived; never fabricated.
                "big_five": profile.big_five,
                "country": profile.country or "Unknown",
                "interested_topics": profile.interested_topics or [],
                "stance_seed": "neutral",
                "activity_seed": _build_activity_seed(role_info),
                "platform_overrides": _build_platform_overrides(role_info),
                "graph_records": graph_records,
                # Deprecated compatibility alias; records remain fully disclosed.
                "source_facts": graph_records,
                "source_facts_deprecated": True,
            }
        )
    return canonical


def build_relationship_bootstrap(
    entities: Sequence[EntityNode],
    canonical_agents: Sequence[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    uuid_to_agent = {agent["source_entity_uuid"]: agent["agent_id"] for agent in canonical_agents}
    relationships: list[Dict[str, Any]] = []
    seen = set()
    for entity in entities:
        source_agent_id = uuid_to_agent.get(entity.uuid)
        if source_agent_id is None:
            continue
        for edge in entity.related_edges:
            target_uuid = edge.get("target_node_uuid") or edge.get("source_node_uuid")
            target_agent_id = uuid_to_agent.get(target_uuid)
            if target_agent_id is None or target_agent_id == source_agent_id:
                continue
            relation_type = edge.get("edge_name") or edge.get("fact") or "related_to"
            dedupe_key = (source_agent_id, target_agent_id, relation_type)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            record_text = edge.get("fact") or edge.get("edge_name") or ""
            # Neutral values are fictional run controls. Relation wording must
            # never be converted into behavioral propensity or causal weight.
            follow_seed = 0.7
            interaction_bias = 0.65
            relationships.append(
                {
                    "source_agent_id": source_agent_id,
                    "target_agent_id": target_agent_id,
                    "relation_type": relation_type,
                    "affinity_score": round(interaction_bias, 2),
                    "platforms": ["twitter", "reddit"],
                    "follow_seed": round(follow_seed, 2),
                    "interaction_bias": round(interaction_bias, 2),
                    "assumption_basis": "neutral_fictional_default",
                    "relationship_behavior_inferred": False,
                    **graph_record_disclosure(record_text),
                    "source_graph_records": [
                        graph_record_disclosure(record_text)
                    ],
                    # Deprecated compatibility alias. The adjacent metadata
                    # prevents this string from being treated as a verified fact.
                    "source_edge_refs": [record_text],
                    "source_edge_refs_deprecated": True,
                }
            )
    return relationships


def save_prepare_artifacts(
    simulation_dir: str,
    entities: Sequence[EntityNode],
    profiles: Sequence[OasisAgentProfile],
) -> Dict[str, Any]:
    registry = build_entity_type_registry(entities)
    canonical_agents = build_canonical_agents(entities, profiles)
    relationships = build_relationship_bootstrap(entities, canonical_agents)
    write_json(entity_type_registry_path(simulation_dir), registry)
    write_json(canonical_agents_path(simulation_dir), canonical_agents)
    write_json(relationship_bootstrap_path(simulation_dir), relationships)
    return {
        "entity_type_registry": registry,
        "canonical_agents": canonical_agents,
        "relationship_bootstrap": relationships,
    }


def canonical_to_twitter_rows(canonical_agents: Sequence[Dict[str, Any]]) -> list[Dict[str, Any]]:
    rows = []
    for agent in canonical_agents:
        rows.append(
            {
                "user_id": agent["agent_id"],
                "name": agent["display_name"],
                "username": agent["username"],
                "user_char": agent["internal_persona"],
                "description": agent["public_bio"],
            }
        )
    return rows


def canonical_to_reddit_profiles(canonical_agents: Sequence[Dict[str, Any]]) -> list[Dict[str, Any]]:
    profiles = []
    for agent in canonical_agents:
        # Layer 1: prospect-theory risk framing (from Big Five traits)
        # Layer 2: structural constraint framing (from entity role type)
        # Both reach the OASIS agent system prompt via:
        #   agents_generator.py  profile["other_info"]["user_profile"] = agent_info[i]["persona"]
        # Deterministic, no model call; absent traits/roles leave persona unchanged.
        try:
            from .trait_behavior_projection import (
                persona_with_framing,
                persona_with_constraint_framing,
            )
            persona_text = persona_with_framing(agent["internal_persona"], agent)
            # Pass the normalized role STRING directly — re-normalizing it
            # round-trips through role_normalizer, which does not recognize
            # normalized roles ("individual", "organization") as inputs and
            # would silently degrade them to entity/unknown.
            role_key = (
                agent.get("source_entity_type_normalized")
                or agent.get("source_entity_type_raw")
                or agent.get("entity_type")
                or "entity"
            )
            persona_text = persona_with_constraint_framing(persona_text, role_key)
        except Exception:
            persona_text = agent["internal_persona"]

        profile = {
            "realname": agent["display_name"],
            "username": agent["username"],
            "bio": agent["public_bio"],
            "persona": persona_text,
            "age": int(agent["age"]),
            "gender": _normalize_gender(agent.get("gender")),
            "mbti": agent["mbti"],
            "country": agent["country"],
        }
        if agent.get("profession"):
            profile["profession"] = agent["profession"]
        if agent.get("interested_topics"):
            profile["interested_topics"] = agent["interested_topics"]
        profiles.append(profile)
    return profiles


def validate_twitter_rows(rows: Sequence[Dict[str, Any]]) -> list[str]:
    errors = []
    for index, row in enumerate(rows):
        if list(row.keys()) != TWITTER_FIELDS:
            errors.append(f"twitter row {index}: fields must be exactly {TWITTER_FIELDS}")
        for field in TWITTER_FIELDS:
            if field not in row:
                errors.append(f"twitter row {index}: missing {field}")
        if str(row.get("user_id")) != str(index):
            errors.append(f"twitter row {index}: user_id must match canonical order")
    return errors


def validate_reddit_profiles(profiles: Sequence[Dict[str, Any]]) -> list[str]:
    errors = []
    allowed = set(REDDIT_REQUIRED_FIELDS + REDDIT_OPTIONAL_FIELDS)
    for index, profile in enumerate(profiles):
        missing = [field for field in REDDIT_REQUIRED_FIELDS if field not in profile]
        if missing:
            errors.append(f"reddit profile {index}: missing {missing}")
        extra = [field for field in profile.keys() if field not in allowed]
        if extra:
            errors.append(f"reddit profile {index}: unexpected fields {extra}")
    return errors


def write_exports_from_canonical(simulation_dir: str, canonical_agents: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    twitter_rows = canonical_to_twitter_rows(canonical_agents)
    reddit_profiles = canonical_to_reddit_profiles(canonical_agents)
    twitter_errors = validate_twitter_rows(twitter_rows)
    reddit_errors = validate_reddit_profiles(reddit_profiles)
    if twitter_errors or reddit_errors:
        raise ValueError("; ".join(twitter_errors + reddit_errors))

    twitter_path = os.path.join(simulation_dir, "twitter_profiles.csv")
    with open(twitter_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TWITTER_FIELDS)
        writer.writeheader()
        writer.writerows(twitter_rows)

    reddit_path = os.path.join(simulation_dir, "reddit_profiles.json")
    write_json(reddit_path, reddit_profiles)
    return {
        "twitter_path": twitter_path,
        "reddit_path": reddit_path,
        "twitter_rows": twitter_rows,
        "reddit_profiles": reddit_profiles,
    }
