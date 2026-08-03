"""
Archetype Engine — Agent Archetype Compression for OASIS simulations.

Clusters N entity profiles into K archetypes via LLM, then expands each
archetype to M variant profiles using stochastic variation. This scales
simulations from ~30 agents to 300+ at the cost of only K LLM profile calls.
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .oasis_profile_generator import OasisAgentProfile

logger = logging.getLogger("askthepeople.archetype_engine")

_USERNAME_SAFE = re.compile(r"[^a-z0-9_]")


def _sanitize_label(label: str, max_len: int = 30) -> str:
    """Convert a human-readable label to a safe identifier string."""
    sanitized = _USERNAME_SAFE.sub("", label.lower().replace(" ", "_").replace("-", "_"))
    return sanitized[:max_len] if sanitized else "archetype"


class PopulationTierId(str, Enum):
    TIER_1 = "MICRO_PRECISION"
    TIER_2 = "BALANCED_NETWORK"
    TIER_3 = "MACRO_CROWD"


@dataclass
class PopulationTierSpec:
    tier_id: PopulationTierId
    name: str
    description: str
    target_llm_agents: int  # Core LLM / Archetype Variant agents
    n_archetypes: int       # Number of K archetypes clustered by LLM
    expansion_factor: int   # Number of variant profiles per archetype
    follower_count: int     # Rule-based follower count
    variance_level: float   # Stochastic variance multiplier

    @property
    def total_population(self) -> int:
        return self.target_llm_agents + self.follower_count


TIER_SPECS: Dict[PopulationTierId, PopulationTierSpec] = {
    PopulationTierId.TIER_1: PopulationTierSpec(
        tier_id=PopulationTierId.TIER_1,
        name="Micro Precision",
        description="High-fidelity 1:1 LLM agent modeling for targeted focus groups.",
        target_llm_agents=20,
        n_archetypes=20,
        expansion_factor=1,
        follower_count=0,
        variance_level=0.10,
    ),
    PopulationTierId.TIER_2: PopulationTierSpec(
        tier_id=PopulationTierId.TIER_2,
        name="Balanced Network",
        description="Balanced agent graph with LLM core agents and lightweight follower agents.",
        target_llm_agents=80,
        n_archetypes=16,
        expansion_factor=5,
        follower_count=500,
        variance_level=0.20,
    ),
    PopulationTierId.TIER_3: PopulationTierSpec(
        tier_id=PopulationTierId.TIER_3,
        name="Macro Crowd",
        description="Mass crowd scale using 300 archetype variants and 5,000 follower agents.",
        target_llm_agents=300,
        n_archetypes=20,
        expansion_factor=15,
        follower_count=5000,
        variance_level=0.35,
    ),
}


@dataclass
class AgentArchetype:
    archetype_id: int
    label: str
    member_indices: List[int]
    centroid_index: int
    source_entity_uuids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype_id": self.archetype_id,
            "label": self.label,
            "member_indices": self.member_indices,
            "centroid_index": self.centroid_index,
            "source_entity_uuids": self.source_entity_uuids,
        }


class ArchetypeEngine:
    """Clusters profiles into archetypes and expands each to M variants."""

    MAX_PROFILES_FOR_CLUSTERING = 500

    @staticmethod
    def get_tier_spec(tier: str | PopulationTierId) -> PopulationTierSpec:
        """Resolve tier spec by string or PopulationTierId enum."""
        if isinstance(tier, PopulationTierId):
            return TIER_SPECS[tier]
        
        tier_str = str(tier).upper().replace(" ", "_")
        for tid, spec in TIER_SPECS.items():
            if tid.value == tier_str or spec.name.upper().replace(" ", "_") == tier_str:
                return spec
            
        if tier_str in ("1", "TIER_1", "TIER1", "MICRO"):
            return TIER_SPECS[PopulationTierId.TIER_1]
        elif tier_str in ("2", "TIER_2", "TIER2", "BALANCED"):
            return TIER_SPECS[PopulationTierId.TIER_2]
        elif tier_str in ("3", "TIER_3", "TIER3", "MACRO"):
            return TIER_SPECS[PopulationTierId.TIER_3]

        return TIER_SPECS[PopulationTierId.TIER_2]

    def cluster_agents(
        self,
        profiles: List[OasisAgentProfile],
        n_archetypes: int,
        llm_client: Any,  # LLMClient — avoid circular import
    ) -> List[AgentArchetype]:
        """
        Cluster profiles into n_archetypes groups via a single LLM call.

        Post-processes the response to handle missing / duplicate assignments:
        - Unassigned profile indices → assigned to archetype_id % n_archetypes
        - Duplicate assignments → first assignment wins
        """
        if not profiles:
            return []

        if len(profiles) > self.MAX_PROFILES_FOR_CLUSTERING:
            logger.warning(
                f"Profile count {len(profiles)} exceeds clustering limit "
                f"{self.MAX_PROFILES_FOR_CLUSTERING}; truncating for LLM clustering."
            )
            clustering_profiles = profiles[: self.MAX_PROFILES_FOR_CLUSTERING]
        else:
            clustering_profiles = profiles

        n = len(clustering_profiles)
        summaries = [
            {"index": i, "summary": f"{p.name}: {(p.bio or '')[:120]}"}
            for i, p in enumerate(clustering_profiles)
        ]

        try:
            # Use registry-based prompt if available
            if hasattr(llm_client, 'registry') and llm_client.registry:
                contract_result = llm_client.chat_with_registry_prompt(
                    prompt_id="archetype_clustering",
                    prompt_version=None,  # Use latest
                    n_profiles=n,
                    n_archetypes=n_archetypes,
                    profiles_json=json.dumps(summaries, ensure_ascii=False),
                    temperature=0.2,
                    complexity="routine",
                )
                response = contract_result["data"]
                raw_archetypes = response.get("archetypes", [])
            else:
                # Fallback to direct call
                prompt = (
                    f"You are grouping {n} social media agent profiles into exactly "
                    f"{n_archetypes} archetypes for a simulation.\n\n"
                    "Profiles:\n"
                    f"{json.dumps(summaries, ensure_ascii=False)}\n\n"
                    f"Return a JSON object with a single key 'archetypes' containing an array of "
                    f"exactly {n_archetypes} objects. Each object must have:\n"
                    '  "archetype_id": integer (0-based index)\n'
                    '  "label": short snake_case identifier (e.g. "skeptical_student")\n'
                    '  "member_indices": array of profile indices belonging to this archetype\n\n'
                    "Every profile index must appear in exactly one archetype. "
                    "Do not omit any indices. Return only the JSON object."
                )
                response = llm_client.chat_json(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                raw_archetypes = response.get("archetypes", [])
        except Exception as e:
            logger.error(f"LLM clustering call failed: {e}. Falling back to round-robin.")
            raw_archetypes = []

        # Build assignment map: profile_index → archetype_id (first assignment wins)
        assigned: Dict[int, int] = {}
        labels: Dict[int, str] = {}
        archetype_members: Dict[int, List[int]] = {i: [] for i in range(n_archetypes)}

        for item in raw_archetypes:
            arch_id = item.get("archetype_id")
            label = item.get("label", f"archetype_{arch_id}")
            if not isinstance(arch_id, int) or arch_id < 0 or arch_id >= n_archetypes:
                continue
            labels[arch_id] = _sanitize_label(label)
            for idx in item.get("member_indices", []):
                if isinstance(idx, int) and 0 <= idx < n and idx not in assigned:
                    assigned[idx] = arch_id
                    archetype_members[arch_id].append(idx)

        # Assign any unassigned profile indices via round-robin
        for idx in range(n):
            if idx not in assigned:
                arch_id = idx % n_archetypes
                assigned[idx] = arch_id
                archetype_members[arch_id].append(idx)

        # Build AgentArchetype objects
        archetypes: List[AgentArchetype] = []
        for arch_id in range(n_archetypes):
            members = archetype_members[arch_id]
            if not members:
                # Edge case: empty cluster — assign idx=arch_id as sole member
                fallback = arch_id % n
                members = [fallback]
                assigned[fallback] = arch_id

            centroid = members[len(members) // 2]
            label = labels.get(arch_id, f"archetype_{arch_id}")
            uuids = [
                p.source_entity_uuid
                for i, p in enumerate(clustering_profiles)
                if i in members and p.source_entity_uuid
            ]
            archetypes.append(
                AgentArchetype(
                    archetype_id=arch_id,
                    label=label,
                    member_indices=members,
                    centroid_index=centroid,
                    source_entity_uuids=uuids,
                )
            )

        return archetypes

    def expand_archetype(
        self,
        archetype: AgentArchetype,
        base_profile: OasisAgentProfile,
        count: int,
        base_agent_id: int,
    ) -> List[OasisAgentProfile]:
        """
        Generate `count` variant profiles derived from base_profile.

        Each variant is a shallow copy with stochastic numeric variation.
        Textual fields (persona, bio, mbti, etc.) are copied verbatim.
        """
        variants: List[OasisAgentProfile] = []
        for n in range(count):
            random.seed(archetype.archetype_id * 1000 + n)

            user_id = base_agent_id + n
            label = archetype.label
            username = f"{label}_{n:02d}"
            display_name = f"{label.replace('_', ' ').title()} {n + 1}"

            age: Optional[int]
            if base_profile.age:
                age = max(18, min(80, base_profile.age + random.randint(-5, 5)))
            else:
                age = 30

            # Only jitter if base value exists and is source-derived
            # Don't fabricate counts from None
            karma = (
                int(base_profile.karma * random.uniform(0.7, 1.3))
                if base_profile.karma is not None
                else None
            )
            follower_count = (
                int(base_profile.follower_count * random.uniform(0.7, 1.3))
                if base_profile.follower_count is not None
                else None
            )
            friend_count = (
                int(base_profile.friend_count * random.uniform(0.7, 1.3))
                if base_profile.friend_count is not None
                else None
            )
            statuses_count = (
                int(base_profile.statuses_count * random.uniform(0.7, 1.3))
                if base_profile.statuses_count is not None
                else None
            )

            variants.append(
                OasisAgentProfile(
                    user_id=user_id,
                    user_name=username,
                    name=display_name,
                    bio=base_profile.bio,
                    persona=base_profile.persona,
                    karma=karma,
                    friend_count=friend_count,
                    follower_count=follower_count,
                    statuses_count=statuses_count,
                    age=age,
                    gender=base_profile.gender,
                    mbti=base_profile.mbti,
                    country=base_profile.country,
                    profession=base_profile.profession,
                    interested_topics=list(base_profile.interested_topics or []),
                    source_entity_uuid=None,
                    source_entity_type="archetype_variant",
                )
            )
        return variants
