"""Shared computational bounds for simulation execution."""

import math

from ..utils.input_policy import SIMULATION_ROUNDS_MAX


def resolve_total_rounds(config: dict, max_rounds: int | None = None) -> int:
    """Resolve a positive run length using ceil semantics and the global cap.

    Full simulation configs are canonical. A bare ``time_config`` mapping
    remains accepted for compatibility with the prior helper contract.
    """
    if not isinstance(config, dict):
        raise ValueError("simulation config must be an object")

    time_config = config.get("time_config", config)
    if not isinstance(time_config, dict):
        raise ValueError("time_config must be an object")

    try:
        total_hours = float(time_config.get("total_simulation_hours", 72))
        minutes_per_round = float(time_config.get("minutes_per_round", 30))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "total_simulation_hours and minutes_per_round must be numbers"
        ) from exc

    if not math.isfinite(total_hours) or total_hours <= 0:
        raise ValueError("total_simulation_hours must be a positive finite number")
    if not math.isfinite(minutes_per_round) or minutes_per_round <= 0:
        raise ValueError("minutes_per_round must be a positive finite number")

    effective_limit = SIMULATION_ROUNDS_MAX
    if max_rounds is not None:
        if isinstance(max_rounds, bool):
            raise ValueError("requested max rounds must be an integer")
        try:
            requested_limit = int(max_rounds)
        except (TypeError, ValueError) as exc:
            raise ValueError("requested max rounds must be an integer") from exc
        if requested_limit <= 0:
            raise ValueError("requested max rounds must be positive")
        effective_limit = min(effective_limit, requested_limit)

    configured_rounds = math.ceil((total_hours * 60.0) / minutes_per_round)
    return max(1, min(configured_rounds, effective_limit))
