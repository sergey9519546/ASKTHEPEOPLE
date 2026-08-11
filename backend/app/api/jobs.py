"""
Canonical Job Status API
Provides unified job-status endpoint for all background tasks.
This is the endpoint referenced in HTTP 202 Location headers.
"""

from flask import Blueprint, jsonify
from ..models.task import TaskManager

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@jobs_bp.route("/<task_id>", methods=["GET"])
def get_job_status(task_id: str):
    """
    Get job status by task ID.
    
    This is the canonical job-status endpoint referenced in HTTP 202 responses.
    Works for any background job type (graph build, preparation, execution, report).
    
    Args:
        task_id: Task identifier returned from a 202 response
        
    Returns:
        200: Task exists, returns status
        404: Task not found
    """
    task_manager = TaskManager()  # singleton via __new__
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": "task_not_found",
            "message": f"No task with ID {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "job": task.to_public_dict()
    }), 200
