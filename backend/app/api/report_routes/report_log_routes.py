"""Agent and console log retrieval, including the streaming variants.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import traceback

from flask import jsonify, request

from ...services.claim_boundary import synthetic_output_disclosure

from ...services.report_agent import ReportManager

from ...utils.safe_path import SafePathError
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



def get_agent_log(report_id: str):
    """
    Get detailed execution logs of Report Agent
    
    Get every action in the report generation process in real-time, including:
    - Report start, planning start/completion
    - Each section start, tool call, LLM response, completion
    - Report completion or failure
    
    Query parameters:
        from_line: Read from which line (optional, default 0, for incremental retrieval)
    
    Returns:
        {
            "success": true,
            "data": {
                "logs": [
                    {
                        "timestamp": "2025-12-13T...",
                        "elapsed_seconds": 12.5,
                        "report_id": "report_xxxx",
                        "action": "tool_call",
                        "stage": "generating",
                        "section_title": "Executive Summary",
                        "section_index": 1,
                        "details": {
                            "tool_name": "insight_forge",
                            "parameters": {...},
                            ...
                        }
                    },
                    ...
                ],
                "total_lines": 25,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)
        
        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)
        
        return jsonify({
            "success": True,
            "data": log_data,
            "disclosure": synthetic_output_disclosure(),
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def stream_agent_log(report_id: str):
    """
    Get complete Agent logs (retrieve all at once)
    
    Returns:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 25
            }
        }
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            },
            "disclosure": synthetic_output_disclosure(),
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Console Log Interfaces ==============


def get_console_log(report_id: str):
    """
    Get console output logs of Report Agent
    
    Get console output (INFO, WARNING, etc.) during report generation in real-time.
    This is different from the structured JSON logs returned by the agent-log interface,
    it's plain text console-style logs.
    
    Query parameters:
        from_line: Read from which line (optional, default 0, for incremental retrieval)
    
    Returns:
        {
            "success": true,
            "data": {
                "logs": [
                    "[19:46:14] INFO: Search completed: found 15 relevant facts",
                    "[19:46:14] INFO: Graph search: graph_id=xxx, query=...",
                    ...
                ],
                "total_lines": 100,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)
        
        log_data = ReportManager.get_console_log(report_id, from_line=from_line)

        return jsonify({
            "success": True,
            "data": log_data,
            "disclosure": synthetic_output_disclosure(),
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def stream_console_log(report_id: str):
    """
    Get complete console logs (retrieve all at once)
    
    Returns:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 100
            }
        }
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)

        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            },
            "disclosure": synthetic_output_disclosure(),
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Tool Call Interfaces (for debugging) ==============

ROUTES = (
    ("/<report_id>/agent-log", ['GET'], "get_agent_log"),
    ("/<report_id>/agent-log/stream", ['GET'], "stream_agent_log"),
    ("/<report_id>/console-log", ['GET'], "get_console_log"),
    ("/<report_id>/console-log/stream", ['GET'], "stream_console_log"),
)
