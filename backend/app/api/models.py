"""Privileged, operator-allowlisted catalog for OpenAI-compatible endpoints."""

from __future__ import annotations

import os

from flask import Blueprint, jsonify

from ..config import Config
from .settings import SettingsValidationError, _runtime_settings_enabled, _validate_base_url

models_bp = Blueprint('models', __name__)


def _configured_provider() -> tuple[str, str]:
    """Select an endpoint and credential together; never borrow another key."""
    if Config.LLM_BASE_URL or Config.LLM_API_KEY:
        return Config.LLM_BASE_URL or '', Config.LLM_API_KEY or ''
    return (
        os.environ.get('LLM_BOOST_BASE_URL', ''),
        os.environ.get('LLM_BOOST_API_KEY', ''),
    )


@models_bp.route('', methods=['GET'])
def list_models():
    """List models only through the explicitly enabled settings control plane."""
    if not _runtime_settings_enabled():
        return jsonify({"success": False, "error": "runtime_settings_disabled"}), 403

    raw_url, api_key = _configured_provider()
    try:
        # Validate raw input: normalization must not erase native /messages.
        base_url = _validate_base_url(raw_url)
    except SettingsValidationError as exc:
        return jsonify({
            "success": False,
            "error": "model_catalog_endpoint_rejected",
            # The shared validator supplies fixed policy messages, never URLs
            # or provider exception text. This also explains native refusal.
            "message": str(exc),
        }), 400

    if not api_key:
        return jsonify({"success": False, "error": "model_catalog_unconfigured"}), 503

    try:
        from openai import OpenAI

        with OpenAI(api_key=api_key, base_url=base_url, timeout=15.0) as client:
            models_response = client.models.list()
            models = [{
                "id": model.id,
                "name": model.id,
                "provider": "openai-compatible",
                "owned_by": getattr(model, 'owned_by', 'unknown'),
            } for model in models_response.data]
        return jsonify({
            "success": True,
            "data": {"provider": "openai-compatible", "models": models},
        })
    except Exception:
        return jsonify({"success": False, "error": "model_catalog_unavailable"}), 502
