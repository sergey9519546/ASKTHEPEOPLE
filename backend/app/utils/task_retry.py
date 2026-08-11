"""Shared retry classification for Celery-owned external operations."""

import time
from collections.abc import Callable
from typing import TypeVar


_T = TypeVar("_T")

_DETERMINISTIC_ERROR_NAMES = {
    "ProfileValidationError",
    "InputPolicyError",
    "ValueError",
    "KeyError",
    "TypeError",
    "AttributeError",
    "FileNotFoundError",
    "SafePathError",
}


def is_retryable_task_exception(exc: BaseException) -> bool:
    """Return whether an external-operation failure is plausibly transient."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    name = type(exc).__name__
    if name in {
        "ConnectionError",
        "ConnectionResetError",
        "ConnectionRefusedError",
        "ConnectTimeout",
        "ReadTimeout",
        "TimeoutError",
        "BrokerConnectionError",
        "OperationalError",
    }:
        return True

    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500

    if name in _DETERMINISTIC_ERROR_NAMES:
        return False

    return False


def retry_transient_operation(
    operation: Callable[[], _T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.25,
) -> _T:
    """Retry one replay-safe read operation with a small bounded backoff."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as exc:
            if attempt + 1 >= max_attempts or not is_retryable_task_exception(exc):
                raise
            time.sleep(base_delay * (2**attempt))

    raise RuntimeError("unreachable")
