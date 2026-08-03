from flask import Blueprint, jsonify, request
import os
from . import simulation_bp
from app.services.simulation_fork_service import fork_simulation
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
        
    try:
        new_id = fork_simulation(simulation_id, int(target_turn))
        return jsonify({
            "success": True, 
            "data": {
                "new_simulation_id": new_id,
                "message": f"Successfully forked simulation to {new_id} at round {target_turn}"
            }
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("Failed to fork simulation")
        return jsonify({"success": False, "error": "Internal server error"}), 500
