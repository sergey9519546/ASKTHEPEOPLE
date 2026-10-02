"""Interactive chat against a generated report.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import traceback

from flask import jsonify, request

from ...config import Config

from ...models.project import ProjectManager

from ...services.claim_boundary import synthetic_output_disclosure

from ...services.report_agent import ReportAgent

from ...services.simulation_manager import SimulationManager

from ...utils.input_policy import (
    CHAT_MESSAGE_MAX, InputPolicyError, bounded_text, validate_chat_history,
)

from .. import limiter
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def chat_with_report_agent():
    """
    Chat with Report Agent
    
    Report Agent can autonomously call retrieval tools during chat to answer questions
    
    Request (JSON):
        {
            "simulation_id": "sim_xxxx",        // Required, simulation ID
            "message": "Please explain the synthetic scenario pattern", // Required, user message
            "chat_history": [                   // Optional, chat history
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "response": "Agent reply...",
                "tool_calls": [List of called tools],
                "retrieval_queries": [graph or run-record search queries]
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        try:
            message = bounded_text(
                data.get('message'),
                field="message",
                max_length=CHAT_MESSAGE_MAX,
                required=True,
            )
            chat_history = validate_chat_history(data.get('chat_history', []))
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400
        
        # Get simulation and project info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {state.project_id}"
            }), 404
        
        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "Missing graph ID"
            }), 400
        
        simulation_requirement = project.simulation_requirement or ""
        
        # Create Agent and start chat
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement
        )
        
        result = agent.chat(message=message, chat_history=chat_history)
        
        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Report Progress and Section Interfaces ==============

ROUTES = (
    ("/chat", ['POST'], "chat_with_report_agent"),
)
