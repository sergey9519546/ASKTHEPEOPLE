"""Focused contract tests for the read-only cached Zep readiness probe."""

from __future__ import annotations

import importlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest


class FakeClock:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self.started_at = datetime(2026, 8, 8, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.elapsed

    def now(self) -> datetime:
        return self.started_at + timedelta(seconds=self.elapsed)

    def advance(self, seconds: float) -> None:
        self.elapsed += seconds


class ProviderError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _contract():
    try:
        module = importlib.import_module("app.services.zep_dependency_status")
    except ModuleNotFoundError:
        pytest.fail(
            "cached Zep dependency status module is not implemented",
            pytrace=False,
        )
    return module


def _monitor(*, factory, clock: FakeClock):
    return _contract().ZepDependencyMonitor(
        client_factory=factory,
        monotonic=clock.monotonic,
        utcnow=clock.now,
    )


def test_probe_uses_only_project_get_and_discards_provider_payload():
    clock = FakeClock()
    calls: list[dict[str, object]] = []

    class Client:
        class Project:
            def get(self):
                return {
                    "private_project": "provider-project-secret",
                    "graph_ids": ["must-not-escape"],
                }

        project = Project()

        @property
        def graph(self):
            raise AssertionError("readiness must never touch graph APIs")

    def factory(**kwargs):
        calls.append(kwargs)
        return Client()

    result = _monitor(factory=factory, clock=clock).check("zep-secret-value")

    assert result["status"] == "ok"
    assert result["reason"] == "available"
    assert result["cached"] is False
    assert result["stale"] is False
    assert calls == [{"api_key": "zep-secret-value", "timeout": 2.0}]
    assert "provider-project-secret" not in repr(result)
    assert "must-not-escape" not in repr(result)
    assert "zep-secret-value" not in repr(result)


def test_success_is_cached_for_thirty_seconds_then_refreshed():
    clock = FakeClock()
    calls = 0

    class Client:
        class Project:
            @staticmethod
            def get():
                return object()

        project = Project()

    def factory(**_kwargs):
        nonlocal calls
        calls += 1
        return Client()

    monitor = _monitor(factory=factory, clock=clock)

    assert monitor.check("key")["cached"] is False
    clock.advance(29.9)
    cached = monitor.check("key")
    assert cached["cached"] is True
    assert cached["age_seconds"] == pytest.approx(29.9)
    assert calls == 1

    clock.advance(0.2)
    refreshed = monitor.check("key")
    assert refreshed["cached"] is False
    assert refreshed["age_seconds"] == 0
    assert calls == 2


def test_failure_is_cached_for_ten_seconds_then_can_recover():
    clock = FakeClock()
    calls = 0

    class HealthyClient:
        class Project:
            @staticmethod
            def get():
                return object()

        project = Project()

    def factory(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("provider-body-must-not-escape")
        return HealthyClient()

    monitor = _monitor(factory=factory, clock=clock)
    failed = monitor.check("key")
    assert failed["status"] == "error"
    assert failed["reason"] == "timeout"

    clock.advance(9.9)
    assert monitor.check("key")["cached"] is True
    assert calls == 1

    clock.advance(0.2)
    recovered = monitor.check("key")
    assert recovered["status"] == "ok"
    assert recovered["cached"] is False
    assert calls == 2


def test_expired_success_is_never_reused_after_refresh_failure():
    clock = FakeClock()
    calls = 0

    class Client:
        class Project:
            def get(self):
                nonlocal calls
                if calls > 1:
                    raise ConnectionError("private upstream response")
                return object()

        project = Project()

    def factory(**_kwargs):
        nonlocal calls
        calls += 1
        return Client()

    monitor = _monitor(factory=factory, clock=clock)
    assert monitor.check("key")["status"] == "ok"

    clock.advance(30.1)
    result = monitor.check("key")
    assert result["status"] == "error"
    assert result["reason"] == "unavailable"
    assert result["stale"] is False
    assert result["cached"] is False


def test_key_change_invalidates_a_fresh_cache_without_exposing_either_key():
    clock = FakeClock()
    keys: list[str] = []

    class Client:
        class Project:
            @staticmethod
            def get():
                return object()

        project = Project()

    def factory(*, api_key, **_kwargs):
        keys.append(api_key)
        return Client()

    monitor = _monitor(factory=factory, clock=clock)
    first = monitor.check("old-secret")
    second = monitor.check("new-secret")

    assert first["cached"] is False
    assert second["cached"] is False
    assert keys == ["old-secret", "new-secret"]
    assert "old-secret" not in repr(second)
    assert "new-secret" not in repr(second)


@pytest.mark.parametrize(
    ("exc", "reason"),
    [
        (ProviderError("private-401-body", status_code=401), "authentication_failed"),
        (ProviderError("private-403-body", status_code=403), "authentication_failed"),
        (ProviderError("private-408-body", status_code=408), "timeout"),
        (ProviderError("private-429-body", status_code=429), "rate_limited"),
        (ProviderError("private-500-body", status_code=500), "unavailable"),
        (ConnectionError("private-host"), "unavailable"),
        (TimeoutError("private-timeout"), "timeout"),
        (ValueError("private-provider-body"), "probe_failed"),
    ],
)
def test_provider_errors_map_to_bounded_reasons(exc, reason):
    clock = FakeClock()

    def factory(**_kwargs):
        raise exc

    result = _monitor(factory=factory, clock=clock).check("never-return-this-key")

    assert result["status"] == "error"
    assert result["reason"] == reason
    assert str(exc) not in repr(result)
    assert "never-return-this-key" not in repr(result)


def test_missing_key_is_non_networked_and_key_appearance_invalidates_cache():
    clock = FakeClock()
    calls = 0

    class Client:
        class Project:
            @staticmethod
            def get():
                return object()

        project = Project()

    def factory(**_kwargs):
        nonlocal calls
        calls += 1
        return Client()

    monitor = _monitor(factory=factory, clock=clock)
    missing = monitor.check("   ")
    configured = monitor.check("configured-key")

    assert missing["status"] == "error"
    assert missing["reason"] == "not_configured"
    assert configured["status"] == "ok"
    assert calls == 1


def test_concurrent_refreshes_make_one_provider_call():
    clock = FakeClock()
    provider_started = threading.Event()
    release_provider = threading.Event()
    calls = 0

    class Client:
        class Project:
            @staticmethod
            def get():
                provider_started.set()
                assert release_provider.wait(timeout=2)
                return object()

        project = Project()

    def factory(**_kwargs):
        nonlocal calls
        calls += 1
        return Client()

    monitor = _monitor(factory=factory, clock=clock)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(monitor.check, "key") for _ in range(4)]
        assert provider_started.wait(timeout=2)
        release_provider.set()
        results = [future.result(timeout=2) for future in futures]

    assert calls == 1
    assert sum(result["cached"] is False for result in results) == 1
    assert all(result["status"] == "ok" for result in results)


def test_warning_log_uses_only_bounded_metadata(monkeypatch):
    module = _contract()
    clock = FakeClock()
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class SpyLogger:
        def warning(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setattr(module, "logger", SpyLogger())

    def factory(**_kwargs):
        raise ProviderError(
            "secret-provider-body https://private.example zep-secret-value",
            status_code=503,
        )

    result = module.ZepDependencyMonitor(
        client_factory=factory,
        monotonic=clock.monotonic,
        utcnow=clock.now,
    ).check("zep-secret-value")

    rendered = repr(calls)
    assert result["reason"] == "unavailable"
    assert "secret-provider-body" not in rendered
    assert "private.example" not in rendered
    assert "zep-secret-value" not in rendered
    assert "unavailable" in rendered
    assert "503" in rendered


def test_readiness_suppresses_only_http_transport_endpoint_logs():
    clock = FakeClock()
    transport_messages: list[str] = []
    app_messages: list[str] = []

    class Capture(logging.Handler):
        def __init__(self, target: list[str]) -> None:
            super().__init__()
            self.target = target

        def emit(self, record: logging.LogRecord) -> None:
            self.target.append(record.getMessage())

    transport_loggers = [
        logging.getLogger("httpx"),
        logging.getLogger("httpcore.connection"),
    ]
    app_logger = logging.getLogger("askthepeople.readiness-test")
    old_state = [
        (logger, list(logger.handlers), logger.level, logger.propagate)
        for logger in [*transport_loggers, app_logger]
    ]
    try:
        for transport_logger in transport_loggers:
            transport_logger.handlers = [Capture(transport_messages)]
            transport_logger.setLevel(logging.INFO)
            transport_logger.propagate = False
        app_logger.handlers = [Capture(app_messages)]
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = False

        class Client:
            class Project:
                @staticmethod
                def get():
                    logging.getLogger("httpx").info(
                        "GET https://private.zep.example/projects/private-project"
                    )
                    logging.getLogger("httpcore.connection").info(
                        "connect_tcp host=private.zep.example"
                    )
                    app_logger.info("bounded readiness diagnostic")
                    return object()

            project = Project()

        monitor = _monitor(factory=lambda **_kwargs: Client(), clock=clock)
        assert monitor.check("secret-key")["status"] == "ok"

        # The filter must be context-bound: normal transport diagnostics after
        # the readiness call remain available.
        logging.getLogger("httpx").info("outside readiness remains visible")
    finally:
        for logger, handlers, level, propagate in old_state:
            logger.handlers = handlers
            logger.setLevel(level)
            logger.propagate = propagate

    assert "bounded readiness diagnostic" in app_messages
    assert transport_messages == ["outside readiness remains visible"]
