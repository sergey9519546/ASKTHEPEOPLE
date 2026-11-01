"""Local PRNG streams for simulation scheduling and generated observations.

The versioned SHA-256 encoding avoids Python's process-randomized hash(). Each
call creates a fresh stream at its addressed starting point; no global RNG is
reseeded. These streams govern local draws only, not provider responses.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Mapping, Optional


MAX_SEED = 2**63 - 1


def validate_seed(seed: Any) -> int:
    """Require a non-boolean integer root seed in the supported JSON range."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed must be an integer between 0 and {MAX_SEED}")
    return seed


def seed_from_config(config: Mapping[str, Any]) -> Optional[int]:
    """Return None only for an omitted seed; explicit null is invalid input."""
    return validate_seed(config["seed"]) if "seed" in config else None


def derive_seed(
    seed: int,
    namespace: str,
    *,
    round_num: Optional[int] = None,
    agent_id: Optional[int] = None,
) -> int:
    """Derive a stable integer for one purpose, round, and optional agent."""
    validate_seed(seed)
    if not isinstance(namespace, str) or not namespace:
        raise ValueError("RNG namespace must be a non-empty string")
    for name, value in (("round_num", round_num), ("agent_id", agent_id)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError(f"{name} must be an integer when provided")
    encoded = json.dumps(
        ["simulation-rng-v1", seed, namespace, round_num, agent_id],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest(), "big")


def make_rng(
    seed: int,
    namespace: str,
    *,
    round_num: Optional[int] = None,
    agent_id: Optional[int] = None,
) -> random.Random:
    """Create a local stream, also usable with existing BigFive RNG seams."""
    return random.Random(derive_seed(seed, namespace, round_num=round_num, agent_id=agent_id))
