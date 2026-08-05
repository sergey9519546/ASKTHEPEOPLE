"""Retry classification for the Celery simulation tasks (ADR-0003).

A task failure is only worth retrying if a retry could plausibly succeed.
Deterministic failures (validation, input policy, missing files, bad input)
must fail immediately so the user sees the real error; transient failures
(connection resets, broker timeouts, 429/5xx) retry with backoff.

These tests pin the classification predicate; the wiring into the task bodies
(self.retry gated by _is_retryable_task_exception) is exercised by the
dispatch suite.
"""

import pytest

from app.tasks.simulation_tasks import _is_retryable_task_exception
from app.utils.input_policy import InputPolicyError


class _HttpStatusError(Exception):
    """Stand-in for a provider SDK error carrying an HTTP status code."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: ConnectionError("broker reset"),
        lambda: TimeoutError("read timed out"),
        lambda: ConnectionResetError("connection reset"),
        lambda: _HttpStatusError("rate limited", 429),
        lambda: _HttpStatusError("bad gateway", 502),
        lambda: _HttpStatusError("server error", 500),
    ],
    ids=["connection", "timeout", "reset", "429", "502", "500"],
)
def test_transient_failures_are_retryable(exc_factory):
    assert _is_retryable_task_exception(exc_factory()) is True


@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: ValueError("bad simulation id"),
        lambda: InputPolicyError("text_field_too_long", "too long"),
        lambda: FileNotFoundError("missing config"),
        lambda: KeyError("agent_configs"),
        lambda: TypeError("not subscriptable"),
        lambda: _HttpStatusError("not found", 404),
        lambda: _HttpStatusError("bad request", 400),
        lambda: _HttpStatusError("unauthorized", 401),
    ],
    ids=[
        "valueerror",
        "inputpolicy",
        "filenotfound",
        "keyerror",
        "typeerror",
        "404",
        "400",
        "401",
    ],
)
def test_deterministic_failures_are_not_retryable(exc_factory):
    """A retry of a deterministic failure burns the backoff budget and delays
    the real error. These must fail immediately."""
    assert _is_retryable_task_exception(exc_factory()) is False


def test_unknown_error_defaults_to_non_retryable():
    """A surprise exception is more likely a bug than a transient blip.
    Defaulting to non-retry prevents silent retries from masking real issues."""

    class Surprise(Exception):
        pass

    assert _is_retryable_task_exception(Surprise("???")) is False
