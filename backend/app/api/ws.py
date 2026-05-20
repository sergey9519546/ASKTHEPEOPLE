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
import time
from typing import Any, Dict

from ..extensions import sock
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


# ── simulation WebSocket ──────────────────────────────────────────────────────

@sock.route("/ws/simulation/<simulation_id>")
def simulation_ws(ws, simulation_id: str):
    """
    Stream SimulationRunState updates every 2 s until the simulation
    reaches a terminal state or the client disconnects.
    """
    from ..services.simulation_runner import SimulationRunner

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

            base = state.to_dict()
            base["type"] = "state"
            base["recent_actions"] = [
                a.to_dict() for a in state.recent_actions[:_MAX_RECENT_ACTIONS]
            ]

            if not _send(ws, base):
                break  # client gone

            if base.get("runner_status") in _SIM_TERMINAL:
                _send(ws, {"type": "done", "runner_status": base["runner_status"]})
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

            frame: Dict = {
                "type": "progress",
                "report_id": report_id,
                "status": progress.get("status", "unknown"),
                "progress": progress.get("progress", 0),
                "message": progress.get("message", ""),
                "current_stage": progress.get("current_stage", ""),
                "sections_done": progress.get("sections_done", 0),
                "sections_total": progress.get("sections_total", 0),
            }

            if not _send(ws, frame):
                break  # client gone

            if frame["status"] in _REPORT_TERMINAL:
                _send(ws, {"type": "done", "status": frame["status"]})
                break

            time.sleep(_REPORT_POLL_INTERVAL)

    except Exception as exc:
        logger.debug(f"WS report {report_id} closed: {exc}")

    logger.info(f"WS report closed: {report_id}")
