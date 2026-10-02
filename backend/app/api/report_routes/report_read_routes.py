"""Read-only report retrieval: single report, by-simulation, list, sections.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import os

import traceback

from flask import jsonify, request

from ...services.claim_boundary import synthetic_output_disclosure

from ...services.report_agent import (
    ReportManager, ReportStatus,
)

from ...utils.response import truth_metadata

from ...utils.safe_path import SafePathError
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



def get_report(report_id: str):
    """
    Get report details
    
    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "simulation_id": "sim_xxxx",
                "status": "completed",
                "outline": {...},
                "markdown_content": "...",
                "created_at": "...",
                "completed_at": "..."
            }
        }
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": report.to_dict(),
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def get_report_by_simulation(simulation_id: str):
    """
    Get report by simulation ID
    
    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                ...
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": f"No report found for this simulation: {simulation_id}",
                "has_report": False
            }), 404
        
        return jsonify({
            "success": True,
            "data": report.to_dict(),
            "has_report": True,
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })
        
    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def list_reports():
    """
    List all reports
    
    Query parameters:
        simulation_id: Filter by simulation ID (optional)
        limit: Return quantity limit (default 50)
    
    Returns:
        {
            "success": true,
            "data": [...],
            "count": 10
        }
    """
    try:
        simulation_id = request.args.get('simulation_id')
        limit = request.args.get('limit', 50, type=int)
        
        reports = ReportManager.list_reports(
            simulation_id=simulation_id,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in reports],
            "count": len(reports),
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })
        
    except Exception as e:
        logger.error(f"Failed to list reports: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def get_report_sections(report_id: str):
    """
    Get generated section list (sectioned output)
    
    Frontend can poll this interface to get generated section content without waiting for the full report to complete
    
    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "sections": [
                    {
                        "filename": "section_01.md",
                        "section_index": 1,
                        "content": "## Executive Summary\\n\\n..."
                    },
                    ...
                ],
                "total_sections": 3,
                "is_complete": false
            }
        }
    """
    try:
        sections = ReportManager.get_generated_sections(report_id)
        
        # Get report status
        report = ReportManager.get_report(report_id)
        is_complete = report is not None and report.status == ReportStatus.COMPLETED
        
        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "sections": sections,
                "total_sections": len(sections),
                "is_complete": is_complete
            },
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get section list: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def get_single_section(report_id: str, section_index: int):
    """
    Get single section content
    
    Returns:
        {
            "success": true,
            "data": {
                "filename": "section_01.md",
                "content": "## Executive Summary\\n\\n..."
            }
        }
    """
    try:
        section_path = ReportManager._get_section_path(report_id, section_index)
        
        if not os.path.exists(section_path):
            return jsonify({
                "success": False,
                "error": f"Section does not exist: section_{section_index:02d}.md"
            }), 404
        
        with open(section_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            "success": True,
            "data": {
                "filename": f"section_{section_index:02d}.md",
                "section_index": section_index,
                "content": content
            },
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get section content: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Report Status Check Interfaces ==============

ROUTES = (
    ("/<report_id>", ['GET'], "get_report"),
    ("/by-simulation/<simulation_id>", ['GET'], "get_report_by_simulation"),
    ("/list", ['GET'], "list_reports"),
    ("/<report_id>/sections", ['GET'], "get_report_sections"),
    ("/<report_id>/section/<int:section_index>", ['GET'], "get_single_section"),
)
