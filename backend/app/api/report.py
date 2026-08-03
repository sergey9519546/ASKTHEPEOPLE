"""
Report API Routes
Provides interfaces for simulation report generation, retrieval, chat, etc.
"""

import os
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from flask import request, jsonify, send_file

from . import report_bp, limiter
from ..config import Config
from ..services.report_agent import Report, ReportAgent, ReportManager, ReportStatus
from ..services.report_generation_coordinator import (
    ReportGenerationCancelled,
    report_generation_coordinator,
)
from ..services.report_evidence import load_report_evidence
from ..services.claim_boundary import (
    graph_record_disclosure,
    synthetic_output_disclosure,
)
from ..services.simulation_manager import SimulationManager
from ..services.export_service import PDFGenerator, CSVExporter, ExecutiveExporter
from ..services.zep_tools import ZepToolsService
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils.response import truth_metadata
from ..utils.safe_path import SafePathError
from ..utils.input_policy import (
    CHAT_MESSAGE_MAX,
    GRAPH_QUERY_MAX,
    InputPolicyError,
    bounded_integer,
    bounded_text,
    validate_chat_history,
)

logger = get_logger('askthepeople.api.report')


def _get_status_request_data():
    if request.method == 'GET':
        return {
            "task_id": request.args.get('task_id'),
            "simulation_id": request.args.get('simulation_id'),
            "report_id": request.args.get('report_id'),
        }
    data = request.get_json(silent=True) or {}
    return {
        "task_id": data.get('task_id'),
        "simulation_id": data.get('simulation_id'),
        "report_id": data.get('report_id'),
    }


# ============== Report Generation Interfaces ==============

@report_bp.route('/generate', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def generate_report():
    """
    Generate simulation analysis report (asynchronous task)
    
    This is a time-consuming operation; the interface will immediately return a task_id.
    Use GET /api/report/generate/status to check progress.
    
    Request (JSON):
        {
            "simulation_id": "sim_xxxx",    // Required, simulation ID
            "force_regenerate": false        // Optional, force regeneration
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "Report generation task started"
            }
        }
    """
    lease = None
    generation_thread_started = False
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400
        
        force_regenerate = data.get('force_regenerate', False)
        
        # Get simulation info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        # Check if report already exists
        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": "Report already exists",
                        "already_generated": True
                    }
                })
        
        # Get project info
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
                "error": "Missing graph ID, please ensure the graph is built"
            }), 400
        
        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Missing simulation requirement description"
            }), 400
        
        # Pre-generate report_id to return to the frontend immediately
        import uuid
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        lease, active_lease = report_generation_coordinator.acquire(
            simulation_id,
            report_id,
        )
        if lease is None:
            return jsonify({
                "success": False,
                "error": "report_generation_in_progress",
                "data": active_lease.to_public_dict(),
            }), 409

        # Close the completed-result check/acquire race. Force regeneration may
        # bypass reuse, but it never bypasses an active generation lease.
        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                report_generation_coordinator.release(lease)
                lease = None
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": "Report already exists",
                        "already_generated": True,
                    },
                })
        
        # Create asynchronous task
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )
        lease.task_id = task_id
        
        from ..tasks.report_tasks import generate_report_task
        
        generation_thread_started = True
        
        generate_report_task.delay(
            simulation_id=simulation_id,
            report_id=report_id,
            user_prompt=data.get('user_prompt'),
            custom_instructions=data.get('custom_instructions'),
            task_id=task_id
        )
        
        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "task_id": task_id,
                "status": "pending"
            }
        }), 202, {'Location': f'/api/jobs/{task_id}'}
        
    except Exception as e:
        if lease is not None and not generation_thread_started:
            report_generation_coordinator.release(lease)
        logger.error(f"Failed to start report generation task: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/generate/status', methods=['GET', 'POST'])
def get_generate_status():
    """
    Query report generation task progress
    
    Request (JSON):
        {
            "task_id": "task_xxxx",         // Optional, task_id returned by generate
            "simulation_id": "sim_xxxx"     // Optional, simulation ID
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 45,
                "message": "..."
            }
        }
    """
    try:
        data = _get_status_request_data()

        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        report_id = data.get('report_id')

        if report_id:
            report = ReportManager.get_report(report_id)
            progress = ReportManager.get_progress(report_id)
            if report:
                return jsonify({
                    "success": True,
                    "data": {
                        "report_id": report_id,
                        "simulation_id": report.simulation_id,
                        "status": report.status.value,
                        "progress": 100 if report.status == ReportStatus.COMPLETED else (progress or {}).get("progress", 0),
                        "message": (progress or {}).get("message") or ("Report generated" if report.status == ReportStatus.COMPLETED else "Report processing"),
                        "already_completed": report.status == ReportStatus.COMPLETED,
                    }
                })
            if progress:
                return jsonify({
                    "success": True,
                    "data": {
                        "report_id": report_id,
                        "status": progress.get("status", "generating"),
                        "progress": progress.get("progress", 0),
                        "message": progress.get("message", "Report processing"),
                        "already_completed": False,
                    }
                })
        
        # If simulation_id is provided, check for an existing completed report first
        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "Report generated",
                        "already_completed": True
                    }
                })
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": "Please provide task_id, simulation_id, or report_id"
            }), 400
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                "success": False,
                "error": f"Task does not exist: {task_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": task.to_public_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== Report Retrieval Interfaces ==============

