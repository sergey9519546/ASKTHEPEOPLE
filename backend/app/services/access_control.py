"""Small, signed credentials used at browser-only transport seams."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from typing import Any


_WS_TICKET_VERSION = 1
_WS_TICKET_TTL_SECONDS = 60
_RESOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_ALLOWED_WS_SCOPES = {"simulation", "report"}
_USED_WS_TICKET_NONCES: dict[str, int] = {}
_USED_WS_TICKET_NONCES_LOCK = threading.Lock()


class AccessTicketError(ValueError):
    """Raised when a short-lived access ticket is invalid or expired."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise AccessTicketError("malformed_ticket") from exc


def _validate_scope(scope: str, resource_id: str) -> None:
    if scope not in _ALLOWED_WS_SCOPES:
        raise AccessTicketError("invalid_scope")
    if not _RESOURCE_ID_PATTERN.fullmatch(resource_id):
        raise AccessTicketError("invalid_resource_id")


def issue_ws_ticket(
    secret_key: str,
    scope: str,
    resource_id: str,
    *,
    now: int | None = None,
) -> tuple[str, int]:
    """Issue a signed, short-lived ticket bound to one WebSocket resource."""
    if not secret_key:
        raise AccessTicketError("ticket_signing_not_configured")
    _validate_scope(scope, resource_id)

    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + _WS_TICKET_TTL_SECONDS
    payload: dict[str, Any] = {
        "v": _WS_TICKET_VERSION,
        "scope": scope,
        "resource_id": resource_id,
        "iat": issued_at,
        "exp": expires_at,
        "nonce": secrets.token_urlsafe(12),
    }
    encoded_payload = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}", expires_at


def verify_ws_ticket(
    ticket: str,
    secret_key: str,
    scope: str,
    resource_id: str,
    *,
    now: int | None = None,
) -> None:
    """Verify and atomically consume a single-use browser transport ticket."""
    if not ticket or not secret_key:
        raise AccessTicketError("missing_ticket")
    _validate_scope(scope, resource_id)

    try:
        encoded_payload, encoded_signature = ticket.split(".", 1)
    except ValueError as exc:
        raise AccessTicketError("malformed_ticket") from exc

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    supplied_signature = _decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise AccessTicketError("invalid_ticket")

    try:
        payload = json.loads(_decode(encoded_payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AccessTicketError("malformed_ticket") from exc

    current_time = int(time.time() if now is None else now)
    if payload.get("v") != _WS_TICKET_VERSION:
        raise AccessTicketError("invalid_ticket_version")
    if payload.get("scope") != scope or payload.get("resource_id") != resource_id:
        raise AccessTicketError("ticket_scope_mismatch")
    if not isinstance(payload.get("iat"), int) or not isinstance(payload.get("exp"), int):
        raise AccessTicketError("malformed_ticket")
    if not isinstance(payload.get("nonce"), str) or not payload["nonce"]:
        raise AccessTicketError("malformed_ticket")
    if payload["iat"] > current_time + 5:
        raise AccessTicketError("ticket_not_yet_valid")
    if payload["exp"] <= current_time:
        raise AccessTicketError("expired_ticket")
    if payload["exp"] - payload["iat"] > _WS_TICKET_TTL_SECONDS:
        raise AccessTicketError("invalid_ticket_lifetime")

    nonce = payload["nonce"]
    with _USED_WS_TICKET_NONCES_LOCK:
        expired_nonces = [
            used_nonce
            for used_nonce, expires_at in _USED_WS_TICKET_NONCES.items()
            if expires_at <= current_time
        ]
        for used_nonce in expired_nonces:
            _USED_WS_TICKET_NONCES.pop(used_nonce, None)
        if nonce in _USED_WS_TICKET_NONCES:
            raise AccessTicketError("ticket_replayed")
        _USED_WS_TICKET_NONCES[nonce] = payload["exp"]
