"""
Follower Engine — Lightweight rule-based follower agents for OASIS simulations.

Follower agents are computed in the Flask monitor thread after each OASIS round
and written to separate follower_actions.jsonl files. They never run inside the
OASIS subprocess — zero changes to OASIS scripts.
"""

from __future__ import annotations

import random as _random_module
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Module-level handle so tests can seed determinism without touching the
# interpreter-global RNG — every stochastic draw in this module goes through
# this name. The stdlib module is bound privately as `_random_module` so that
# nothing can rebind a bare `random` attribute on this module and shadow the
# real module object underneath it.
_rng = _random_module


class FollowerBehavior(str, Enum):
    AMPLIFIER = "AMPLIFIER"
    CONTRARIAN = "CONTRARIAN"
    NEUTRAL = "NEUTRAL"
    LURKER = "LURKER"


@dataclass
class FollowerAgent:
    agent_id: int
    agent_name: str
    behavior_type: FollowerBehavior
    opinion_bias: float          # -1.0 to +1.0
    activity_probability: float  # 0.0 to 1.0
    # Role/topic-varied display name from the compositional matrix. None on
    # agents built before the matrix existed; the old agent_name stays the
    # unique identifier either way.
    display_name: Optional[str] = None


_CONTRARIAN_PHRASES = [
    "I strongly disagree.",
    "The opposite is more likely.",
    "This seems misguided.",
    "Skeptical of this view.",
]


