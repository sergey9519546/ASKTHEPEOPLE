"""
Privileged provider-settings control plane.

Reading configuration never returns credential fragments. Runtime mutation and
connection testing are disabled unless an operator explicitly enables them
with ALLOW_RUNTIME_SETTINGS=true. In production the existing APP_TOKEN must
also be configured.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
from urllib.parse import urlsplit, urlunsplit

from flask import current_app, jsonify, request

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from . import settings_bp

logger = get_logger("askthepeople.settings")

_SECRET_KEYS = (
    "LLM_API_KEY",
    "ZEP_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "LLM_BOOST_API_KEY",
)
_TEXT_KEYS = (
    "LLM_MODEL_NAME",
    "LLM_BOOST_MODEL_NAME",
)
_URL_KEYS = (
    "LLM_BASE_URL",
    "LLM_BOOST_BASE_URL",
)
_ALL_MUTABLE_KEYS = _SECRET_KEYS + _TEXT_KEYS + _URL_KEYS
_MAX_SECRET_LENGTH = 8192
_MAX_TEXT_LENGTH = 256
_MAX_URL_LENGTH = 2048


class SettingsValidationError(ValueError):
    """Raised for rejected settings-control-plane input."""


def _runtime_settings_enabled() -> bool:
    if not current_app.config.get("ALLOW_RUNTIME_SETTINGS", False):
        return False
    # An explicitly enabled local debug instance may remain header-free.
    # Production mutation/testing must also pass the global bearer guard.
    if not current_app.config.get("DEBUG", False) and not current_app.config.get("APP_TOKEN"):
        return False
    return True


def _configuration_metadata() -> dict:
    """Return useful status without returning any credential material."""
    runtime_enabled = _runtime_settings_enabled()
    return {
        # Keep empty credential fields for compatibility with the settings
        # form, but never reveal prefixes, suffixes, lengths, or placeholders.
        **{key: "" for key in _SECRET_KEYS},
        "LLM_API_KEY_CONFIGURED": bool(Config.LLM_API_KEY),
        "ZEP_API_KEY_CONFIGURED": bool(Config.ZEP_API_KEY),
        "BRAVE_SEARCH_API_KEY_CONFIGURED": bool(os.environ.get("BRAVE_SEARCH_API_KEY")),
        "LLM_BOOST_API_KEY_CONFIGURED": bool(os.environ.get("LLM_BOOST_API_KEY")),
        # Provider topology/model details are only needed by the explicitly
        # enabled control plane. A public read-only status endpoint gets
        # presence booleans, not internal endpoint metadata.
        "LLM_BASE_URL": Config.LLM_BASE_URL if runtime_enabled else "",
        "LLM_MODEL_NAME": Config.LLM_MODEL_NAME if runtime_enabled else "",
        "LLM_BOOST_BASE_URL": (
            os.environ.get("LLM_BOOST_BASE_URL", "") if runtime_enabled else ""
        ),
        "LLM_BOOST_MODEL_NAME": (
            os.environ.get("LLM_BOOST_MODEL_NAME", "") if runtime_enabled else ""
        ),
        "runtime_settings_enabled": runtime_enabled,
        "allowed_llm_base_urls": (
            sorted(_allowed_base_urls()) if runtime_enabled else []
        ),
        "allow_private_llm_endpoints": (
            bool(current_app.config.get("ALLOW_PRIVATE_LLM_ENDPOINTS", False))
            if runtime_enabled
            else False
        ),
    }


def _clean_value(key: str, value: object) -> str:
    if not isinstance(value, str):
        raise SettingsValidationError(f"{key} must be a string")
    if any(char in value for char in ("\r", "\n", "\x00")):
        raise SettingsValidationError(f"{key} contains invalid control characters")
    cleaned = value.strip()
    max_length = (
        _MAX_SECRET_LENGTH if key in _SECRET_KEYS
        else _MAX_URL_LENGTH if key in _URL_KEYS
        else _MAX_TEXT_LENGTH
    )
    if len(cleaned) > max_length:
        raise SettingsValidationError(f"{key} is too long")
    return cleaned


def _normalize_base_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        # Accessing .port also validates the numeric range.
        _ = parsed.port
    except ValueError as exc:
        raise SettingsValidationError("Invalid LLM base URL") from exc

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SettingsValidationError("LLM base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SettingsValidationError(
            "LLM base URL cannot contain credentials, a query, or a fragment"
        )

    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", path, "", ""))


def _allowed_base_urls() -> set[str]:
    raw = current_app.config.get("LLM_ALLOWED_BASE_URLS", "")
    allowed: set[str] = set()
    for entry in str(raw).split(","):
        entry = entry.strip()
        if entry:
            allowed.add(_normalize_base_url(entry))
    return allowed


def _validate_base_url(value: str) -> str:
    normalized = _normalize_base_url(value)
    if normalized not in _allowed_base_urls():
        raise SettingsValidationError(
            "LLM base URL is not in the operator allowlist"
        )

    parsed = urlsplit(normalized)
    allow_private = current_app.config.get("ALLOW_PRIVATE_LLM_ENDPOINTS", False)
    if parsed.scheme != "https" and not allow_private:
        raise SettingsValidationError("LLM base URL must use HTTPS")

    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise SettingsValidationError("LLM base URL host could not be resolved") from exc

    if not addresses:
        raise SettingsValidationError("LLM base URL host could not be resolved")
    if not allow_private:
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise SettingsValidationError(
                    "LLM base URL resolves to a private or reserved address"
                )
    return normalized


def _persist_settings(settings: dict[str, str]) -> None:
    env_path = os.path.abspath(
        current_app.config.get("RUNTIME_SETTINGS_ENV_PATH", Config.RUNTIME_SETTINGS_ENV_PATH)
    )
    env_dir = os.path.dirname(env_path)
    os.makedirs(env_dir, exist_ok=True)

    lines: list[str] = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

    updated: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in settings:
                output.append(f"{key}={settings[key]}\n")
                updated.add(key)
                continue
        output.append(line)

    for key, value in settings.items():
        if key not in updated:
            if output and not output[-1].endswith("\n"):
                output[-1] += "\n"
            output.append(f"{key}={value}\n")

    fd, temp_path = tempfile.mkstemp(prefix=".settings-", dir=env_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.writelines(output)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, env_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _apply_in_memory(settings: dict[str, str]) -> None:
    for key, value in settings.items():
        os.environ[key] = value
    if "LLM_API_KEY" in settings:
        Config.LLM_API_KEY = settings["LLM_API_KEY"]
    if "LLM_BASE_URL" in settings:
        Config.LLM_BASE_URL = settings["LLM_BASE_URL"]
    if "LLM_MODEL_NAME" in settings:
        Config.LLM_MODEL_NAME = settings["LLM_MODEL_NAME"]
    if "ZEP_API_KEY" in settings:
        Config.ZEP_API_KEY = settings["ZEP_API_KEY"]


@settings_bp.route("", methods=["GET"])
def get_settings():
    """Return non-secret provider metadata and control-plane availability."""
    return jsonify({"success": True, "data": _configuration_metadata()})


@settings_bp.route("", methods=["POST"])
def update_settings():
    """Update allowlisted provider settings when explicitly enabled."""
    if not _runtime_settings_enabled():
        return jsonify({
            "success": False,
            "error": "runtime_settings_disabled",
        }), 403

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise SettingsValidationError("JSON object required")

        settings: dict[str, str] = {}
        for key in _ALL_MUTABLE_KEYS:
            if key not in data:
                continue
            value = _clean_value(key, data[key])
            if value:
                settings[key] = value

        if not settings:
            raise SettingsValidationError("No settings were provided")

        if "LLM_BASE_URL" in settings:
            settings["LLM_BASE_URL"] = _validate_base_url(settings["LLM_BASE_URL"])
            if (
                settings["LLM_BASE_URL"] != _normalize_base_url(Config.LLM_BASE_URL)
                and "LLM_API_KEY" not in settings
            ):
                raise SettingsValidationError(
                    "A new API key is required when changing the LLM base URL"
                )

        current_boost_url = os.environ.get("LLM_BOOST_BASE_URL", "")
        if "LLM_BOOST_BASE_URL" in settings:
            settings["LLM_BOOST_BASE_URL"] = _validate_base_url(
                settings["LLM_BOOST_BASE_URL"]
            )
            if (
                settings["LLM_BOOST_BASE_URL"]
                != (_normalize_base_url(current_boost_url) if current_boost_url else "")
                and "LLM_BOOST_API_KEY" not in settings
            ):
                raise SettingsValidationError(
                    "A new boost API key is required when changing the boost base URL"
                )

        _persist_settings(settings)
        _apply_in_memory(settings)
        return jsonify({
            "success": True,
            "message": "Settings saved successfully",
            "data": _configuration_metadata(),
        })
    except SettingsValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.warning(
            "Failed to update runtime settings (%s)",
            type(exc).__name__,
        )
        return jsonify({
            "success": False,
            "error": "configuration_update_failed",
        }), 500


@settings_bp.route("/test", methods=["POST"])
def test_settings():
    """Test an operator-allowlisted endpoint using only caller-supplied credentials."""
    if not _runtime_settings_enabled():
        return jsonify({
            "success": False,
            "error": "runtime_settings_disabled",
        }), 403

    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise SettingsValidationError("JSON object required")

        target = data.get("target", "llm")
        if target == "zep" or ("ZEP_API_KEY" in data and "LLM_API_KEY" not in data):
            zep_key = _clean_value("ZEP_API_KEY", data.get("ZEP_API_KEY", Config.ZEP_API_KEY or ""))
            if not zep_key:
                raise SettingsValidationError("ZEP_API_KEY is required to test Zep connection")
            from zep_cloud.client import Zep
            zep_client = Zep(api_key=zep_key)
            try:
                zep_client.project.get()
            except Exception as zep_exc:
                logger.warning("Zep API test failed: %s", zep_exc)
                raise SettingsValidationError(f"Zep connection test failed: {str(zep_exc)[:100]}")
            return jsonify({
                "success": True,
                "message": "Zep API connection test succeeded",
            })

        api_key = _clean_value("LLM_API_KEY", data.get("LLM_API_KEY", ""))
        base_url = _clean_value("LLM_BASE_URL", data.get("LLM_BASE_URL", ""))
        model = _clean_value("LLM_MODEL_NAME", data.get("LLM_MODEL_NAME", ""))
        if not api_key:
            raise SettingsValidationError("API Key is required to run test")
        if not base_url:
            raise SettingsValidationError("Base URL is required to run test")
        if not model:
            raise SettingsValidationError("Model Name is required to run test")
        base_url = _validate_base_url(base_url)

        client = LLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=15.0,
        )
        response = client.chat(
            messages=[{"role": "user", "content": "Respond with only one word: Connected"}],
            max_tokens=10,
        )
        return jsonify({
            "success": True,
            "message": "Connection test succeeded",
            "response": response,
        })
    except SettingsValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.warning(
            "Provider connection test failed (%s)",
            type(exc).__name__,
        )
        return jsonify({
            "success": False,
            "error": "connection_test_failed",
        }), 502

