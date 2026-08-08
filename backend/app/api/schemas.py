"""
Pydantic v2 request schemas and validation helper for typed API boundaries.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from flask import request, jsonify
from functools import wraps


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
    simulation_id: str = Field(..., min_length=1, description="Required simulation identifier")


class FetchUrlsRequest(BaseModel):
    urls: List[str] = Field(..., min_items=1, max_items=10, description="List of HTTP/HTTPS URLs to fetch")
    simulation_id: Optional[str] = Field(None, description="Optional simulation identifier")


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
