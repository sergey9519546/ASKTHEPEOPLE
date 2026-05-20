"""
Shared runtime helpers that turn prepared simulation artifacts into live
OASIS/CAMEL execution behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import random

from .camel_model_factory import create_camel_model, load_model_resolution
from .simulation_artifacts import (
    append_jsonl,
    bootstrap_actions_path,
    read_json,
    relationship_bootstrap_path,
    scheduled_events_path,
)


POST_EVENT_TYPES = {
    "seed_post",
    "official_statement",
    "media_breaking_news",
    "topic_spike",
    "inject_post",
}
FOLLOW_EVENT_TYPES = {"follow_wave"}


REFLECTION_PROMPT = """
You have just completed several hours of simulation. Reflect on your recent interactions, the posts you have seen, and the overall context of the conversation. 
Summarize your current state of mind, your stance on the main topic, and how your sentiment has evolved in 2-3 concise sentences.
"""


def get_reflection_prompt() -> str:
    """Return the standardized reflection prompt."""
    return REFLECTION_PROMPT.strip()


def build_agent_name_lookup(config: Dict[str, Any]) -> Dict[int, str]:
    lookup: Dict[int, str] = {}
    for agent_config in config.get("agent_configs", []):
        agent_id = agent_config.get("agent_id")
        if agent_id is None:
            continue
        lookup[agent_id] = agent_config.get("entity_name", f"Agent_{agent_id}")
    return lookup


def create_actor_model_for_runtime(
    simulation_dir: str,
    prefer_boost: bool = False,
) -> Tuple[Any, Dict[str, Any]]:
    matrix = load_model_resolution(simulation_dir)
    actor_settings = matrix.get("actor", {})
    model = create_camel_model("actor", prefer_boost=prefer_boost)
    return model, actor_settings


def _platform_matches(platform_preference: str, platform: str) -> bool:
    preference = (platform_preference or "both").strip().lower()
    if preference in {"", "both"}:
        return True
    return preference == platform


def _platform_weight(platform_preference: str, platform: str) -> float:
    preference = (platform_preference or "both").strip().lower()
    if preference in {"", "both"}:
        return 1.0
    if preference == platform:
        return 1.15
    return 0.3


def _agent_config_map(config: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {
        agent.get("agent_id"): agent
        for agent in config.get("agent_configs", [])
        if agent.get("agent_id") is not None
    }


def _listify(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _add_action(container: Dict[Any, Any], agent: Any, action: Any) -> None:
    if agent not in container:
        container[agent] = action
        return
    existing = container[agent]
    if isinstance(existing, list):
        existing.append(action)
    else:
        container[agent] = [existing, action]


def _event_platforms_match(platform: str, event_platforms: Any) -> bool:
    if not event_platforms:
        return True
    return platform in {str(item).lower() for item in _listify(event_platforms)}


def _build_event_content(event_type: str, payload: Dict[str, Any]) -> str:
    if payload.get("content"):
        return str(payload["content"]).strip()
    if event_type == "topic_spike":
        topics = [str(topic).strip() for topic in _listify(payload.get("topics")) if str(topic).strip()]
        if topics:
            return f"Topic spike: {', '.join(topics[:3])}"
        return "Topic spike is accelerating across the network."
    if event_type == "official_statement":
        return str(payload.get("statement") or payload.get("summary") or "Official statement released.").strip()
    if event_type == "media_breaking_news":
        return str(payload.get("headline") or payload.get("summary") or "Breaking news is spreading quickly.").strip()
    if event_type == "seed_post":
        return str(payload.get("summary") or "Follow-up seed post.").strip()
    if event_type == "inject_post":
        return str(payload.get("summary") or "Injected post").strip()
    return ""


def _select_target_agent_ids(
    config: Dict[str, Any],
    platform: str,
    targeting: Dict[str, Any],
    fallback_limit: int = 1,
) -> List[int]:
    agent_configs = config.get("agent_configs", [])
    requested_ids = [agent_id for agent_id in _listify(targeting.get("agent_ids")) if isinstance(agent_id, int)]
    poster_agent_id = targeting.get("poster_agent_id")
    if isinstance(poster_agent_id, int):
        requested_ids.insert(0, poster_agent_id)

    unique_ids: List[int] = []
    seen = set()
    for agent_id in requested_ids:
        if agent_id in seen:
            continue
        seen.add(agent_id)
        agent_cfg = next((cfg for cfg in agent_configs if cfg.get("agent_id") == agent_id), None)
        if agent_cfg and _platform_matches(agent_cfg.get("platform_preference", "both"), platform):
            unique_ids.append(agent_id)
    if unique_ids:
        return unique_ids[: max(fallback_limit, 1)]

    roles = {
        str(role).strip().lower()
        for role in _listify(targeting.get("roles"))
        if str(role).strip()
    }
    if roles:
        matched = [
            cfg
            for cfg in agent_configs
            if _platform_matches(cfg.get("platform_preference", "both"), platform)
            and (
                str(cfg.get("normalized_role", "")).lower() in roles
                or str(cfg.get("entity_type", "")).lower() in roles
            )
        ]
        matched.sort(key=lambda cfg: float(cfg.get("influence_weight", 1.0)), reverse=True)
        return [cfg.get("agent_id") for cfg in matched[: max(fallback_limit, 1)]]

    fallback = [
        cfg
        for cfg in agent_configs
        if _platform_matches(cfg.get("platform_preference", "both"), platform)
    ]
    fallback.sort(key=lambda cfg: float(cfg.get("influence_weight", 1.0)), reverse=True)
    return [cfg.get("agent_id") for cfg in fallback[: max(fallback_limit, 1)]]


def select_active_agent_ids(
    config: Dict[str, Any],
    platform: str,
    current_hour: int,
    round_num: int,
    event_boost_agent_ids: Optional[Iterable[int]] = None,
) -> List[int]:
    time_config = config.get("time_config", {})
    agent_configs = config.get("agent_configs", [])
    boost_ids = set(event_boost_agent_ids or [])

    base_min = time_config.get("agents_per_hour_min", 5)
    base_max = time_config.get("agents_per_hour_max", 20)
    peak_hours = set(time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22]))
    off_peak_hours = set(time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5]))
    work_hours = set(time_config.get("work_hours", list(range(9, 19))))

    if current_hour in peak_hours:
        multiplier = time_config.get("peak_activity_multiplier", 1.5)
    elif current_hour in off_peak_hours:
        multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
    else:
        multiplier = 1.0

    target_count = int(random.uniform(base_min, base_max) * multiplier)
    if boost_ids:
        target_count = max(target_count, min(len(agent_configs), len(boost_ids)))

    candidates: List[int] = []
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)
        active_hours = cfg.get("active_hours", list(range(8, 23)))
        if current_hour not in active_hours:
            continue

        platform_preference = cfg.get("platform_preference", "both")
        if not _platform_matches(platform_preference, platform):
            continue

        activity_probability = float(cfg.get("activity_level", 0.5))
        activity_probability *= _platform_weight(platform_preference, platform)

        reaction_style = str(cfg.get("reaction_style", "measured")).lower()
        novelty = float(cfg.get("novelty_seeking", 0.45))
        authority = float(cfg.get("authority_sensitivity", 0.4))
        conflict = float(cfg.get("conflict_tolerance", 0.45))

        if reaction_style in {"reactive", "amplifying"}:
            activity_probability += 0.08
        elif reaction_style == "cautious":
            activity_probability -= 0.05

        if novelty > 0.6:
            activity_probability += 0.05
        if authority > 0.7 and current_hour in work_hours:
            activity_probability += 0.04
        if conflict > 0.6 and round_num > 0:
            activity_probability += 0.03
        if agent_id in boost_ids:
            activity_probability = max(activity_probability, 0.92)

        activity_probability = max(0.02, min(0.98, activity_probability))
        if random.random() < activity_probability:
            candidates.append(agent_id)

    if not candidates:
        return list(boost_ids)[:target_count]
    if len(candidates) <= target_count:
        return candidates
    return random.sample(candidates, min(target_count, len(candidates)))


def _bootstrap_follow_specs(
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
) -> List[Dict[str, Any]]:
    network_bootstrap = config.get("network_bootstrap", {})
    if not network_bootstrap.get("enable_follow_bootstrap", False):
        return []
    if not network_bootstrap.get("platforms", {}).get(platform, True):
        return []

    relationship_bootstrap = read_json(relationship_bootstrap_path(simulation_dir), default=[])
    config_by_agent = _agent_config_map(config)
    follow_density = float(network_bootstrap.get("follow_density", 0.35))
    role_bias_rules = {
        str(key).strip().lower(): float(value)
        for key, value in (network_bootstrap.get("role_bias_rules") or {}).items()
    }
    threshold = max(0.25, 1.0 - follow_density)

    specs: List[Dict[str, Any]] = []
    for relation in relationship_bootstrap:
        if not _event_platforms_match(platform, relation.get("platforms")):
            continue
        source_agent_id = relation.get("source_agent_id")
        target_agent_id = relation.get("target_agent_id")
        if not isinstance(source_agent_id, int) or not isinstance(target_agent_id, int):
            continue
        source_cfg = config_by_agent.get(source_agent_id, {})
        target_cfg = config_by_agent.get(target_agent_id, {})
        if not _platform_matches(source_cfg.get("platform_preference", "both"), platform):
            continue
        if not _platform_matches(target_cfg.get("platform_preference", "both"), platform):
            continue

        role_key = str(source_cfg.get("normalized_role", source_cfg.get("entity_type", ""))).lower()
        role_bias = role_bias_rules.get(role_key, 0.6)
        effective_score = (float(relation.get("follow_seed", 0.0)) * 0.7) + (float(relation.get("affinity_score", 0.0)) * 0.3)
        effective_score *= 0.6 + (role_bias * 0.4)
        if effective_score < threshold:
            continue

        specs.append(
            {
                "event_type": "bootstrap_follow",
                "source_agent_id": source_agent_id,
                "action_type": "FOLLOW",
                "action_args": {"user_id": target_agent_id},
                "content": None,
                "metadata": {
                    "target_agent_id": target_agent_id,
                    "relation_type": relation.get("relation_type"),
                    "follow_seed": relation.get("follow_seed"),
                    "affinity_score": relation.get("affinity_score"),
                },
            }
        )
    return specs


def _bootstrap_post_specs(config: Dict[str, Any], platform: str) -> List[Dict[str, Any]]:
    bootstrap_posts = config.get("bootstrap_posts") or config.get("event_config", {}).get("initial_posts", [])
    specs: List[Dict[str, Any]] = []
    for post in bootstrap_posts:
        poster_agent_id = post.get("poster_agent_id")
        if not isinstance(poster_agent_id, int):
            continue
        target_ids = _select_target_agent_ids(
            config,
            platform,
            {"poster_agent_id": poster_agent_id},
            fallback_limit=1,
        )
        if not target_ids:
            continue
        content = str(post.get("content", "")).strip()
        if not content:
            continue
        specs.append(
            {
                "event_type": "bootstrap_post",
                "source_agent_id": target_ids[0],
                "action_type": "CREATE_POST",
                "action_args": {"content": content},
                "content": content,
                "metadata": {
                    "poster_assignment_confidence": post.get("poster_assignment_confidence"),
                    "poster_assignment_reason": post.get("poster_assignment_reason"),
                    "poster_type": post.get("poster_type"),
                },
            }
        )
    return specs


def bootstrap_boost_agent_ids(simulation_dir: str, config: Dict[str, Any], platform: str) -> List[int]:
    ids = []
    for spec in _bootstrap_follow_specs(simulation_dir, config, platform) + _bootstrap_post_specs(config, platform):
        ids.append(spec["source_agent_id"])
        target_agent_id = spec.get("metadata", {}).get("target_agent_id")
        if isinstance(target_agent_id, int):
            ids.append(target_agent_id)
    return sorted(set(ids))


def _scheduled_event_specs(
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
    current_round: int,
) -> List[Dict[str, Any]]:
    schedule = config.get("event_schedule", [])
    specs: List[Dict[str, Any]] = []
    for event in schedule:
        try:
            trigger_round = int(event.get("trigger_round", -1))
        except (TypeError, ValueError):
            continue
        if trigger_round != current_round:
            continue
        if not _event_platforms_match(platform, event.get("platforms")):
            continue

        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload") or {}
        targeting = event.get("targeting") or {}
        reasoning = event.get("reasoning")

        if event_type in POST_EVENT_TYPES:
            limit = 3 if event_type == "topic_spike" else 1
            target_ids = _select_target_agent_ids(config, platform, targeting, fallback_limit=limit)
            content = _build_event_content(event_type, payload)
            if not content:
                continue
            for agent_id in target_ids:
                specs.append(
                    {
                        "event_type": event_type,
                        "source_agent_id": agent_id,
                        "action_type": "CREATE_POST",
                        "action_args": {"content": content},
                        "content": content,
                        "metadata": {
                            "payload": payload,
                            "targeting": targeting,
                            "reasoning": reasoning,
                        },
                    }
                )
            continue

        if event_type in FOLLOW_EVENT_TYPES:
            relationship_bootstrap = read_json(relationship_bootstrap_path(simulation_dir), default=[])
            source_roles = {
                str(role).strip().lower()
                for role in _listify(targeting.get("source_roles") or targeting.get("roles"))
                if str(role).strip()
            }
            target_roles = {
                str(role).strip().lower()
                for role in _listify(targeting.get("target_roles"))
                if str(role).strip()
            }
            config_by_agent = _agent_config_map(config)
            for relation in relationship_bootstrap:
                if not _event_platforms_match(platform, relation.get("platforms")):
                    continue
                source_cfg = config_by_agent.get(relation.get("source_agent_id"), {})
                target_cfg = config_by_agent.get(relation.get("target_agent_id"), {})
                source_role = str(source_cfg.get("normalized_role", source_cfg.get("entity_type", ""))).lower()
                target_role = str(target_cfg.get("normalized_role", target_cfg.get("entity_type", ""))).lower()
                if source_roles and source_role not in source_roles:
                    continue
                if target_roles and target_role not in target_roles:
                    continue
                specs.append(
                    {
                        "event_type": event_type,
                        "source_agent_id": relation.get("source_agent_id"),
                        "action_type": "FOLLOW",
                        "action_args": {"user_id": relation.get("target_agent_id")},
                        "content": None,
                        "metadata": {
                            "payload": payload,
                            "targeting": targeting,
                            "reasoning": reasoning,
                            "target_agent_id": relation.get("target_agent_id"),
                        },
                    }
                )
    return specs


def scheduled_event_boost_agent_ids(
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
    current_round: int,
) -> List[int]:
    ids = []
    for spec in _scheduled_event_specs(simulation_dir, config, platform, current_round):
        ids.append(spec["source_agent_id"])
        target_agent_id = spec.get("metadata", {}).get("target_agent_id")
        if isinstance(target_agent_id, int):
            ids.append(target_agent_id)
    return sorted(set(ids))


async def _apply_specs(
    env: Any,
    simulation_dir: str,
    platform: str,
    round_num: int,
    specs: Sequence[Dict[str, Any]],
    agent_names: Dict[int, str],
    manual_action_cls: Any,
    action_type_cls: Any,
    event_log_path: str,
    action_logger: Any = None,
) -> int:
    actions: Dict[Any, Any] = {}
    persisted_rows: List[Dict[str, Any]] = []

    for spec in specs:
        source_agent_id = spec.get("source_agent_id")
        if not isinstance(source_agent_id, int):
            continue
        try:
            agent = env.agent_graph.get_agent(source_agent_id)
        except Exception:
            continue

        action_name = str(spec.get("action_type", "")).strip().upper()
        try:
            action_type = getattr(action_type_cls, action_name)
        except AttributeError:
            continue

        action_args = dict(spec.get("action_args") or {})
        action = manual_action_cls(action_type=action_type, action_args=action_args)
        _add_action(actions, agent, action)

        row = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform,
            "round_num": round_num,
            "event_type": spec.get("event_type"),
            "agent_id": source_agent_id,
            "agent_name": agent_names.get(source_agent_id, f"Agent_{source_agent_id}"),
            "content": spec.get("content"),
            "action_type": action_name,
            "action_args": action_args,
        }
        row.update(spec.get("metadata") or {})
        persisted_rows.append(row)

    if not actions:
        return 0

    await env.step(actions)

    for row in persisted_rows:
        append_jsonl(event_log_path, row)
        if action_logger:
            action_logger.log_action(
                round_num=row["round_num"],
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                action_type=row["action_type"],
                action_args=row.get("action_args") or {},
            )

    return len(persisted_rows)


async def apply_bootstrap_actions(
    env: Any,
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
    agent_names: Dict[int, str],
    manual_action_cls: Any,
    action_type_cls: Any,
    action_logger: Any = None,
) -> int:
    specs = _bootstrap_follow_specs(simulation_dir, config, platform) + _bootstrap_post_specs(config, platform)
    return await _apply_specs(
        env=env,
        simulation_dir=simulation_dir,
        platform=platform,
        round_num=0,
        specs=specs,
        agent_names=agent_names,
        manual_action_cls=manual_action_cls,
        action_type_cls=action_type_cls,
        event_log_path=bootstrap_actions_path(simulation_dir),
        action_logger=action_logger,
    )


async def apply_scheduled_events(
    env: Any,
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
    current_round: int,
    agent_names: Dict[int, str],
    manual_action_cls: Any,
    action_type_cls: Any,
    action_logger: Any = None,
) -> int:
    specs = _scheduled_event_specs(simulation_dir, config, platform, current_round)
    return await _apply_specs(
        env=env,
        simulation_dir=simulation_dir,
        platform=platform,
        round_num=current_round,
        specs=specs,
        agent_names=agent_names,
        manual_action_cls=manual_action_cls,
        action_type_cls=action_type_cls,
        event_log_path=scheduled_events_path(simulation_dir),
        action_logger=action_logger,
    )


async def apply_runtime_control(
    env: Any,
    simulation_dir: str,
    config: Dict[str, Any],
    platform: str,
    command_type: str,
    args: Dict[str, Any],
    agent_names: Dict[int, str],
    manual_action_cls: Any,
    action_type_cls: Any,
    round_num: int,
    action_logger: Any = None,
) -> Dict[str, Any]:
    normalized = str(command_type or "").strip().lower()
    specs: List[Dict[str, Any]] = []

    if normalized == "inject_post":
        content = str(args.get("content", "")).strip()
        if not content:
            raise ValueError("inject_post requires content")
        target_ids = _select_target_agent_ids(
            config,
            platform,
            {
                "poster_agent_id": args.get("agent_id"),
                "agent_ids": args.get("agent_ids"),
                "roles": args.get("roles"),
            },
            fallback_limit=max(1, len(_listify(args.get("agent_ids")))) or 1,
        )
        for agent_id in target_ids:
            specs.append(
                {
                    "event_type": "inject_post",
                    "source_agent_id": agent_id,
                    "action_type": "CREATE_POST",
                    "action_args": {"content": content},
                    "content": content,
                    "metadata": {
                        "control_source": "ipc",
                        "reasoning": args.get("reason"),
                    },
                }
            )
    elif normalized == "inject_event":
        event_type = str(args.get("event_type", "")).strip()
        if not event_type:
            raise ValueError("inject_event requires event_type")
        event = {
            "trigger_round": round_num,
            "platforms": args.get("platforms") or [platform],
            "event_type": event_type,
            "payload": args.get("payload") or {},
            "targeting": args.get("targeting") or {},
            "reasoning": args.get("reason"),
        }
        specs = _scheduled_event_specs(simulation_dir, {"agent_configs": config.get("agent_configs", []), "event_schedule": [event]}, platform, round_num)
        for spec in specs:
            spec.setdefault("metadata", {})
            spec["metadata"]["control_source"] = "ipc"
    else:
        raise ValueError(f"unsupported runtime control: {command_type}")

    applied = await _apply_specs(
        env=env,
        simulation_dir=simulation_dir,
        platform=platform,
        round_num=round_num,
        specs=specs,
        agent_names=agent_names,
        manual_action_cls=manual_action_cls,
        action_type_cls=action_type_cls,
        event_log_path=scheduled_events_path(simulation_dir),
        action_logger=action_logger,
    )
    return {"applied_count": applied, "round_num": round_num, "platform": platform}


async def apply_reflection_round(
    env: Any,
    platform: str,
    round_num: int,
    agent_names: Dict[int, str],
    manual_action_cls: Any,
    action_type_cls: Any,
    action_logger: Any = None,
) -> int:
    """
    Trigger a reflection round for all available agents.
    
    Args:
        env: OASIS environment
        platform: Platform name
        round_num: Current round number
        agent_names: Mapping of agent_id to name
        manual_action_cls: OASIS ManualAction class
        action_type_cls: OASIS ActionType class
        action_logger: Optional action logger
        
    Returns:
        Number of agents that reflected
    """
    from oasis import ActionType as OasisActionType
    
    actions: Dict[Any, Any] = {}
    prompt = get_reflection_prompt()

    # Materialise the agent list before stepping to avoid iterating a
    # potentially mutated graph after env.step() returns.
    agent_list = list(env.agent_graph.get_agents())

    for agent_id, agent in agent_list:
        action = manual_action_cls(
            action_type=OasisActionType.INTERVIEW,
            action_args={"prompt": prompt, "is_reflection": True}
        )
        actions[agent] = action

    if not actions:
        return 0

    await env.step(actions)

    if action_logger:
        for agent_id, agent in agent_list:
             action_type_str = "INTERVIEW" # Standard name for logging
             action_logger.log_action(
                 round_num=round_num,
                 agent_id=agent_id,
                 agent_name=agent_names.get(agent_id, f"Agent_{agent_id}"),
                 action_type=action_type_str,
                 action_args={"prompt": prompt, "is_reflection": True},
             )

    return len(actions)
