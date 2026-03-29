"""
Validation Engine — Post-simulation networkx analysis.

Computes polarization, Gini, echo-chamber score, cascade stats, and per-round
summaries. Results are cached to metrics.json and exposed via GET /<id>/metrics.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import logging

logger = logging.getLogger("askthepeople.validation_engine")


@dataclass
class SimulationMetrics:
    polarization_index: float          # modularity Q in [0,1]
    engagement_gini: float             # Gini in [0,1]
    echo_chamber_score: float          # intra-community edges / total in [0,1]
    cascade_stats: List[Dict[str, Any]]   # top 20 posts by reactions
    action_type_distribution: Dict[str, int]
    top_agents: List[Dict[str, Any]]      # top 10 by action count
    round_summaries: List[Dict[str, Any]] # per-round: {round_num, action_count, active_agents}
    total_actions: int
    total_agents: int
    community_count: int
    computed_at: str                   # ISO timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "polarization_index": self.polarization_index,
            "engagement_gini": self.engagement_gini,
            "echo_chamber_score": self.echo_chamber_score,
            "cascade_stats": self.cascade_stats,
            "action_type_distribution": self.action_type_distribution,
            "top_agents": self.top_agents,
            "round_summaries": self.round_summaries,
            "total_actions": self.total_actions,
            "total_agents": self.total_agents,
            "community_count": self.community_count,
            "computed_at": self.computed_at,
        }


class ValidationEngine:
    METRICS_FILENAME = "metrics.json"

    def compute_metrics(
        self,
        simulation_id: str,
        force: bool = False,
    ) -> SimulationMetrics:
        """
        Compute (or load from cache) simulation metrics.

        Args:
            simulation_id: Simulation ID
            force: If True, recompute even if metrics.json already exists

        Returns:
            SimulationMetrics
        """
        from .simulation_runner import SimulationRunner

        sim_dir = os.path.join(SimulationRunner.RUN_STATE_DIR, simulation_id)
        metrics_path = os.path.join(sim_dir, self.METRICS_FILENAME)

        # Cache hit
        if not force and os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SimulationMetrics(**data)

        actions = SimulationRunner.get_all_actions(simulation_id, include_followers=True)
        if not actions:
            raise ValueError("No actions found for this simulation")

        # Build interaction graph
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for validation metrics. Add networkx>=3.0 to dependencies.")

        G, post_registry = self._build_interaction_graph(actions, nx)

        # Compute metrics
        polarization, communities = self._compute_polarization(G, nx)
        gini = self._compute_engagement_gini(actions)
        echo = self._compute_echo_chamber_score(G, communities)
        cascade = self._compute_cascade_stats(actions, post_registry)
        action_dist = dict(Counter(a.action_type for a in actions))
        agent_counts = Counter(a.agent_id for a in actions)
        top_agents = [
            {
                "agent_id": aid,
                "name": next((a.agent_name for a in actions if a.agent_id == aid), ""),
                "count": cnt,
                "is_follower": getattr(
                    next((a for a in actions if a.agent_id == aid), None),
                    "action_args", {}
                ).get("is_follower", False),
            }
            for aid, cnt in agent_counts.most_common(10)
        ]
        round_summaries = self._compute_round_summaries(actions)

        metrics = SimulationMetrics(
            polarization_index=polarization,
            engagement_gini=gini,
            echo_chamber_score=echo,
            cascade_stats=cascade,
            action_type_distribution=action_dist,
            top_agents=top_agents,
            round_summaries=round_summaries,
            total_actions=len(actions),
            total_agents=len(agent_counts),
            community_count=len(communities),
            computed_at=datetime.now().isoformat(),
        )

        # Save to cache
        os.makedirs(sim_dir, exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, ensure_ascii=False, indent=2)

        return metrics

    def _build_interaction_graph(self, actions: List[Any], nx: Any) -> Tuple[Any, Dict]:
        """Build directed interaction graph from actions.

        Returns (G, post_to_creator) where post_to_creator maps post_key → creator_agent_id.
        """
        G = nx.DiGraph()

        # First pass: register post creators
        post_to_creator: Dict[str, int] = {}
        for a in actions:
            if a.action_type == "CREATE_POST":
                args = a.action_args or {}
                post_key = args.get("tweet_id") or args.get("post_id") or ""
                if post_key:
                    post_to_creator[post_key] = a.agent_id

        # Second pass: build edges from reactions
        reaction_types = {"LIKE_POST", "REPOST", "QUOTE_POST", "CREATE_COMMENT", "LIKE_COMMENT"}
        for a in actions:
            if a.action_type in reaction_types:
                args = a.action_args or {}
                post_key = args.get("tweet_id") or args.get("post_id") or ""
                creator = post_to_creator.get(post_key)
                if creator is not None and creator != a.agent_id:
                    if G.has_edge(a.agent_id, creator):
                        G[a.agent_id][creator]["weight"] += 1
                    else:
                        G.add_edge(a.agent_id, creator, weight=1)
            elif a.action_type == "FOLLOW":
                args = a.action_args or {}
                followed = args.get("follow_id")
                if followed is not None and followed != a.agent_id:
                    if not G.has_edge(a.agent_id, followed):
                        G.add_edge(a.agent_id, followed, weight=1)

        return G, post_to_creator

    def _compute_polarization(self, G: Any, nx: Any) -> Tuple[float, List]:
        """Compute modularity-based polarization index."""
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            G_ud = G.to_undirected()
            if G_ud.number_of_edges() == 0:
                return 0.0, []

            communities = list(greedy_modularity_communities(G_ud, weight="weight"))
            Q = nx.community.modularity(G_ud, communities, weight="weight")
            return max(0.0, float(Q)), communities
        except Exception as e:
            logger.warning(f"Polarization computation failed: {e}")
            return 0.0, []

    def _compute_engagement_gini(self, actions: List[Any]) -> float:
        """Compute Gini coefficient of agent action counts (no numpy)."""
        counts = sorted(Counter(a.agent_id for a in actions).values())
        n = len(counts)
        total = sum(counts)
        if n == 0 or total == 0:
            return 0.0
        return sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(counts)) / (n * total)

    def _compute_echo_chamber_score(self, G: Any, communities: List) -> float:
        """Compute fraction of edges that are intra-community."""
        if not communities or G.number_of_edges() == 0:
            return 0.0

        agent_to_community: Dict[int, int] = {}
        for comm_id, comm in enumerate(communities):
            for node in comm:
                agent_to_community[node] = comm_id

        intra = sum(
            1
            for u, v in G.edges()
            if agent_to_community.get(u) is not None
            and agent_to_community.get(u) == agent_to_community.get(v)
        )
        return intra / G.number_of_edges()

    def _compute_cascade_stats(self, actions: List[Any], post_to_creator: Dict) -> List[Dict]:
        """Compute top 20 posts by total reactions."""
        post_stats: Dict[str, Dict] = {}
        for a in actions:
            if a.action_type == "CREATE_POST":
                args = a.action_args or {}
                key = args.get("tweet_id") or args.get("post_id") or ""
                if key and key not in post_stats:
                    post_stats[key] = {
                        "post_id": key,
                        "creator_id": a.agent_id,
                        "platform": a.platform,
                        "round_num": a.round_num,
                        "likes": 0,
                        "reposts": 0,
                        "comments": 0,
                    }

        for a in actions:
            args = a.action_args or {}
            key = args.get("tweet_id") or args.get("post_id") or ""
            if not key or key not in post_stats:
                continue
            if a.action_type in ("LIKE_POST", "LIKE_COMMENT"):
                post_stats[key]["likes"] += 1
            elif a.action_type == "REPOST":
                post_stats[key]["reposts"] += 1
            elif a.action_type in ("CREATE_COMMENT", "QUOTE_POST"):
                post_stats[key]["comments"] += 1

        for s in post_stats.values():
            s["total"] = s["likes"] + s["reposts"] + s["comments"]

        return sorted(post_stats.values(), key=lambda x: x["total"], reverse=True)[:20]

    def _compute_round_summaries(self, actions: List[Any]) -> List[Dict]:
        """Compute per-round action counts and active agent counts."""
        rounds: Dict[int, Dict] = {}
        for a in actions:
            r = a.round_num
            if r not in rounds:
                rounds[r] = {"round_num": r, "action_count": 0, "active_agents": set()}
            rounds[r]["action_count"] += 1
            rounds[r]["active_agents"].add(a.agent_id)

        result = []
        for r in sorted(rounds.keys()):
            d = rounds[r]
            result.append({
                "round_num": d["round_num"],
                "action_count": d["action_count"],
                "active_agents": len(d["active_agents"]),
            })
        return result

    @staticmethod
    def load_metrics(simulation_id: str) -> Optional[Dict[str, Any]]:
        """Load cached metrics from disk, or None if not yet computed."""
        from .simulation_runner import SimulationRunner  # lazy import — avoids circular
        path = os.path.join(
            SimulationRunner.RUN_STATE_DIR,
            simulation_id,
            ValidationEngine.METRICS_FILENAME,
        )
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
