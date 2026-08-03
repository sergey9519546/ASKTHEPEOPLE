import pytest
from app import create_app

@pytest.fixture
def app():
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
