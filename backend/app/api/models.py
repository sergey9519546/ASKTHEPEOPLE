"""
Model catalog endpoint.

Returns the list of models available from the configured LLM provider.
For OpenAI-compatible providers, this queries the /v1/models endpoint.
For Anthropic-compatible providers, this returns a static list of known Claude models.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from ..config import Config
from ..services.camel_model_factory import _detect_provider_mode

models_bp = Blueprint('models', __name__)


_COMMON_CLAUDE_MODELS = [
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic"},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "provider": "anthropic"},
    {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic"},
    {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "anthropic"},
    {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "anthropic"},
    {"id": "claude-2.1", "name": "Claude 2.1", "provider": "anthropic"},
    {"id": "claude-2.0", "name": "Claude 2.0", "provider": "anthropic"},
]


def _get_configured_base_url() -> str:
    """Return the best configured base URL for model listing."""
    raw = Config.LLM_BASE_URL or os.environ.get('LLM_BOOST_BASE_URL', 'https://api.openai.com/v1')
    normalized = raw.rstrip("/")
    for suffix in ("/chat/completions", "/messages"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return normalized or 'https://api.openai.com/v1'


def _get_configured_api_key() -> str:
    """Return the best configured API key for model listing."""
    return Config.LLM_API_KEY or os.environ.get('LLM_BOOST_API_KEY', '')


@models_bp.route('/models', methods=['GET'])
def list_models():
    """Return available models from the configured provider."""
    base_url = _get_configured_base_url()
    api_key = _get_configured_api_key()
    model_name = Config.LLM_MODEL_NAME or os.environ.get('LLM_BOOST_MODEL_NAME', '')

    provider_mode, _ = _detect_provider_mode(base_url, model_name)

    if provider_mode == 'anthropic':
        return jsonify({
            "success": True,
            "data": {
                "provider": "anthropic",
                "models": _COMMON_CLAUDE_MODELS,
                "note": "Anthropic-compatible providers may not expose a model listing endpoint. Showing common Claude models.",
            },
        })

    # OpenAI-compatible: try to fetch from /v1/models
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key or 'placeholder',
            base_url=base_url,
            timeout=15.0,
        )
        models_response = client.models.list()
        models = []
        for m in models_response.data:
            models.append({
                "id": m.id,
                "name": m.id,
                "provider": "openai-compatible",
                "owned_by": getattr(m, 'owned_by', 'unknown'),
            })
        return jsonify({
            "success": True,
            "data": {
                "provider": "openai-compatible",
                "models": models,
            },
        })
    except Exception as exc:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch models: {str(exc)[:200]}",
            "data": {
                "provider": "openai-compatible",
                "models": [],
                "configured_model": model_name,
                "base_url": base_url,
            },
        }), 502
