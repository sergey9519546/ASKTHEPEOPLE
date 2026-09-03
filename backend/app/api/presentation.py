"""Presentation seam for the simulation/report API.

This module is the single place where Flask responses are shaped. It owns:

- the success envelope (``jsonify({"success": True, ...})``)
- the error envelope (``jsonify({"success": False, "error": ...}), status``)
- the truth-contract attachment for detached records (profiles, activity,
  config) so a route cannot forget the disclosure — the disclosure is applied
  here, at the response boundary, instead of relying on every handler to call
  ``_with_*_truth`` by hand.

The disclosure factories themselves live in
``services/claim_boundary.py``; this module applies them by payload kind.

Callers get:

    present(data, status=200, extra=None)          -> success response
    error_response(error, status=400, **extra)     -> error response
    with_profile_truth(records)                     -> detached profile records
    with_activity_truth(records)                    -> detached activity records
    with_config_truth(config)                       -> detached config payload

The old underscored names in ``api/simulation.py`` re-import these for
backward compatibility, but routes should import from here.
"""

from flask import jsonify

from ..services.claim_boundary import (
    fictional_profile_disclosure,
    synthetic_activity_disclosure,
    synthetic_config_disclosure,
    synthetic_output_disclosure,
)


def present(data=None, *, status: int = 200, extra: dict | None = None):
    """Build the canonical success response envelope."""
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    resp = jsonify(payload)
    resp.status_code = status
    return resp


def error_response(error: str, *, status: int = 400, **extra):
    """Build the canonical error response envelope."""
    payload = {"success": False, "error": error}
    payload.update(extra)
    return jsonify(payload), status


def with_profile_truth(records):
    """Attach non-human provenance to detached API profile records."""
    disclosed = []
    for record in records if isinstance(records, list) else []:
        if isinstance(record, dict):
            disclosed.append({**record, **fictional_profile_disclosure()})
        else:
            disclosed.append(record)
    return disclosed


def with_activity_truth(records):
    """Attach synthetic-run provenance to detached API activity records."""
    disclosed = []
    for record in records if isinstance(records, list) else []:
        if isinstance(record, dict):
            disclosed.append({**record, **synthetic_activity_disclosure()})
        else:
            disclosed.append(record)
    return disclosed


def with_config_truth(config):
    """Ensure old and new config payloads carry the same truth contract."""
    if not isinstance(config, dict):
        return config
    disclosed = dict(config)
    disclosed["truth_status"] = synthetic_output_disclosure()
    disclosed["control_metadata"] = synthetic_config_disclosure()
    return disclosed
