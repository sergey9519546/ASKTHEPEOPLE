"""Report lifecycle: generation, status queries, progress, and deletion.

Moved out of app/api/report.py by exec-plan T25 (ADR-0011).
"""

import traceback

from flask import jsonify, request

from ...config import Config

from ...models.project import ProjectManager

from ...models.task import (
    TaskIdempotencyConflict, TaskManager,
)

from ...services.claim_boundary import synthetic_output_disclosure

from ...services.report_agent import (
    ReportManager, ReportStatus,
)

from ...services.report_generation_coordinator import report_generation_coordinator

from ...services.simulation_manager import (
    SimulationManager, SimulationStatus,
)

from ...utils.response import (
    mark_public_safe_error, truth_metadata,
)

from ...utils.safe_path import SafePathError

from .. import limiter
from ..schemas import GenerateReportRequest, enforce_schema
from ...utils.logger import get_logger

logger = get_logger('askthepeople.api.report')



def _release_report_lease_safely(lease) -> None:
    if lease is None:
        return
    try:
        report_generation_coordinator.release(lease)
    except Exception:
        logger.error(
            "Report lease release failed: code=report_lease_release_failed",
            extra={"privacy_safe": True},
        )


def _fail_report_task_safely(task_manager, task_id, failure_code) -> None:
    if task_manager is None or task_id is None:
        return
    get_task = getattr(task_manager, "get_task", None)
    if callable(get_task):
        try:
            if get_task(task_id) is None:
                # Admission may have failed before the candidate was written.
                # update_task creates placeholders for legacy progress events,
                # so calling fail_task here would fabricate a task record.
                return
        except Exception:
            logger.error(
                "Report dispatch task lookup failed: "
                "code=report_failure_persistence_failed",
                extra={"privacy_safe": True},
            )
            return
    try:
        task_manager.fail_task(
            task_id,
            failure_code,
            public_error=failure_code,
        )
    except Exception:
        logger.error(
            "Report dispatch failure persistence failed: "
            "code=report_failure_persistence_failed",
            extra={"privacy_safe": True},
        )


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


@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
@enforce_schema(GenerateReportRequest, "report_request_invalid")
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
    task_manager = None
    task_id = None
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "report_request_invalid",
            }), 400
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "report_simulation_id_missing"
            }), 400
        
        force_regenerate = data.get('force_regenerate', False)
        
        # Get simulation info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": "report_simulation_not_found"
            }), 404

        # Task 5 fix: report generation requires a terminal run. A simulation
        # that is still PREPARING, RUNNING, or otherwise non-terminal must not
        # enter report generation — its data is incomplete or in-flight.
        # Terminal states (COMPLETED, STOPPED, INTERRUPTED, FAILED) may
        # generate a report (a stopped/failed run has partial data worth
        # surfacing, with the truth-contract disclosure handling the caveat).
        # Use getattr so a legacy/mock simulation without a status attribute
        # passes through rather than crashing.
        _NON_TERMINAL = {
            SimulationStatus.CREATED,
            SimulationStatus.PREPARING,
            SimulationStatus.NEEDS_REVIEW,
            SimulationStatus.READY,
            SimulationStatus.RUNNING,
            SimulationStatus.PAUSED,
        }
        _status = getattr(state, "status", None)
        if _status is not None and _status in _NON_TERMINAL:
            return jsonify({
                "success": False,
                "error": "report_run_not_terminal",
                "message": (
                    f"Simulation status is '{state.status.value}'; report "
                    "generation requires a terminal run (completed, stopped, "
                    "interrupted, or failed)."
                ),
            }), 409
        
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
                "error": "report_project_not_found"
            }), 404
        
        graph_id = getattr(project, "graph_id", None)
        if (
            not isinstance(graph_id, str)
            or not graph_id.strip()
            or graph_id != graph_id.strip()
        ):
            return jsonify({
                "success": False,
                "error": "report_graph_id_missing",
            }), 400

        simulation_graph_id = getattr(state, "graph_id", None)
        if (
            simulation_graph_id not in (None, "")
            and simulation_graph_id != graph_id
        ):
            return jsonify({
                "success": False,
                "error": "report_graph_scope_mismatch",
            }), 409
        
        simulation_requirement = getattr(project, "simulation_requirement", None)
        if (
            not isinstance(simulation_requirement, str)
            or not simulation_requirement.strip()
        ):
            return jsonify({
                "success": False,
                "error": "report_simulation_requirement_missing",
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
                _release_report_lease_safely(lease)
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
        candidate_task_id = str(uuid.uuid4())
        # Bind the candidate before create_task: the task write happens before
        # its audit event, so a post-write audit failure must still be able to
        # fail this exact record instead of leaving a phantom PENDING task.
        task_id = candidate_task_id
        created_task_id = task_manager.create_task(
            task_type="report_generate",
            task_id=candidate_task_id,
            idempotency_key=f"report_generate:{simulation_id}",
            idempotency_identity={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
            },
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )
        task_id = created_task_id
        lease.task_id = task_id

        if task_id != candidate_task_id:
            existing_task = task_manager.get_task(task_id)
            existing_metadata = getattr(existing_task, "metadata", None) or {}
            existing_report_id = existing_metadata.get("report_id", report_id)
            _release_report_lease_safely(lease)
            lease = None
            return jsonify({
                "success": True,
                "data": {
                    "report_id": existing_report_id,
                    "task_id": task_id,
                    "status": "pending",
                    "already_queued": True,
                },
            }), 202, {'Location': f'/api/jobs/{task_id}'}
        
        from ...tasks.report_tasks import generate_report_task

        generate_report_task.apply_async(
            kwargs={
                "simulation_id": simulation_id,
                "report_id": report_id,
            },
            task_id=task_id,
        )

        _release_report_lease_safely(lease)
        lease = None
        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "task_id": task_id,
                "status": "pending"
            }
        }), 202, {'Location': f'/api/jobs/{task_id}'}

    except TaskIdempotencyConflict:
        _release_report_lease_safely(lease)
        lease = None
        return jsonify({
            "success": False,
            "error": "idempotency_key_conflict",
        }), 409
    except Exception:
        failure_code = "report_dispatch_failed"
        _fail_report_task_safely(task_manager, task_id, failure_code)
        _release_report_lease_safely(lease)
        lease = None
        logger.error(
            "Report generation start failed: code=%s",
            failure_code,
            extra={"privacy_safe": True},
        )
        response = jsonify({
            "success": False,
            "error": failure_code,
        })
        return mark_public_safe_error(response, failure_code), 503


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
            **truth_metadata()
        })
        
    except Exception as e:
        logger.error(f"Failed to check report status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Agent Log Interfaces ==============

ROUTES = (
    ("/generate", ['POST'], "generate_report"),
    ("/generate/status", ['GET', 'POST'], "get_generate_status"),
    ("/<report_id>", ['DELETE'], "delete_report"),
    ("/<report_id>/progress", ['GET'], "get_report_progress"),
    ("/check/<simulation_id>", ['GET'], "check_report_status"),
)
