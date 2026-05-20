"""
Shared CAMEL model resolution and creation helpers.

The app persists a model-resolution artifact during simulation prepare and uses
the same resolution logic in the runtime scripts and report path.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict

from ..config import Config


MODEL_RESOLUTION_FILENAME = "model_resolution.json"
OPENAI_DEFAULT_URLS = {
    "https://api.openai.com",
    "https://api.openai.com/",
    "https://api.openai.com/v1",
    "https://api.openai.com/v1/",
}


@dataclass
class ResolvedModelConfig:
    role: str
    provider_mode: str
    model_platform: str
    model_name: str
    base_url: str
    api_key_present: bool
    timeout: float
    max_retries: int
    semaphore: int
    source_prefix: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_url(url: str | None) -> str:
    return (url or "").strip() or Config.LLM_BASE_URL


def _env_value(prefix: str, key: str, fallback: str = "") -> str:
    return os.environ.get(f"{prefix}_{key}", fallback)


def resolve_model_config(role: str, prefer_boost: bool = False) -> ResolvedModelConfig:
    upper_role = role.upper()

    if prefer_boost and os.environ.get("LLM_BOOST_API_KEY"):
        source_prefix = "LLM_BOOST"
        api_key = os.environ.get("LLM_BOOST_API_KEY", "")
        base_url = _clean_url(os.environ.get("LLM_BOOST_BASE_URL", Config.LLM_BASE_URL))
        model_name = os.environ.get("LLM_BOOST_MODEL_NAME", "") or os.environ.get("LLM_MODEL_NAME", "")
        timeout = float(os.environ.get("LLM_BOOST_TIMEOUT", os.environ.get("LLM_TIMEOUT", "120")))
        max_retries = int(os.environ.get("LLM_BOOST_MAX_RETRIES", os.environ.get("LLM_MAX_RETRIES", "3")))
        semaphore = int(os.environ.get("LLM_BOOST_SEMAPHORE", os.environ.get("LLM_SEMAPHORE", "30")))
    else:
        source_prefix = f"LLM_{upper_role}"
        api_key = _env_value(source_prefix, "API_KEY", Config.LLM_API_KEY or "")
        base_url = _clean_url(_env_value(source_prefix, "BASE_URL", Config.LLM_BASE_URL))
        model_name = _env_value(source_prefix, "MODEL_NAME", Config.LLM_MODEL_NAME)
        timeout = float(_env_value(source_prefix, "TIMEOUT", os.environ.get("LLM_TIMEOUT", "120")))
        max_retries = int(_env_value(source_prefix, "MAX_RETRIES", os.environ.get("LLM_MAX_RETRIES", "3")))
        semaphore = int(_env_value(source_prefix, "SEMAPHORE", os.environ.get("LLM_SEMAPHORE", "30")))

    normalized_url = base_url.rstrip("/")
    if normalized_url in {url.rstrip("/") for url in OPENAI_DEFAULT_URLS}:
        provider_mode = "openai"
        model_platform = "OPENAI"
    else:
        provider_mode = "openai_compatible"
        model_platform = "OPENAI_COMPATIBLE_MODEL"

    return ResolvedModelConfig(
        role=role,
        provider_mode=provider_mode,
        model_platform=model_platform,
        model_name=model_name,
        base_url=base_url,
        api_key_present=bool(api_key),
        timeout=timeout,
        max_retries=max_retries,
        semaphore=semaphore,
        source_prefix=source_prefix,
    )


def resolve_model_matrix(prefer_boost_for_actor: bool = False) -> Dict[str, Dict[str, Any]]:
    matrix = {}
    for role in ("actor", "interview", "curator", "report"):
        matrix[role] = resolve_model_config(role, prefer_boost=prefer_boost_for_actor and role == "actor").to_dict()
    return matrix


def write_model_resolution(simulation_dir: str, prefer_boost_for_actor: bool = False) -> Dict[str, Dict[str, Any]]:
    matrix = resolve_model_matrix(prefer_boost_for_actor=prefer_boost_for_actor)
    path = os.path.join(simulation_dir, MODEL_RESOLUTION_FILENAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    return matrix


def load_model_resolution(simulation_dir: str) -> Dict[str, Dict[str, Any]]:
    path = os.path.join(simulation_dir, MODEL_RESOLUTION_FILENAME)
    if not os.path.exists(path):
        return write_model_resolution(simulation_dir)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_required_model_env(role: str, prefer_boost: bool = False) -> list[str]:
    settings = resolve_model_config(role, prefer_boost=prefer_boost)
    errors = []
    if not settings.api_key_present:
        errors.append(f"{role}: missing API key")
    if not settings.model_name:
        errors.append(f"{role}: missing model name")
    return errors


def validate_camel_runtime_imports() -> list[str]:
    errors = []
    try:
        from camel.models import ModelFactory  # noqa: F401
        from camel.types import ModelPlatformType  # noqa: F401
    except Exception as exc:  # pragma: no cover
        errors.append(f"camel import failed: {exc}")
    try:
        import oasis  # noqa: F401
    except Exception as exc:  # pragma: no cover
        errors.append(f"oasis import failed: {exc}")
    return errors


def create_camel_model(role: str, prefer_boost: bool = False):
    settings = resolve_model_config(role, prefer_boost=prefer_boost)
    api_key = ""

    if settings.source_prefix == "LLM_BOOST":
        api_key = os.environ.get("LLM_BOOST_API_KEY", "")
    else:
        api_key = os.environ.get(f"{settings.source_prefix}_API_KEY", Config.LLM_API_KEY or "")

    if not settings.api_key_present:
        raise ValueError(f"{role}: missing API key for model creation")

    from camel.models import ModelFactory
    from camel.types import ModelPlatformType

    platform_type = getattr(ModelPlatformType, settings.model_platform)
    kwargs: Dict[str, Any] = {
        "model_platform": platform_type,
        "model_type": settings.model_name,
        "timeout": settings.timeout,
        "max_retries": settings.max_retries,
    }

    if settings.provider_mode == "openai_compatible":
        kwargs["url"] = settings.base_url
        kwargs["api_key"] = api_key
    else:
        kwargs["api_key"] = api_key

    return ModelFactory.create(**kwargs)
