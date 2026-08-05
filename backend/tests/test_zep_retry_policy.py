"""Zep retries must distinguish transient failures from permanent ones.

_call_with_retry caught bare Exception and retried everything with exponential
backoff. A 401 from a wrong ZEP_API_KEY, or a 404 for a graph that does not
exist, fails identically on every attempt — so the retries only spent the
backoff. With the defaults (MAX_RETRIES=3, RETRY_DELAY=2.0) that is ~6s per
call, and report generation issues many calls per section, which presents a
clear configuration error as flakiness.
"""

import pytest

from app.services.zep_tools import ZepToolsService


class FakeApiError(Exception):
    """Stands in for zep_cloud.core.ApiError, which carries status_code."""

    def __init__(self, status_code):
        super().__init__(f"api error {status_code}")
        self.status_code = status_code


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(ZepToolsService, "__init__", lambda self: None)
    svc = ZepToolsService()
    svc.MAX_RETRIES = 3
    svc.RETRY_DELAY = 0.0
    return svc


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_are_not_retryable(status):
    assert ZepToolsService._is_retryable(FakeApiError(status)) is False


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_server_errors_are_retryable(status):
    assert ZepToolsService._is_retryable(FakeApiError(status)) is True


def test_rate_limiting_is_retryable():
    assert ZepToolsService._is_retryable(FakeApiError(429)) is True


def test_transport_failures_without_a_status_are_retryable():
    # Timeouts and reset connections carry no status_code.
    assert ZepToolsService._is_retryable(TimeoutError("read timed out")) is True
    assert ZepToolsService._is_retryable(ConnectionError("reset by peer")) is True


# --------------------------------------------------------------------------- #
# Behaviour through _call_with_retry
# --------------------------------------------------------------------------- #

def test_a_permanent_error_is_raised_on_the_first_attempt(service):
    calls = []

    def boom():
        calls.append(1)
        raise FakeApiError(401)

    with pytest.raises(FakeApiError):
        service._call_with_retry(boom, "search")

    assert len(calls) == 1, "a 401 must not be retried"


def test_a_transient_error_is_retried_to_the_limit(service):
    calls = []

    def boom():
        calls.append(1)
        raise FakeApiError(503)

    with pytest.raises(FakeApiError):
        service._call_with_retry(boom, "search")

    assert len(calls) == service.MAX_RETRIES


def test_a_transient_error_that_clears_returns_the_value(service):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise FakeApiError(503)
        return "ok"

    assert service._call_with_retry(flaky, "search") == "ok"
    assert len(calls) == 2


def test_success_on_the_first_attempt_does_not_retry(service):
    calls = []

    def fine():
        calls.append(1)
        return "ok"

    assert service._call_with_retry(fine, "search") == "ok"
    assert len(calls) == 1


def test_the_original_exception_propagates_unwrapped(service):
    """Callers match on the Zep error type; wrapping it would break them."""
    original = FakeApiError(404)

    def boom():
        raise original

    with pytest.raises(FakeApiError) as excinfo:
        service._call_with_retry(boom, "search")

    assert excinfo.value is original