@report_bp.route('/<report_id>/related-records', methods=['GET'])
@report_bp.route('/<report_id>/evidence', methods=['GET'])
def get_report_evidence(report_id: str):
    """Get post-hoc keyword-related run records, never citations or evidence."""
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404

        report_dir = ReportManager._get_report_folder(report_id)
        evidence = load_report_evidence(report_dir)

        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "count": len(evidence),
                "selection_method": "post_hoc_keyword_overlap",
                "relationship": "related_example_not_citation",
                "evidence": evidence
            },
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get report evidence: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@report_bp.route('/<report_id>', methods=['GET'])
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


@report_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
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


@report_bp.route('/list', methods=['GET'])
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
        })
        
    except Exception as e:
        logger.error(f"Failed to list reports: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """
    Download report (Markdown format)
    
    Return Markdown file
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404
        
        md_path = ReportManager._get_report_markdown_path(report_id)
        
        if not os.path.exists(md_path):
            # If the MD file doesn't exist, send it from memory using BytesIO
            from io import BytesIO
            md_bytes = report.markdown_content.encode('utf-8')
            return send_file(
                BytesIO(md_bytes),
                as_attachment=True,
                download_name=f"{report_id}.md",
                mimetype='text/markdown'
            )
        
        return send_file(
            md_path,
            as_attachment=True,
            download_name=f"{report_id}.md"
        )

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/export/pdf', methods=['GET'])
def export_report_pdf(report_id: str):
    """
    Export report as PDF (Bauhaus Style)
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        generator = PDFGenerator()
        pdf_bytes = generator.generate(report.to_dict())
        
        from io import BytesIO
        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"ATP_REPORT_{report_id}.pdf",
            mimetype='application/pdf'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export PDF: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/export/csv', methods=['GET'])
def export_report_csv(report_id: str):
    """
    Export simulation graph data as CSV
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        graph_id = report.graph_id
        if not graph_id:
            return jsonify({"success": False, "error": "No graph associated with this report"}), 400
            
        zep = ZepToolsService()
        exporter = CSVExporter(zep)
        csv_data = exporter.export_graph(graph_id)
        csv_bytes = csv_data.encode('utf-8')
        
        from io import BytesIO
        return send_file(
            BytesIO(csv_bytes),
            as_attachment=True,
            download_name=f"ATP_DATA_{report_id}.csv",
            mimetype='text/csv'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export CSV: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/export/executive', methods=['GET'])
def export_report_executive(report_id: str):
    """
    Export report as executive HTML presentation slide deck
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report does not exist: {report_id}"}), 404
            
        metrics_data = None
        if report.simulation_id:
            from ..services.validation_engine import ValidationEngine
            metrics_data = ValidationEngine.load_metrics(report.simulation_id)

        exporter = ExecutiveExporter()
        html_deck = exporter.generate_html_deck(report.to_dict(), metrics_data=metrics_data)
        
        from io import BytesIO
        return send_file(
            BytesIO(html_deck.encode('utf-8')),
            as_attachment=True,
            download_name=f"ATP_EXECUTIVE_PRESENTATION_{report_id}.html",
            mimetype='text/html'
        )
    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to export executive presentation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>', methods=['DELETE'])
def delete_report(report_id: str):
    """Delete report"""
    try:
        success = ReportManager.delete_report(report_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": f"Report does not exist: {report_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "message": f"Report deleted: {report_id}"
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to delete report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Report Agent Chat Interfaces ==============

@report_bp.route('/chat', methods=['POST'])
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

@report_bp.route('/<report_id>/progress', methods=['GET'])
def get_report_progress(report_id: str):
    """
    Get report generation progress (real-time)
    
    Returns:
        {
            "success": true,
            "data": {
                "status": "generating",
                "progress": 45,
                "message": "Generating section: Key Findings",
                "current_section": "Key Findings",
                "completed_sections": ["Executive Summary", "Simulation Background"],
                "updated_at": "2025-12-09T..."
            }
        }
    """
    try:
        progress = ReportManager.get_progress(report_id)
        
        if not progress:
            return jsonify({
                "success": False,
                "error": f"Report does not exist or progress info is unavailable: {report_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": progress
        })

    except SafePathError:
        logger.warning(f"Rejected path-traversal report_id: {report_id!r}")
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to get report progress: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/sections', methods=['GET'])
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


@report_bp.route('/<report_id>/section/<int:section_index>', methods=['GET'])
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

@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """
    Check if simulation has a report and its status
    
    Used by the frontend to unlock fictional generated-response tools.
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "generated_response_tools_unlocked": true,
                "interview_unlocked": true
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        
        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None
        
        # Generated follow-ups are available only after the report is completed.
        generated_response_tools_unlocked = (
            has_report and report.status == ReportStatus.COMPLETED
        )
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "generated_response_tools_unlocked": generated_response_tools_unlocked,
                # Deprecated compatibility alias; remove after legacy clients migrate.
                "interview_unlocked": generated_response_tools_unlocked,
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to check report status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Agent Log Interfaces ==============

@report_bp.route('/<report_id>/agent-log', methods=['GET'])
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


@report_bp.route('/<report_id>/agent-log/stream', methods=['GET'])
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

@report_bp.route('/<report_id>/console-log', methods=['GET'])
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


@report_bp.route('/<report_id>/console-log/stream', methods=['GET'])
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

@report_bp.route('/tools/search', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_MEDIUM)
def search_graph_tool():
    """
    Graph search tool interface (for debugging)
    
    Request (JSON):
        {
            "graph_id": "atp_xxxx",
            "query": "Search query",
            "limit": 10
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        try:
            query = bounded_text(
                data.get('query'),
                field="query",
                max_length=GRAPH_QUERY_MAX,
                required=True,
            )
            limit = bounded_integer(
                data.get('limit', 10),
                field="limit",
                minimum=1,
                maximum=50,
            )
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400
        
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "Please provide graph_id"
            }), 400
        
        tools = ZepToolsService()
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )
        search_payload = result.to_dict()
        search_payload["records"] = [
            graph_record_disclosure(record)
            for record in search_payload.get("facts", [])
        ]
        search_payload["edges"] = [
            {
                **edge,
                **graph_record_disclosure(edge.get("fact", "")),
            }
            for edge in search_payload.get("edges", [])
        ]
        search_payload["facts_deprecated"] = True
        search_payload.update(graph_record_disclosure())

        return jsonify({
            "success": True,
            "data": search_payload,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Graph search failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/tools/statistics', methods=['POST'])
def get_graph_statistics_tool():
    """
    Graph statistics tool interface (for debugging)
    
    Request (JSON):
        {
            "graph_id": "atp_xxxx"
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "Please provide graph_id"
            }), 400
        
        tools = ZepToolsService()
        result = tools.get_graph_statistics(graph_id)
        
        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
