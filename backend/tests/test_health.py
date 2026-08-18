import pytest
import time
from types import SimpleNamespace
from app import create_app

@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        "app.api.health.check_zep_dependency",
        lambda: {
            "status": "ok",
            "reason": "available",
            "cached": False,
            "stale": False,
            "checked_at": "2026-08-08T00:00:00Z",
            "age_seconds": 0.0,
        },
    )
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_liveness(client):
    response = client.get('/health')
    assert response.status_code in (200, 503)
    json_data = response.get_json()
    assert 'status' in json_data
    assert 'service' in json_data

def test_health_readiness(client):
    response = client.get('/health/readiness')
    assert response.status_code in (200, 503)
    json_data = response.get_json()
    assert 'status' in json_data
    assert 'storage' in json_data
    assert 'redis' in json_data
    assert 'database' in json_data


def test_celery_component_reports_degraded_when_inspection_fails(monkeypatch):
    import celery
    from app.api import health as health_api

    class BrokenControl:
        def inspect(self, **_kwargs):
            raise RuntimeError("broker detail that must not escape")

    monkeypatch.setattr(
        celery,
        "current_app",
        SimpleNamespace(
            conf=SimpleNamespace(broker_url="memory://"),
            control=BrokenControl(),
        ),
    )

    assert health_api.check_celery() is False


# --------------------------------------------------------------------------- #
# Deadline-bounded probes: /health is the container HEALTHCHECK target
# (Dockerfile urllib timeout=3s), so a hanging dependency must degrade the
# probe instead of stalling the endpoint at the OS-level TCP timeout.
# --------------------------------------------------------------------------- #


def test_check_database_bounded_when_engine_hangs(monkeypatch):
    """A DB engine that never answers must degrade within the deadline."""
    from app.api import health as health_api

    class HangingConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args, **_kwargs):
            time.sleep(60)
            return object()

    class HangingEngine:
        def connect(self):
            return HangingConnection()

    import app.db as db_module

    monkeypatch.setattr(db_module, "get_engine", lambda: HangingEngine())

    start = time.monotonic()
    assert health_api.check_database() is False
    assert time.monotonic() - start < 4.0


def test_check_redis_bounded_when_broker_blackholes(monkeypatch, app):
    """A broker that accepts packets but never answers must not hang the
    probe at the OS-level TCP connect timeout (the original code took ~4s;
    a black-holed route would take far longer)."""
    from app.api import health as health_api

    class HangingRedis:
        def ping(self):
            time.sleep(60)
            return True

        def close(self):
            pass

    captured_kwargs = {}

    def fake_from_url(url, **kwargs):
        captured_kwargs.update(kwargs)
        return HangingRedis()

    monkeypatch.setattr(health_api.Redis, "from_url", fake_from_url)

    with app.app_context():
        start = time.monotonic()
        assert health_api.check_redis() is False
        elapsed = time.monotonic() - start

    assert elapsed < 4.0
    # The Redis client must bound both its connect and its command phases.
    assert captured_kwargs.get("socket_connect_timeout") == health_api.PROBE_DEADLINE_SECONDS
    assert captured_kwargs.get("socket_timeout") == health_api.PROBE_DEADLINE_SECONDS


def test_check_celery_bounded_when_broker_hangs(monkeypatch):
    """Celery's broker connection/retry must never stall the liveness probe."""
    from app.api import health as health_api

    class HangingInspector:
        def stats(self):
            time.sleep(60)
            return {}

    class HangingControl:
        def inspect(self, **_kwargs):
            return HangingInspector()

    import celery

    monkeypatch.setattr(
        celery,
        "current_app",
        SimpleNamespace(
            conf=SimpleNamespace(broker_url="memory://"),
            control=HangingControl(),
        ),
    )

    start = time.monotonic()
    assert health_api.check_celery() is False
    assert time.monotonic() - start < 4.0


def test_check_celery_fast_fails_before_inspect_when_broker_dead(monkeypatch):
    """A dead broker must be rejected at the TCP layer so kombu's retry loop
    never keeps an abandoned probe thread alive (the leak the deadline alone
    would leave behind).

    Redis probes without socket_connect_timeout took ~4s and Celery's
    kombu retry loop took ~6s on a dead broker before the fix.
    """
    import socket
    from app.api import health as health_api

    class MustNotInspect:
        def inspect(self, **_kwargs):
            raise AssertionError("inspect must not run when the broker is dead")

    def refused(*_args, **_kwargs):
        raise ConnectionRefusedError("broker dead")

    monkeypatch.setattr(socket, "create_connection", refused)

    import celery

    monkeypatch.setattr(
        celery,
        "current_app",
        SimpleNamespace(
            conf=SimpleNamespace(broker_url="redis://localhost:6379/0"),
            control=MustNotInspect(),
        ),
    )

    start = time.monotonic()
    assert health_api.check_celery() is False
    assert time.monotonic() - start < 2.0


def test_health_endpoint_answers_inside_healthcheck_window(client, monkeypatch):
    """With every dependency hanging for 60s, /health must still answer well
    under the Docker HEALTHCHECK urllib timeout of 3s (the probe thread
    budget keeps the endpoint bounded while threads run to completion in
    the background as daemons)."""
    monkeypatch.setattr("app.api.health.check_database", lambda: time.sleep(60) or True)
    monkeypatch.setattr("app.api.health.check_redis", lambda: time.sleep(60) or True)
    monkeypatch.setattr("app.api.health.check_celery", lambda: time.sleep(60) or True)

    start = time.monotonic()
    response = client.get("/health")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["components"]["database"] == "degraded"
    assert payload["components"]["redis"] == "degraded"
    assert payload["components"]["celery"] == "degraded"
    assert elapsed < 3.5, f"/health took {elapsed:.2f}s under hanging probes"


def test_health_endpoint_still_reports_ok_with_patched_healthy_checks(client, monkeypatch):
    """The concurrent probe layer must not change the patch seam: healthy
    checks still yield status 'ok' (also pinned by test_app_hardening)."""
    monkeypatch.setattr("app.api.health.check_database", lambda: True)
    monkeypatch.setattr("app.api.health.check_redis", lambda: True)
    monkeypatch.setattr("app.api.health.check_celery", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["components"]["redis"] == "ok"
    assert response.get_json()["components"]["celery"] == "ok"