class FollowerEngine:
    """Generates follower agents and computes their per-round actions."""

    DEFAULT_DISTRIBUTION: Dict[str, float] = {
        "AMPLIFIER": 0.3,
        "CONTRARIAN": 0.2,
        "NEUTRAL": 0.4,
        "LURKER": 0.1,
    }

    def __init__(self, id_base: int = 1000):
        self.id_base = id_base

    def generate_followers(
        self,
        count: int,
        distribution: Optional[Dict[str, float]] = None,
    ) -> List[FollowerAgent]:
        """
        Generate `count` follower agents with stochastic behavior assignment.

        Args:
            count: Number of follower agents to generate
            distribution: Optional dict mapping behavior name → weight (must sum to ~1.0)

        Returns:
            List of FollowerAgent instances
        """
        dist = distribution or self.DEFAULT_DISTRIBUTION
        behaviors = list(FollowerBehavior)
        weights = [dist.get(b.value, 0.0) for b in behaviors]

        # Role/topic-varied display names from the compositional matrix. A
        # 45,000-follower crowd of "Follower 42" names reads as a counter,
        # not characters; role rotation fixes that while staying
        # deterministic and unique (agent_name remains the identifier).
        try:
            from .persona_composition import compose_display_name
            from .role_normalizer import normalize_entity_type
            compose_names = True
        except Exception:  # pragma: no cover - matrix must never break a run
            compose_names = False
        role_rotation = [
            normalize_entity_type(role_key)
            for role_key in (
                "resident", "citizen", "worker", "parent", "individual",
                "volunteer", "student", "neighborhood",
            )
        ] if compose_names else []

        agents: List[FollowerAgent] = []
        for i in range(count):
            behavior = _rng.choices(behaviors, weights=weights, k=1)[0]

            if behavior == FollowerBehavior.AMPLIFIER:
                opinion_bias = _rng.uniform(0.3, 1.0)
                activity_prob = _rng.uniform(0.5, 0.9)
            elif behavior == FollowerBehavior.CONTRARIAN:
                opinion_bias = _rng.uniform(-1.0, -0.3)
                activity_prob = _rng.uniform(0.4, 0.8)
            elif behavior == FollowerBehavior.NEUTRAL:
                opinion_bias = _rng.uniform(-0.2, 0.2)
                activity_prob = _rng.uniform(0.2, 0.6)
            else:  # LURKER
                opinion_bias = _rng.uniform(-0.5, 0.5)
                activity_prob = _rng.uniform(0.02, 0.1)

            display_name = None
            if compose_names and role_rotation:
                display_name = compose_display_name(
                    archetype_id=0,
                    variant_index=i,
                    role_info=role_rotation[i % len(role_rotation)],
                )

            agents.append(
                FollowerAgent(
                    agent_id=self.id_base + i,
                    agent_name=f"follower_{behavior.value.lower()}_{i:04d}",
                    behavior_type=behavior,
                    opinion_bias=opinion_bias,
                    activity_probability=activity_prob,
                    display_name=display_name,
                )
            )
        return agents

    def compute_round_actions(
        self,
        followers: List[FollowerAgent],
        round_actions: List[Dict[str, Any]],
        round_num: int,
        platform: str,
        max_actions: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute follower actions for one round based on leader actions.

        Args:
            followers: List of follower agents
            round_actions: Raw action dicts from this round's leader agents
            round_num: Current round number
            platform: "twitter" or "reddit"
            max_actions: Optional ceiling on actions returned this round.
                An uncapped 45,000-follower crowd produces ~18,000 writes per
                round — pure volume, no additional signal. When the computed
                set exceeds the ceiling, a deterministic (platform, round)-
                seeded reduction keeps a stable subset, so the same round
                always keeps the same followers and the log volume stays
                bounded (Config.TIER4_CROWD_ACTIONS_PER_ROUND_MAX).

        Returns:
            List of follower action dicts (same schema as actions.jsonl entries)
        """
        # Collect candidate actions followers can react to
        reactive_types = {"CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"}
        candidates = [a for a in round_actions if a.get("action_type") in reactive_types]

        result: List[Dict[str, Any]] = []
        now = datetime.now().isoformat()

        for follower in followers:
            if _rng.random() >= follower.activity_probability:
                continue
            if not candidates:
                continue

            target = _rng.choice(candidates)
            target_args = target.get("action_args") or {}

            action_type, action_args = self._pick_action(follower, target, target_args, platform)

            result.append(
                {
                    "round": round_num,
                    "timestamp": now,
                    "platform": platform,
                    "agent_id": follower.agent_id,
                    "agent_name": follower.agent_name,
                    "action_type": action_type,
                    "action_args": action_args,
                    "result": None,
                    "success": True,
                    "is_follower": True,
                }
            )

        if max_actions is not None and len(result) > max_actions:
            # Deterministic per-round down-sample: the same (platform, round)
            # always keeps the same subset, sorted back into agent order so
            # the log reads in a stable sequence.
            rng = _random_module.Random(f"{platform}:{round_num}")
            keep = sorted(rng.sample(range(len(result)), max_actions))
            result = [result[i] for i in keep]
        return result

    @staticmethod
    def _pick_action(
        follower: FollowerAgent,
        target: Dict[str, Any],
        target_args: Dict[str, Any],
        platform: str,
    ):
        """Return (action_type, action_args) for one follower reaction."""
        post_id = target_args.get("tweet_id") or target_args.get("post_id") or ""
        content = str(target_args.get("content") or target_args.get("tweet_content") or "")

        behavior = follower.behavior_type

        if platform == "twitter":
            if behavior == FollowerBehavior.AMPLIFIER:
                if _rng.random() < 0.6:
                    return "LIKE_POST", {"tweet_id": post_id}
                else:
                    return "REPOST", {"tweet_id": post_id}
            elif behavior == FollowerBehavior.CONTRARIAN:
                phrase = _rng.choice(_CONTRARIAN_PHRASES)
                return "QUOTE_POST", {
                    "tweet_id": post_id,
                    "content": f"Disagree: {content[:50]} — {phrase}",
                }
            elif behavior == FollowerBehavior.NEUTRAL:
                if _rng.random() < 0.5:
                    return "LIKE_POST", {"tweet_id": post_id}
                else:
                    return "DO_NOTHING", {}
            else:  # LURKER
                return "DO_NOTHING", {}

        else:  # reddit
            if behavior == FollowerBehavior.AMPLIFIER:
                return "LIKE_POST", {"post_id": post_id}
            elif behavior == FollowerBehavior.CONTRARIAN:
                if _rng.random() < 0.5:
                    return "DISLIKE_POST", {"post_id": post_id}
                else:
                    phrase = _rng.choice(_CONTRARIAN_PHRASES)
                    return "CREATE_COMMENT", {"post_id": post_id, "content": phrase}
            elif behavior == FollowerBehavior.NEUTRAL:
                if _rng.random() < 0.5:
                    return "LIKE_POST", {"post_id": post_id}
                else:
                    return "DO_NOTHING", {}
            else:  # LURKER
                return "DO_NOTHING", {}


def apply_follower_round_in_proc(
    db_conn: Any,
    followers: List[FollowerAgent],
    round_actions: List[Dict[str, Any]],
    round_num: int,
    platform: str,
    max_actions: Optional[int] = None,
) -> int:
    """
    Executes follower reactions in-process against the active OASIS SQLite DB connection if provided.
    Inserts follower posts, comments, likes, and reposts directly into DB tables.
    Returns the total count of follower actions written.
    """
    if not db_conn or not followers or not round_actions:
        return 0

    engine = FollowerEngine()
    follower_actions = engine.compute_round_actions(
        followers, round_actions, round_num, platform, max_actions=max_actions
    )
    
    written = 0
    try:
        cursor = db_conn.cursor()
        for act in follower_actions:
            atype = act.get("action_type")
            aargs = act.get("action_args") or {}
            
            if atype == "LIKE_POST" and ("tweet_id" in aargs or "post_id" in aargs):
                pid = aargs.get("tweet_id") or aargs.get("post_id")
                cursor.execute(
                    "INSERT OR IGNORE INTO likes (user_id, post_id, created_at) VALUES (?, ?, ?)",
                    (act["agent_id"], pid, act["timestamp"])
                )
                written += 1
            elif atype == "REPOST" and "tweet_id" in aargs:
                cursor.execute(
                    "INSERT OR IGNORE INTO reposts (user_id, tweet_id, created_at) VALUES (?, ?, ?)",
                    (act["agent_id"], aargs["tweet_id"], act["timestamp"])
                )
                written += 1
        db_conn.commit()
    except Exception:
        # Ignore if tables differ slightly between platforms
        pass

    return written

