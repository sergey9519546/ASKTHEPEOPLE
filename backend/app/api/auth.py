"""Authentication support routes."""

from __future__ import annotations

from flask import current_app, jsonify, request

from . import auth_bp, limiter
from ..services.access_control import AccessTicketError, issue_ws_ticket


@auth_bp.route("/ws-ticket", methods=["POST"])
@limiter.limit("30 per minute")
def create_ws_ticket():
    """Exchange an authenticated HTTP request for a short-lived WS ticket."""
    data = request.get_json(silent=True) or {}
    scope = str(data.get("scope", "")).strip()
    resource_id = str(data.get("resource_id", "")).strip()

    try:
        ticket, expires_at = issue_ws_ticket(
            str(current_app.config["SECRET_KEY"]),
            scope,
            resource_id,
        )
    except AccessTicketError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    return jsonify(
        {
            "success": True,
            "ticket": ticket,
            "expires_at": expires_at,
            "expires_in": 60,
        }
    )
