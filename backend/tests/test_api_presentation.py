"""Tests for the presentation seam: envelope shape and truth-contract attachment."""

import json

import pytest

from app import create_app
from app.api.presentation import (
    error_response,
    present,
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
