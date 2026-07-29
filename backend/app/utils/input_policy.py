"""Shared bounds and policy checks for model-facing request data."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


PROJECT_NAME_MAX = 120
SCENARIO_QUESTION_MAX = 4_000
ADDITIONAL_CONTEXT_MAX = 8_000
CHAT_MESSAGE_MAX = 4_000
CHAT_HISTORY_ITEMS_MAX = 20
CHAT_HISTORY_TOTAL_MAX = 16_000
INTERVIEW_PROMPT_MAX = 2_000
INTERVIEW_BATCH_MAX = 25
GRAPH_QUERY_MAX = 1_000
UPLOAD_FILE_COUNT_MAX = 10
EXTRACTED_TEXT_CHARACTERS_MAX = 2_000_000
PDF_PAGE_MAX = 1_000
ENTITY_TYPE_FILTER_MAX = 50
ENTITY_TYPE_NAME_MAX = 120
PREPARE_ENTITY_MAX = 500
PARALLEL_PROFILE_WORKERS_MAX = 16
ARCHETYPE_COUNT_MAX = 50
ARCHETYPE_EXPANSION_MAX = 20
PREPARED_PROFILE_MAX = 500
SIMULATION_ROUNDS_MAX = 200
FOLLOWER_COUNT_MAX = 500

ALLOWED_INTENDED_USES = frozenset(
    {
        "scenario_planning",
        "assumption_mapping",
        "research_pretesting",
        "internal_red_teaming",
        "fiction_education",
    }
)


@dataclass(frozen=True)
class InputPolicyError(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def bounded_text(
    value: Any,
    *,
    field: str,
    max_length: int,
    required: bool = False,
) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise InputPolicyError(
            "invalid_text_field",
            f"{field} must be text.",
        )
    if required and not text:
        raise InputPolicyError(
            "missing_required_field",
            f"{field} is required.",
        )
    if len(text) > max_length:
        raise InputPolicyError(
            "text_field_too_long",
            f"{field} must be {max_length} characters or fewer.",
        )
    return text


def bounded_integer(
    value: Any,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool):
        raise InputPolicyError("invalid_integer_field", f"{field} must be an integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InputPolicyError(
            "invalid_integer_field",
            f"{field} must be an integer.",
        ) from exc
    if parsed < minimum or parsed > maximum:
        raise InputPolicyError(
            "integer_field_out_of_range",
            f"{field} must be between {minimum} and {maximum}.",
        )
    return parsed


def validate_chat_history(value: Any) -> list[dict[str, str]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise InputPolicyError(
            "invalid_chat_history",
            "chat_history must be a list.",
        )
    if len(value) > CHAT_HISTORY_ITEMS_MAX:
        raise InputPolicyError(
            "chat_history_too_long",
            f"chat_history may contain at most {CHAT_HISTORY_ITEMS_MAX} messages.",
        )

    cleaned: list[dict[str, str]] = []
    total = 0
    for item in value:
        if not isinstance(item, dict) or item.get("role") not in {
            "user",
            "assistant",
        }:
            raise InputPolicyError(
                "invalid_chat_history",
                "Each chat_history item must have a user or assistant role.",
            )
        content = bounded_text(
            item.get("content"),
            field="chat_history content",
            max_length=CHAT_MESSAGE_MAX,
            required=True,
        )
        total += len(content)
        cleaned.append({"role": item["role"], "content": content})
    if total > CHAT_HISTORY_TOTAL_MAX:
        raise InputPolicyError(
            "chat_history_too_long",
            f"chat_history must total {CHAT_HISTORY_TOTAL_MAX} characters or fewer.",
        )
    return cleaned


def _is_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def validate_exploratory_use(
    *,
    intended_use: Any,
    acknowledged: Any,
) -> str:
    if not _is_true(acknowledged):
        raise InputPolicyError(
            "use_policy_acknowledgement_required",
            (
                "Confirm exploratory use before starting: synthetic output is "
                "not human evidence and cannot be the sole basis for a "
                "consequential decision."
            ),
        )
    normalized = bounded_text(
        intended_use,
        field="intended_use",
        max_length=64,
        required=True,
    )
    if normalized not in ALLOWED_INTENDED_USES:
        raise InputPolicyError(
            "intended_use_not_allowed",
            "Select a supported exploratory use before starting.",
        )
    return normalized


def validate_item_count(
    values: Iterable[Any],
    *,
    field: str,
    maximum: int,
) -> list[Any]:
    if not isinstance(values, (list, tuple)):
        raise InputPolicyError(
            "invalid_item_list",
            f"{field} must be a list.",
        )
    items = list(values)
    if len(items) > maximum:
        raise InputPolicyError(
            "too_many_items",
            f"{field} may contain at most {maximum} items.",
        )
    return items


def validate_weight_distribution(
    value: Any,
    *,
    field: str,
    allowed_keys: Iterable[str],
) -> dict[str, float] | None:
    """Validate a finite, normalized categorical weight distribution."""
    if value is None:
        return None
    allowed = set(allowed_keys)
    if not isinstance(value, dict) or not value:
        raise InputPolicyError(
            "invalid_weight_distribution",
            f"{field} must be a non-empty object of category weights.",
        )
    if any(not isinstance(key, str) or key not in allowed for key in value):
        raise InputPolicyError(
            "invalid_weight_distribution",
            f"{field} contains an unsupported category.",
        )

    normalized: dict[str, float] = {}
    for key, raw_weight in value.items():
        if isinstance(raw_weight, bool):
            raise InputPolicyError(
                "invalid_weight_distribution",
                f"{field} weights must be finite numbers between 0 and 1.",
            )
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError) as exc:
            raise InputPolicyError(
                "invalid_weight_distribution",
                f"{field} weights must be finite numbers between 0 and 1.",
            ) from exc
        if not math.isfinite(weight) or weight < 0 or weight > 1:
            raise InputPolicyError(
                "invalid_weight_distribution",
                f"{field} weights must be finite numbers between 0 and 1.",
            )
        normalized[key] = weight

    if not math.isclose(sum(normalized.values()), 1.0, abs_tol=0.001):
        raise InputPolicyError(
            "invalid_weight_distribution",
            f"{field} weights must sum to 1.",
        )
    return normalized
