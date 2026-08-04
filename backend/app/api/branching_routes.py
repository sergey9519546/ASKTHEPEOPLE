from flask import Blueprint, jsonify, request
import os
from . import simulation_bp
from app.services.simulation_fork_service import ForkError, fork_simulation
from app.utils.safe_path import SafePathError
import logging

logger = logging.getLogger(__name__)

@simulation_bp.route("/<simulation_id>/fork", methods=["POST"])
def api_fork_simulation(simulation_id):
    """
    Forks an existing simulation at a specific turn.
    Body:
    {
      "target_turn": int
    }
    """
    data = request.json or {}
    target_turn = data.get("target_turn")
    if target_turn is None:
        return jsonify({"success": False, "error": "target_turn is required"}), 400

    # A non-numeric target_turn is a malformed request, not a missing
    # simulation; without this it fell through to the ValueError handler below
    # and was reported as 404.
    try:
        target_turn = int(target_turn)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "target_turn must be an integer"}), 400

    try:
        new_id = fork_simulation(simulation_id, target_turn)
        return jsonify({
            "success": True, 
            "data": {
                "new_simulation_id": new_id,
                "message": f"Successfully forked simulation to {new_id} at round {target_turn}"
            }
        }), 201
    except SafePathError:
        # SafePathError subclasses ValueError, so it must be caught first or a
        # malformed id reports as "not found" instead of "invalid".
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except ForkError:
        logger.exception("Fork failed after copying the simulation")
        return jsonify({"success": False, "error": "fork_failed"}), 500
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception:
        logger.exception("Failed to fork simulation")
        return jsonify({"success": False, "error": "Internal server error"}), 500
