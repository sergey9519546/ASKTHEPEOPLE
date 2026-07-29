"""
WebSocket endpoints.

Routes (registered on the Flask app, NOT on a blueprint):
  ws://host/ws/simulation/<simulation_id>
  ws://host/ws/report/<report_id>

Both endpoints push JSON frames on a fixed poll interval and close
cleanly when the job reaches a terminal state or the client disconnects.

Message shapes
--------------
Simulation frame:
  {
    "type": "state",
    "simulation_id": "sim_xxx",
    "runner_status": "running",
    "current_round": 4,
    "total_rounds": 10,
    "progress_percent": 40.0,
    "twitter_actions_count": 120,
    "reddit_actions_count": 98,
    "follower_twitter_count": 30,
    "follower_reddit_count": 25,
    "twitter_running": true,
    "reddit_running": false,
    "recent_actions": [...],   # last 10 actions
    "error": null
  }

Error frame (sent once, then connection closes):
  {"type": "error", "code": "not_found", "message": "..."}

Done frame (sent once after terminal state, then connection closes):
  {"type": "done", "runner_status": "completed"}

Report frame:
  {
    "type": "progress",
    "report_id": "report_xxx",
    "status": "processing",
    "progress": 42,
    "message": "Generating section 2/4...",
    "current_stage": "generating",
    "sections_done": 2,
    "sections_total": 4
  }
"""

from __future__ import annotations

import json
import hmac
import time
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from flask import current_app, request

from ..extensions import sock
from ..services.access_control import AccessTicketError, verify_ws_ticket
from ..services.claim_boundary import (
    synthetic_activity_disclosure,
    synthetic_output_disclosure,
)
from ..utils.logger import get_logger

logger = get_logger("askthepeople.ws")

# ── tunables ──────────────────────────────────────────────────────────────────
_SIM_POLL_INTERVAL = 2.0    # seconds between simulation state frames
_REPORT_POLL_INTERVAL = 1.0  # seconds between report progress frames
_MAX_RECENT_ACTIONS = 10     # actions included per simulation frame

_SIM_TERMINAL = {"completed", "failed", "stopped", "interrupted"}
_REPORT_TERMINAL = {"completed", "failed"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _send(ws: Any, payload: Dict) -> bool:
    """Send JSON frame; return False if the connection is closed."""
    try:
        ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


def _normalize_origin(value: str) -> str | None:
    """Normalize a browser Origin header for exact allowlist comparison."""
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return None
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", "", "", ""))


def _ws_access_error(scope: str, resource_id: str) -> str | None:
    """Return a policy error code, or None when the request is authorized."""
    allowed_origins = current_app.config.get("CORS_ALLOWED_ORIGINS")
    if allowed_origins is None:
        configured = current_app.config.get("CORS_ORIGINS", "*")
        allowed_origins = (
            "*" if configured == "*"
            else [origin.strip() for origin in str(configured).split(",") if origin.strip()]
        )

    origin = _normalize_origin(request.headers.get("Origin", ""))
    if allowed_origins != "*":
        normalized_allowed = {
            normalized
            for item in allowed_origins
            if (normalized := _normalize_origin(str(item))) is not None
        }
        if origin is None or origin not in normalized_allowed:
            return "origin_not_allowed"

    expected = current_app.config.get("APP_TOKEN")
    if not expected and not current_app.config.get("DEBUG", False):
        return "authentication_not_configured"
    if expected:
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
        if token and hmac.compare_digest(str(token), str(expected)):
            return None

        ticket = request.args.get("ticket", "")
        try:
            verify_ws_ticket(
                ticket,
                str(current_app.config["SECRET_KEY"]),
                scope,
                resource_id,
            )
        except AccessTicketError:
            return "unauthorized"
    return None


def _reject_ws(ws: Any, error_code: str) -> None:
    _send(ws, {
        "type": "error",
        "code": error_code,
        "message": "WebSocket connection rejected by server policy.",
    })
    try:
        ws.close()
    except Exception:
        pass


def _simulation_state_frame(state: Any) -> Dict:
    """Build one disclosed simulation-state frame."""
    frame = state.to_dict()
    frame["type"] = "state"
    frame["recent_actions"] = [
        {
            **action.to_dict(),
            **synthetic_activity_disclosure(),
        }
        for action in state.recent_actions[:_MAX_RECENT_ACTIONS]
    ]
    frame["disclosure"] = synthetic_output_disclosure()
    return frame


def _report_progress_frame(report_id: str, progress: Dict) -> Dict:
    """Build one disclosed report-progress frame."""
    return {
        "type": "progress",
        "report_id": report_id,
        "status": progress.get("status", "unknown"),
        "progress": progress.get("progress", 0),
        "message": progress.get("message", ""),
        "current_stage": progress.get("current_stage", ""),
        "sections_done": progress.get("sections_done", 0),
        "sections_total": progress.get("sections_total", 0),
        "disclosure": synthetic_output_disclosure(),
    }


# ── simulation WebSocket ──────────────────────────────────────────────────────

@sock.route("/ws/simulation/<simulation_id>")
def simulation_ws(ws, simulation_id: str):
    """
    Stream SimulationRunState updates every 2 s until the simulation
    reaches a terminal state or the client disconnects.
    """
    from ..services.simulation_runner import SimulationRunner

    access_error = _ws_access_error("simulation", simulation_id)
    if access_error:
        _reject_ws(ws, access_error)
        return

    logger.info(f"WS simulation open: {simulation_id}")

    try:
        while ws.connected:
            state = SimulationRunner.get_run_state(simulation_id)

            if state is None:
                _send(ws, {
                    "type": "error",
                    "code": "not_found",
                    "message": f"Simulation {simulation_id!r} has no run state yet. "
                               "Start it via POST /api/simulation/start first.",
                })
                break

            base = _simulation_state_frame(state)

            if not _send(ws, base):
                break  # client gone

            if base.get("runner_status") in _SIM_TERMINAL:
                _send(ws, {
                    "type": "done",
                    "runner_status": base["runner_status"],
                    "disclosure": synthetic_output_disclosure(),
                })
                break

            time.sleep(_SIM_POLL_INTERVAL)

    except Exception as exc:
        logger.debug(f"WS simulation {simulation_id} closed: {exc}")

    logger.info(f"WS simulation closed: {simulation_id}")


# ── report WebSocket ──────────────────────────────────────────────────────────

@sock.route("/ws/report/<report_id>")
def report_ws(ws, report_id: str):
    """
    Stream report generation progress every 1 s until the report
    completes or the client disconnects.
    """
    from ..services.report_agent import ReportManager

    access_error = _ws_access_error("report", report_id)
    if access_error:
        _reject_ws(ws, access_error)
        return

    logger.info(f"WS report open: {report_id}")

    try:
        while ws.connected:
            progress = ReportManager.get_progress(report_id)

            if progress is None:
                _send(ws, {
                    "type": "error",
                    "code": "not_found",
                    "message": f"No progress found for report {report_id!r}. "
                               "Generate it via POST /api/report/generate first.",
                })
                break

            frame = _report_progress_frame(report_id, progress)

            if not _send(ws, frame):
                break  # client gone

            if frame["status"] in _REPORT_TERMINAL:
                _send(ws, {
                    "type": "done",
                    "status": frame["status"],
                    "disclosure": synthetic_output_disclosure(),
                })
                break

            time.sleep(_REPORT_POLL_INTERVAL)

    except Exception as exc:
        logger.debug(f"WS report {report_id} closed: {exc}")

    logger.info(f"WS report closed: {report_id}")
