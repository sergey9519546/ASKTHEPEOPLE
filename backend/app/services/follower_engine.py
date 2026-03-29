"""
Follower Engine — Lightweight rule-based follower agents for OASIS simulations.

Follower agents are computed in the Flask monitor thread after each OASIS round
and written to separate follower_actions.jsonl files. They never run inside the
OASIS subprocess — zero changes to OASIS scripts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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

        agents: List[FollowerAgent] = []
        for i in range(count):
            behavior = random.choices(behaviors, weights=weights, k=1)[0]

            if behavior == FollowerBehavior.AMPLIFIER:
                opinion_bias = random.uniform(0.3, 1.0)
                activity_prob = random.uniform(0.5, 0.9)
            elif behavior == FollowerBehavior.CONTRARIAN:
                opinion_bias = random.uniform(-1.0, -0.3)
                activity_prob = random.uniform(0.4, 0.8)
            elif behavior == FollowerBehavior.NEUTRAL:
                opinion_bias = random.uniform(-0.2, 0.2)
                activity_prob = random.uniform(0.2, 0.6)
            else:  # LURKER
                opinion_bias = random.uniform(-0.5, 0.5)
                activity_prob = random.uniform(0.02, 0.1)

            agents.append(
                FollowerAgent(
                    agent_id=self.id_base + i,
                    agent_name=f"follower_{behavior.value.lower()}_{i:04d}",
                    behavior_type=behavior,
                    opinion_bias=opinion_bias,
                    activity_probability=activity_prob,
                )
            )
        return agents

    def compute_round_actions(
        self,
        followers: List[FollowerAgent],
        round_actions: List[Dict[str, Any]],
        round_num: int,
        platform: str,
    ) -> List[Dict[str, Any]]:
        """
        Compute follower actions for one round based on leader actions.

        Args:
            followers: List of follower agents
            round_actions: Raw action dicts from this round's leader agents
            round_num: Current round number
            platform: "twitter" or "reddit"

        Returns:
            List of follower action dicts (same schema as actions.jsonl entries)
        """
        # Collect candidate actions followers can react to
        reactive_types = {"CREATE_POST", "QUOTE_POST", "CREATE_COMMENT"}
        candidates = [a for a in round_actions if a.get("action_type") in reactive_types]

        result: List[Dict[str, Any]] = []
        now = datetime.now().isoformat()

        for follower in followers:
            if random.random() >= follower.activity_probability:
                continue
            if not candidates:
                continue

            target = random.choice(candidates)
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
                if random.random() < 0.6:
                    return "LIKE_POST", {"tweet_id": post_id}
                else:
                    return "REPOST", {"tweet_id": post_id}
            elif behavior == FollowerBehavior.CONTRARIAN:
                phrase = random.choice(_CONTRARIAN_PHRASES)
                return "QUOTE_POST", {
                    "tweet_id": post_id,
                    "content": f"Disagree: {content[:50]} — {phrase}",
                }
            elif behavior == FollowerBehavior.NEUTRAL:
                if random.random() < 0.5:
                    return "LIKE_POST", {"tweet_id": post_id}
                else:
                    return "DO_NOTHING", {}
            else:  # LURKER
                return "DO_NOTHING", {}

        else:  # reddit
            if behavior == FollowerBehavior.AMPLIFIER:
                return "LIKE_POST", {"post_id": post_id}
            elif behavior == FollowerBehavior.CONTRARIAN:
                if random.random() < 0.5:
                    return "DISLIKE_POST", {"post_id": post_id}
                else:
                    phrase = random.choice(_CONTRARIAN_PHRASES)
                    return "CREATE_COMMENT", {"post_id": post_id, "content": phrase}
            elif behavior == FollowerBehavior.NEUTRAL:
                if random.random() < 0.5:
                    return "LIKE_POST", {"post_id": post_id}
                else:
                    return "DO_NOTHING", {}
            else:  # LURKER
                return "DO_NOTHING", {}
