"""Tests for the presentation seam: envelope shape and truth-contract attachment."""

import json

import pytest

from app import create_app
from app.api.presentation import (
    error_response,
    present,
    present_raw,
    with_activity_truth,
    with_config_truth,
    with_profile_truth,
)


@pytest.fixture
def app():
    return create_app()


class TestPresent:
    def test_success_envelope_with_data(self, app):
        with app.test_request_context():
            resp = present({"x": 1})
            assert resp.status_code == 200
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": True, "data": {"x": 1}}

    def test_success_envelope_without_data(self, app):
        with app.test_request_context():
            resp = present()
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": True}

    def test_success_with_status_and_extra(self, app):
        with app.test_request_context():
            resp = present({"id": 5}, status=202, extra={"task_id": "t1"})
            assert resp.status_code == 202
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": True, "data": {"id": 5}, "task_id": "t1"}


class TestPresentRaw:
    def test_raw_payload_keeps_caller_owned_shape(self, app):
        with app.test_request_context():
            resp = present_raw(
                {
                    "success": True,
                    "data": {"result": "ok"},
                    "disclosure": {"status": "synthetic"},
                }
            )
            assert resp.status_code == 200
            body = json.loads(resp.get_data(as_text=True))
            assert body == {
                "success": True,
                "data": {"result": "ok"},
                "disclosure": {"status": "synthetic"},
            }

    def test_raw_preserves_explicit_false_flag(self, app):
        with app.test_request_context():
            resp = present_raw({"success": False, "error": "timeout"})
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": False, "error": "timeout"}

    def test_raw_defaults_missing_success_to_false(self, app):
        with app.test_request_context():
            resp = present_raw({"error": "simulation_not_complete", "status": "running"})
            body = json.loads(resp.get_data(as_text=True))
            assert body == {
                "success": False,
                "error": "simulation_not_complete",
                "status": "running",
            }

    def test_raw_non_dict_payload_normalizes_deterministically(self, app):
        with app.test_request_context():
            for garbage in (None, "text", 42, ["list"], ("t", 1)):
                resp = present_raw(garbage)
                assert resp.status_code == 200
                body = json.loads(resp.get_data(as_text=True))
                assert body == {"success": False}

    def test_raw_non_dict_success_true_is_not_invented(self, app):
        """A payload that cannot speak must never be upgraded to success."""
        with app.test_request_context():
            resp = present_raw(None)
            body = json.loads(resp.get_data(as_text=True))
            assert body["success"] is False

    def test_raw_honors_status(self, app):
        with app.test_request_context():
            resp = present_raw({"success": True}, status=202)
            assert resp.status_code == 202
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": True}

    def test_raw_extra_keys_in_payload_are_preserved_not_dropped(self, app):
        with app.test_request_context():
            resp = present_raw(
                {"success": True, "data": {}, "task_id": "t1", "custom": [1, 2]}
            )
            body = json.loads(resp.get_data(as_text=True))
            assert body == {
                "success": True,
                "data": {},
                "task_id": "t1",
                "custom": [1, 2],
            }


class TestErrorResponse:
    def test_error_shape(self, app):
        with app.test_request_context():
            resp, status = error_response("bad input", status=400)
            assert status == 400
            body = json.loads(resp.get_data(as_text=True))
            assert body == {"success": False, "error": "bad input"}

    def test_error_with_extra(self, app):
        with app.test_request_context():
            resp, status = error_response(
                "not found", status=404, task_id="t9"
            )
            assert status == 404
            body = json.loads(resp.get_data(as_text=True))
            assert body["error"] == "not found"
            assert body["task_id"] == "t9"


class TestTruthAttach:
    def test_profile_truth_attaches(self):
        records = [{"name": "Alice"}]
        out = with_profile_truth(records)
        assert len(out) == 1
        assert out[0]["name"] == "Alice"
        assert out[0]["human_respondents"] == 0
        assert out[0]["profile_origin"] == "fictional_model_generated"

    def test_profile_truth_non_dict_passthrough(self):
        records = ["not a dict", {"name": "Bob"}]
        out = with_profile_truth(records)
        assert out[0] == "not a dict"
        assert out[1]["profile_origin"] == "fictional_model_generated"

    def test_profile_truth_non_list_returns_empty(self):
        assert with_profile_truth("garbage") == []
        assert with_profile_truth(None) == []

    def test_activity_truth_attaches(self):
        out = with_activity_truth([{"action": "walk"}])
        assert out[0]["record_origin"] == "synthetic_simulation"
        assert out[0]["human_respondents"] == 0
        assert out[0]["observed_human_behavior"] is False

    def test_config_truth_adds_disclosure(self):
        config = {"rounds": 10}
        out = with_config_truth(config)
        assert out["rounds"] == 10
        assert "truth_status" in out
        assert out["truth_status"]["human_respondents"] == 0
        assert "control_metadata" in out

    def test_config_truth_non_dict_passthrough(self):
        assert with_config_truth("not a dict") == "not a dict"
