"""Bounded, read-only dependency status for Zep-backed capabilities.

The probe deliberately retrieves only project metadata and discards the
response. It never touches graph APIs and never treats provider state as
canonical application data.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zep_cloud.client import Zep

from ..utils.logger import get_logger


logger = get_logger("askthepeople.zep_dependency_status")

_SUCCESS_TTL_SECONDS = 30.0
_FAILURE_TTL_SECONDS = 10.0
_PROBE_TIMEOUT_SECONDS = 2.0
_TIMEOUT_ERROR_NAMES = {
    "ConnectTimeout",
    "PoolTimeout",
    "ReadTimeout",
    "TimeoutException",
    "WriteTimeout",
}
_CONNECTION_ERROR_NAMES = {
    "ConnectError",
    "ConnectionError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "NetworkError",
    "ProtocolError",
    "RemoteProtocolError",
}
_SUPPRESS_READINESS_TRANSPORT_LOGS: ContextVar[bool] = ContextVar(
    "suppress_zep_readiness_transport_logs",
    default=False,
)


class _ReadinessTransportLogFilter(logging.Filter):
    """Hide transport endpoints only in the readiness probe's context."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not _SUPPRESS_READINESS_TRANSPORT_LOGS.get()


_READINESS_TRANSPORT_FILTER = _ReadinessTransportLogFilter()


def _install_readiness_transport_filters() -> None:
    names = {"httpx", "httpcore"}
    names.update(
        name
        for name in logging.root.manager.loggerDict
        if name.startswith("httpx.") or name.startswith("httpcore.")
    )
    for name in names:
        transport_logger = logging.getLogger(name)
        if _READINESS_TRANSPORT_FILTER not in transport_logger.filters:
            transport_logger.addFilter(_READINESS_TRANSPORT_FILTER)


def _new_zep_client(*, api_key: str, timeout: float) -> Zep:
    return Zep(api_key=api_key, timeout=timeout)


@dataclass(frozen=True)
class _CacheEntry:
    key_digest: bytes
    status: str
    reason: str
    checked_at: str
    observed_at: float
    expires_at: float


def _safe_status_code(exc: BaseException) -> int | None:
    raw_status = getattr(exc, "status_code", None)
    try:
        return int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        return None


def _classify_failure(exc: BaseException) -> tuple[str, int | None]:
    status_code = _safe_status_code(exc)
    if status_code in {401, 403}:
        return "authentication_failed", status_code
    if status_code == 408:
        return "timeout", status_code
    if status_code == 429:
        return "rate_limited", status_code
    if status_code is not None and status_code >= 500:
        return "unavailable", status_code

    name = type(exc).__name__
    if isinstance(exc, TimeoutError) or name in _TIMEOUT_ERROR_NAMES:
        return "timeout", status_code
    if isinstance(exc, (ConnectionError, OSError)) or name in _CONNECTION_ERROR_NAMES:
        return "unavailable", status_code
    return "probe_failed", status_code


class ZepDependencyMonitor:
    """Thread-safe process-local cache around one bounded read-only probe."""

    def __init__(
        self,
        *,
        client_factory: Callable[..., Any] = _new_zep_client,
        monotonic: Callable[[], float] = time.monotonic,
        utcnow: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._monotonic = monotonic
        self._utcnow = utcnow or (lambda: datetime.now(UTC))
        self._fingerprint_salt = secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._cache: _CacheEntry | None = None

    def _key_digest(self, api_key: str) -> bytes:
        return hmac.new(
            self._fingerprint_salt,
            api_key.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def _public_status(
        self,
        entry: _CacheEntry,
        *,
        cached: bool,
        now: float,
    ) -> dict[str, object]:
        return {
            "status": entry.status,
            "reason": entry.reason,
            "cached": cached,
            # Stale success is never served. An expired entry is synchronously
            # refreshed under the lock before this method is called.
            "stale": False,
            "checked_at": entry.checked_at,
            "age_seconds": max(0.0, now - entry.observed_at),
        }

    def check(self, api_key: str | None) -> dict[str, object]:
        normalized_key = str(api_key or "").strip()
        key_digest = self._key_digest(normalized_key)

        with self._lock:
            now = self._monotonic()
            entry = self._cache
            if (
                entry is not None
                and hmac.compare_digest(entry.key_digest, key_digest)
                and now < entry.expires_at
            ):
                return self._public_status(entry, cached=True, now=now)

            status = "error"
            reason = "not_configured"
            ttl = _FAILURE_TTL_SECONDS

            if normalized_key:
                try:
                    _install_readiness_transport_filters()
                    context_token = _SUPPRESS_READINESS_TRANSPORT_LOGS.set(True)
                    try:
                        client = self._client_factory(
                            api_key=normalized_key,
                            timeout=_PROBE_TIMEOUT_SECONDS,
                        )
                        # This is the complete provider interaction. The
                        # returned object is intentionally ignored and never
                        # cached.
                        client.project.get()
                    finally:
                        _SUPPRESS_READINESS_TRANSPORT_LOGS.reset(context_token)
                    status = "ok"
                    reason = "available"
                    ttl = _SUCCESS_TTL_SECONDS
                except Exception as exc:
                    reason, status_code = _classify_failure(exc)
                    logger.warning(
                        "Zep readiness probe failed reason=%s exception=%s status=%s",
                        reason,
                        type(exc).__name__,
                        status_code,
                        extra={"privacy_safe": True},
                    )

            checked_at_value = self._utcnow()
            if checked_at_value.tzinfo is None:
                checked_at_value = checked_at_value.replace(tzinfo=UTC)
            checked_at = checked_at_value.astimezone(UTC).isoformat().replace(
                "+00:00",
                "Z",
            )
            observed_at = self._monotonic()
            entry = _CacheEntry(
                key_digest=key_digest,
                status=status,
                reason=reason,
                checked_at=checked_at,
                observed_at=observed_at,
                expires_at=observed_at + ttl,
            )
            self._cache = entry
            return self._public_status(entry, cached=False, now=observed_at)


_default_monitor = ZepDependencyMonitor()


def check_zep_dependency(api_key: str | None) -> dict[str, object]:
    """Return sanitized Zep status without exposing provider response data."""
    return _default_monitor.check(api_key)
