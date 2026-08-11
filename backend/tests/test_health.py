import pytest
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
        SimpleNamespace(control=BrokenControl()),
    )

    assert health_api.check_celery() is False
