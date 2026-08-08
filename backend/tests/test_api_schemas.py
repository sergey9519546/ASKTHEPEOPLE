"""
Tests for Pydantic v2 schemas and request validation decorator.
"""

from flask import Flask, jsonify, request
from app.api.schemas import (
    CreateSimulationRequest,
    PrepareSimulationRequest,
    FetchUrlsRequest,
    validate_schema,
)


def test_create_simulation_schema_valid():
    payload = {"project_id": "proj_123", "enable_twitter": True}
    req = CreateSimulationRequest.model_validate(payload)
    assert req.project_id == "proj_123"
    assert req.enable_twitter is True
    assert req.enable_reddit is True


def test_prepare_simulation_schema_bounds():
    valid = {"simulation_id": "sim_123", "archetype_count": 50, "profile_workers": 4}
    req = PrepareSimulationRequest.model_validate(valid)
    assert req.archetype_count == 50

    try:
        PrepareSimulationRequest.model_validate({"simulation_id": "sim_123", "archetype_count": 5000})
        assert False, "Should fail archetype_count bounds"
    except Exception:
        pass


def test_validate_schema_decorator():
    app = Flask(__name__)

    @app.route("/test", methods=["POST"])
    @validate_schema(FetchUrlsRequest)
    def test_route():
        data = request.validated_data
        return jsonify({"success": True, "count": len(data.urls)})

    client = app.test_client()

    # Invalid payload (empty urls list)
    resp = client.post("/test", json={"urls": []})
    assert resp.status_code == 422
    assert resp.json["type"] == "validation_error"

    # Valid payload
    resp = client.post("/test", json={"urls": ["https://example.com"]})
    assert resp.status_code == 200
    assert resp.json["count"] == 1
