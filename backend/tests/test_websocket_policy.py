import json
from types import SimpleNamespace

from app import create_app
from app.api import ws as ws_api
from app.api.ws import _ws_access_error
from app.config import Config
from app.services.access_control import issue_ws_ticket
from app.services.claim_boundary import synthetic_output_disclosure
from app.services import report_agent, simulation_runner


def _app():
    previous_token = Config.APP_TOKEN
    Config.APP_TOKEN = "test-app-token-32-characters-long"
    try:
        app = create_app()
    finally:
        Config.APP_TOKEN = previous_token
    app.config.update({
        "TESTING": True,
        "APP_TOKEN": "secret",
        "CORS_ALLOWED_ORIGINS": ["https://app.example.test"],
    })
    return app


def test_websocket_requires_allowed_origin_and_token():
    app = _app()
    ticket, _ = issue_ws_ticket(
        app.config["SECRET_KEY"],
        "simulation",
        "sim_123",
    )
    with app.test_request_context(
        f"/ws/simulation/sim_123?ticket={ticket}",
        headers={"Origin": "https://app.example.test"},
    ):
        assert _ws_access_error("simulation", "sim_123") is None


def test_websocket_rejects_wrong_origin_even_with_token():
    app = _app()
    with app.test_request_context(
        "/ws/simulation/sim_123",
        headers={
            "Origin": "https://evil.example.test",
            "Authorization": "Bearer secret",
        },
    ):
        assert _ws_access_error("simulation", "sim_123") == "origin_not_allowed"


def test_websocket_rejects_missing_or_wrong_token():
    app = _app()
    with app.test_request_context(
        "/ws/report/report_123?token=secret",
        headers={"Origin": "https://app.example.test"},
    ):
        assert _ws_access_error("report", "report_123") == "unauthorized"


def test_production_websocket_fails_closed_without_app_token():
    app = _app()
    app.config.update({"DEBUG": False, "APP_TOKEN": None})
    with app.test_request_context(
        "/ws/report/report_123",
        headers={"Origin": "https://app.example.test"},
    ):
        assert _ws_access_error("report", "report_123") == "authentication_not_configured"


def test_ws_ticket_endpoint_requires_bearer_and_returns_short_lived_ticket():
    app = _app()
    client = app.test_client()

    unauthorized = client.post(
        "/api/auth/ws-ticket",
        json={"scope": "simulation", "resource_id": "sim_123"},
    )
    assert unauthorized.status_code == 401

    response = client.post(
        "/api/auth/ws-ticket",
        json={"scope": "simulation", "resource_id": "sim_123"},
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["expires_in"] == 60
    assert payload["ticket"]


class _FakeWebSocket:
    def __init__(self):
        self.connected = True
        self.frames = []

    def send(self, value):
        self.frames.append(json.loads(value))

    def close(self):
        self.connected = False


def test_simulation_websocket_frames_keep_synthetic_disclosure(monkeypatch):
    action = SimpleNamespace(to_dict=lambda: {"action_type": "CREATE_POST"})
    state = SimpleNamespace(
        recent_actions=[action],
        to_dict=lambda: {"runner_status": "completed"},
    )
    frame = ws_api._simulation_state_frame(state)

    assert frame["disclosure"] == synthetic_output_disclosure()
    assert frame["recent_actions"][0]["record_origin"] == (
        "synthetic_simulation"
    )
    assert frame["recent_actions"][0]["observed_human_behavior"] is False


def test_report_websocket_progress_and_done_frames_disclose(monkeypatch):
    frame = ws_api._report_progress_frame(
        "report_123",
        {"status": "completed", "progress": 100},
    )

    assert frame["disclosure"] == synthetic_output_disclosure()
