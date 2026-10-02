"""
Pydantic v2 request schemas and validation helper for typed API boundaries.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from flask import request, jsonify
from functools import wraps

from ..utils.logger import get_logger

logger = get_logger("askthepeople.api.schemas")


class ProblemDetailsResponse(BaseModel):
    """RFC 7807 Problem Details schema."""
    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None


class CreateSimulationRequest(BaseModel):
    project_id: str = Field(..., min_length=1, description="Required project identifier")
    graph_id: Optional[str] = Field(None, description="Optional graph identifier")
    enable_twitter: bool = Field(default=True, description="Enable Twitter platform simulation")
    enable_reddit: bool = Field(default=True, description="Enable Reddit platform simulation")


class PrepareSimulationRequest(BaseModel):
    simulation_id: str = Field(..., min_length=1, description="Required simulation identifier")
    force_regenerate: Optional[bool] = Field(default=False, description="Force regeneration of profiles")
    archetype_count: Optional[int] = Field(None)
    profile_workers: Optional[int] = Field(None)
    parallel_profile_count: Optional[int] = Field(None)
    expansion_factor: Optional[int] = Field(None)
    entity_types: Optional[List[str]] = Field(None)
    use_archetypes: Optional[bool] = Field(None)
    prompt: Optional[str] = Field(None, max_length=8000)
    seed: Optional[int] = Field(None)


class StartSimulationRequest(BaseModel):
    simulation_id: str = Field(..., min_length=1, description="Required simulation identifier")
    platform: Optional[str] = Field(default="parallel")
    force: Optional[bool] = Field(default=False)
    max_rounds: Optional[int] = Field(None)
    enable_followers: Optional[bool] = Field(default=False)
    follower_count: Optional[int] = Field(None)
    follower_distribution: Optional[Dict[str, float]] = Field(None)
    target_agent_id: Optional[str] = Field(None)
    bias_factor: Optional[float] = Field(None)


class StopSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_id: str = Field(..., min_length=1, description="Required simulation identifier")


class SimulationControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_type: Literal[
        "inject_post",
        "inject_event",
        "pause_after_round",
        "resume",
        "stop",
    ]
    args: Dict[str, Any] = Field(default_factory=dict)
    platforms: Optional[List[Literal["twitter", "reddit"]]] = None

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, value):
        if value is None:
            return value
        if not value:
            raise ValueError("platforms must not be empty")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_command_args(self):
        allowed_keys = {
            "inject_post": {"content", "agent_id", "agent_ids", "roles", "reason"},
            "inject_event": {"event_type", "payload", "targeting", "reason"},
            "pause_after_round": set(),
            "resume": set(),
            "stop": set(),
        }
        unknown = set(self.args) - allowed_keys[self.command_type]
        if unknown:
            raise ValueError(
                f"unsupported args for {self.command_type}: {sorted(unknown)}"
            )

        if self.command_type == "inject_post":
            content = self.args.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("inject_post requires non-empty content")
            if len(content) > 8000:
                raise ValueError("inject_post content exceeds 8000 characters")
            self._validate_target_fields(
                self.args,
                id_keys={"agent_id"},
                list_id_keys={"agent_ids"},
                role_keys={"roles"},
                prefix="inject_post",
            )

        if self.command_type == "inject_event":
            allowed_events = {
                "seed_post",
                "official_statement",
                "media_breaking_news",
                "topic_spike",
                "follow_wave",
            }
            event_type = self.args.get("event_type")
            if event_type not in allowed_events:
                raise ValueError("inject_event event_type is unsupported")
            payload = self.args.get("payload")
            targeting = self.args.get("targeting", {})
            if not isinstance(payload, dict):
                raise ValueError("inject_event payload must be an object")
            if not isinstance(targeting, dict):
                raise ValueError("inject_event targeting must be an object")
            payload_keys = {
                "seed_post": {"content", "summary"},
                "official_statement": {"content", "statement", "summary"},
                "media_breaking_news": {"content", "headline", "summary"},
                "topic_spike": {"content", "topics"},
                "follow_wave": set(),
            }
            unsupported_payload = set(payload) - payload_keys[event_type]
            if unsupported_payload:
                raise ValueError(
                    "unsupported payload for "
                    f"{event_type}: {sorted(unsupported_payload)}"
                )
            if event_type == "follow_wave":
                if payload:
                    raise ValueError("follow_wave payload must be empty")
            else:
                if len(payload) != 1:
                    raise ValueError(
                        f"{event_type} requires exactly one runtime effect field"
                    )
                payload_key, payload_value = next(iter(payload.items()))
                if payload_key == "topics":
                    if (
                        not isinstance(payload_value, list)
                        or not 1 <= len(payload_value) <= 3
                        or any(
                            not isinstance(topic, str)
                            or not topic.strip()
                            or len(topic) > 200
                            for topic in payload_value
                        )
                    ):
                        raise ValueError(
                            "topic_spike topics must contain 1-3 non-empty items of at most 200 characters"
                        )
                elif (
                    not isinstance(payload_value, str)
                    or not payload_value.strip()
                    or len(payload_value) > 8000
                ):
                    raise ValueError(
                        f"{event_type} {payload_key} must be 1-8000 characters"
                    )
            targeting_keys = {
                "seed_post": {"poster_agent_id", "agent_ids", "roles"},
                "official_statement": {"poster_agent_id", "agent_ids", "roles"},
                "media_breaking_news": {"poster_agent_id", "agent_ids", "roles"},
                "topic_spike": {"poster_agent_id", "agent_ids", "roles"},
                "follow_wave": {"source_roles", "roles", "target_roles"},
            }
            unsupported_targeting = set(targeting) - targeting_keys[event_type]
            if unsupported_targeting:
                raise ValueError(
                    "unsupported targeting for "
                    f"{event_type}: {sorted(unsupported_targeting)}"
                )
            self._validate_target_fields(
                targeting,
                id_keys={"agent_id", "poster_agent_id"},
                list_id_keys={"agent_ids"},
                role_keys={"roles", "source_roles", "target_roles"},
                prefix="inject_event targeting",
            )
        return self

    @staticmethod
    def _validate_target_fields(
        values: Dict[str, Any],
        *,
        id_keys: set[str],
        list_id_keys: set[str],
        role_keys: set[str],
        prefix: str,
    ) -> None:
        for key in id_keys & set(values):
            value = values[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{prefix}.{key} must be an agent ID")
        for key in list_id_keys & set(values):
            agent_ids = values[key]
            if (
                not isinstance(agent_ids, list)
                or not agent_ids
                or any(
                    isinstance(agent_id, bool)
                    or not isinstance(agent_id, int)
                    or agent_id < 0
                    for agent_id in agent_ids
                )
            ):
                raise ValueError(
                    f"{prefix}.{key} must be a non-empty list of agent IDs"
                )
        for key in role_keys & set(values):
            roles = values[key]
            if isinstance(roles, str):
                roles = [roles]
            if (
                not isinstance(roles, list)
                or not roles
                or any(not isinstance(role, str) or not role.strip() for role in roles)
            ):
                raise ValueError(
                    f"{prefix}.{key} must contain non-empty role names"
                )


class FetchUrlsRequest(BaseModel):
    urls: List[str] = Field(..., min_items=1, max_items=10, description="List of HTTP/HTTPS URLs to fetch")
    simulation_id: Optional[str] = Field(None, description="Optional simulation identifier")


# ---------------------------------------------------------------------------
# Report request bodies (exec-plan T26).
#
# These exist to type the four report routes that take a JSON body, which
# `api/report_routes/` had left untyped after the T25 decomposition.
#
# Scope is deliberately narrow: SHAPE only. `extra="forbid"` rejects unknown
# keys, and `strict=True` rejects wrong JSON types instead of coercing them.
# Semantic bounds -- required fields, maximum lengths, ranges -- stay with
# `utils.input_policy` (`bounded_text`, `bounded_integer`,
# `validate_chat_history`), because those already produce the specific error
# codes the frontend handles. Duplicating them here would change the error
# contract, which is a breaking change and not a refactor.
#
# `strict=True` matters at a trust boundary: without it Pydantic coerces
# `"force_regenerate": "yes"` to True and `"simulation_id": 5` to `"5"`. The
# first invents consent, the second invents an identifier.
# ---------------------------------------------------------------------------


class GenerateReportRequest(BaseModel):
    # extra="ignore", NOT "forbid", and the reason is a security property.
    #
    # `tests/test_report_worker_dispatch.py` posts a body carrying five
    # client-supplied fields the handler must ignore -- `user_prompt`,
    # `custom_instructions`, `graph_id`, `decision_text`,
    # `simulation_requirement` -- as privacy canaries, then asserts the
    # enqueued Celery kwargs contain only server-side ids. That is the proof
    # for AGENTS.md rule 5: no client-supplied data reaches a canonical
    # server-side record.
    #
    # With extra="forbid" the request would be rejected 400 before the handler
    # ran, and the test would pass for the wrong reason while proving nothing
    # about provenance. Refusing unknown keys here would make the one test
    # that guards payload provenance unable to guard it.
    #
    # `strict=True` still does the part that matters: it blocks coercion, so
    # `"force_regenerate": "yes"` cannot become True and `simulation_id: 5`
    # cannot become "5".
    model_config = ConfigDict(extra="ignore", strict=True)

    # Optional rather than required: the handler owns the "missing
    # simulation_id" response, which is `report_simulation_id_missing` and not
    # the generic `report_request_invalid`. Making it required here would
    # collapse two distinct error codes into one and break clients that branch
    # on them.
    simulation_id: Optional[str] = None
    force_regenerate: Optional[bool] = None


class ReportChatRequest(BaseModel):
    """Shape only. `message` requirement and length stay in input_policy."""

    model_config = ConfigDict(extra="forbid", strict=True)

    simulation_id: Optional[str] = None
    message: Optional[str] = None
    chat_history: Optional[List[Any]] = None


class GraphSearchRequest(BaseModel):
    """Shape only. `query` requirement and the 1-50 range stay in input_policy."""

    model_config = ConfigDict(extra="forbid", strict=True)

    project_id: Optional[str] = None
    graph_id: Optional[str] = None
    query: Optional[str] = None
    limit: Optional[int] = None


class GraphStatisticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    project_id: Optional[str] = None
    graph_id: Optional[str] = None


def validate_schema(schema_cls):
    """
    Decorator to validate JSON request body using a Pydantic v2 model.
    Attaches validated payload to `request.validated_data`.
    Returns HTTP 422 Problem Details on validation error.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raw_data = request.get_json(silent=True) or {}
            try:
                validated = schema_cls.model_validate(raw_data)
                request.validated_data = validated
            except Exception as exc:
                problem = ProblemDetailsResponse(
                    type="validation_error",
                    title="Request Validation Error",
                    status=422,
                    detail=str(exc),
                    instance=request.path,
                )
                return jsonify(problem.model_dump()), 422
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def enforce_schema(schema_cls, error_code: str):
    """Enforce a request schema while preserving the endpoint's own error shape.

    `validate_schema` answers validation failures with RFC-7807 Problem Details
    and a 422. The report endpoints have always answered 400 with the
    `{"success": false, "error": ...}` envelope, and clients match on those
    codes. This decorator therefore keeps that envelope and that status, so
    adding the typed boundary is additive rather than a breaking API change.

    Apply this INSIDE `@limiter.limit`, so malformed requests are still counted
    against the rate limit exactly as they are today.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raw_data = request.get_json(silent=True) or {}
            try:
                request.validated_data = schema_cls.model_validate(raw_data)
            except ValidationError as exc:
                logger.warning(
                    "typed request rejected: code=%s schema=%s fields=%s",
                    error_code,
                    schema_cls.__name__,
                    # A non-object body (a list, a bare string) yields an error
                    # with an empty `loc`, so indexing [-1] here would raise
                    # IndexError and turn a 400 into a 500.
                    sorted(str(e["loc"][-1]) for e in exc.errors() if e.get("loc")),
                    extra={"privacy_safe": True},
                )
                return jsonify({"success": False, "error": error_code}), 400
            return fn(*args, **kwargs)
        return wrapper
    return decorator
