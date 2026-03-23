"""
Simulation preflight validation.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from ..config import Config
from .camel_model_factory import (
    validate_camel_runtime_imports,
    validate_required_model_env,
    write_model_resolution,
)
from .simulation_artifacts import (
    canonical_agents_path,
    preflight_path,
    read_json,
    validate_reddit_profiles,
    validate_twitter_rows,
)


def _read_twitter_rows(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _validate_config_schema(config: Dict[str, Any]) -> List[str]:
    errors = []
    required_top_level = [
        "simulation_id",
        "project_id",
        "graph_id",
        "time_config",
        "agent_configs",
        "context_profile",
        "network_bootstrap",
        "event_schedule",
        "bootstrap_posts",
        "platform_profiles",
    ]
    for field in required_top_level:
        if field not in config:
            errors.append(f"missing config field: {field}")

    for index, agent in enumerate(config.get("agent_configs", [])):
        for field in (
            "agent_id",
            "entity_uuid",
            "entity_name",
            "entity_type",
            "normalized_role",
            "reaction_style",
            "conflict_tolerance",
            "authority_sensitivity",
            "novelty_seeking",
            "platform_preference",
        ):
            if field not in agent:
                errors.append(f"agent_configs[{index}] missing {field}")

    return errors


def run_preflight(simulation_dir: str) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, passed: bool, details: Any = None):
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "failed",
                "details": details,
            }
        )

    canonical_agents = read_json(canonical_agents_path(simulation_dir), default=[])
    canonical_errors = []
    expected_ids = list(range(len(canonical_agents)))
    actual_ids = [agent.get("agent_id") for agent in canonical_agents]
    if actual_ids != expected_ids:
        canonical_errors.append(f"canonical agent ids must be contiguous {expected_ids}, got {actual_ids}")
    add_check("canonical_agent_integrity", not canonical_errors, canonical_errors or {"count": len(canonical_agents)})

    twitter_rows = _read_twitter_rows(os.path.join(simulation_dir, "twitter_profiles.csv"))
    twitter_errors = validate_twitter_rows(twitter_rows) if twitter_rows else ["twitter export missing"]
    add_check("twitter_export_contract", not twitter_errors, twitter_errors or {"count": len(twitter_rows)})

    reddit_profiles = read_json(os.path.join(simulation_dir, "reddit_profiles.json"), default=[])
    reddit_errors = validate_reddit_profiles(reddit_profiles) if reddit_profiles else ["reddit export missing"]
    add_check("reddit_export_contract", not reddit_errors, reddit_errors or {"count": len(reddit_profiles)})

    config = read_json(os.path.join(simulation_dir, "simulation_config.json"), default={})
    config_errors = _validate_config_schema(config) if config else ["simulation_config.json missing"]
    add_check("config_schema", not config_errors, config_errors or {"agents": len(config.get("agent_configs", []))})

    poster_errors = []
    valid_agent_ids = set(expected_ids)
    for index, post in enumerate(config.get("bootstrap_posts", [])):
        if post.get("poster_agent_id") not in valid_agent_ids:
            poster_errors.append(f"bootstrap_posts[{index}] has invalid poster_agent_id")
    add_check("poster_assignment", not poster_errors, poster_errors or {"count": len(config.get("bootstrap_posts", []))})

    prefer_boost_for_actor = bool(os.environ.get("LLM_BOOST_API_KEY"))
    model_matrix = write_model_resolution(
        simulation_dir,
        prefer_boost_for_actor=prefer_boost_for_actor,
    )
    model_errors = []
    for role in ("actor", "interview", "curator", "report"):
        model_errors.extend(
            validate_required_model_env(
                role,
                prefer_boost=prefer_boost_for_actor and role == "actor",
            )
        )
    add_check("model_adapter_resolution", not model_errors, model_errors or model_matrix)

    env_errors = Config.validate()
    add_check("required_env", not env_errors, env_errors or {"validated": True})

    import_errors = validate_camel_runtime_imports()
    add_check("oasis_imports", not import_errors, import_errors or {"validated": True})

    failed_checks = [check["name"] for check in checks if check["status"] != "passed"]
    payload = {
        "status": "passed" if not failed_checks else "failed",
        "generated_at": datetime.now().isoformat(),
        "checks": checks,
        "failed_checks": failed_checks,
    }
    with open(preflight_path(simulation_dir), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return payload
