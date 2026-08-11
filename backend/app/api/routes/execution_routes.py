"""
Simulation API Routes
Step 2: Zep Entity Reading & Filtering, OASIS Simulation Preparation & Running (Fully Automated)
"""

import os
import traceback
from flask import request, jsonify

from .. import simulation_bp
from ..simulation import (
    _resolve_graph_memory_request,
    _check_simulation_prepared,
    _safe_sim_dir,
)
from ...config import Config
from ...services.simulation_manager import SimulationManager, SimulationStatus
from ...services.simulation_runner import SimulationRunner, RunnerStatus
from ...services.runtime_control_store import RuntimeControlStore
from ...services.decision_lens_repository import DecisionLensAdmissionError
from ...services.simulation_preflight import (
    assert_decision_lens_execution_admission,
)
from ...services.claim_boundary import synthetic_output_disclosure
from ...utils.logger import get_logger
from ...utils.input_policy import (
    FOLLOWER_COUNT_MAX,
    InputPolicyError,
    SIMULATION_ROUNDS_MAX,
    bounded_integer,
    validate_weight_distribution,
)

from app.api.schemas import (
    SimulationControlRequest,
    StartSimulationRequest,
    StopSimulationRequest,
    validate_schema,
)

logger = get_logger('askthepeople.api.simulation')


_CONTROL_ACTIVE_STATUSES = {
    RunnerStatus.STARTING.value,
    RunnerStatus.RUNNING.value,
    RunnerStatus.PAUSED.value,
}
_RESTART_BLOCKED_STATUSES = _CONTROL_ACTIVE_STATUSES | {
    RunnerStatus.STOPPING.value,
}


def _runner_status_value(run_state):
    status = getattr(run_state, "runner_status", None)
    return getattr(status, "value", status)


def _active_control_platforms(run_state):
    persisted = getattr(run_state, "active_platforms", None)
    if isinstance(persisted, list) and persisted:
        return [
            platform
            for platform in ("twitter", "reddit")
            if platform in persisted
        ]

    running = []
    if getattr(run_state, "twitter_running", False):
        running.append("twitter")
    if getattr(run_state, "reddit_running", False):
        running.append("reddit")
    return running


def _enqueue_runtime_control(
    simulation_id,
    command_type,
    args,
    requested_platforms=None,
    idempotency_key=None,
):
    manager = SimulationManager()
    simulation_state = manager.get_simulation(simulation_id)
    if simulation_state is None:
        return None, ({
            "success": False,
            "code": "simulation_not_found",
            "error": f"Simulation does not exist: {simulation_id}",
        }, 404)

    run_state = SimulationRunner.get_run_state(simulation_id)
    run_status = _runner_status_value(run_state)
    if run_state is None:
        return None, ({
            "success": False,
            "code": "simulation_not_active",
            "error": "simulation_not_active",
            "message": "Runtime controls require an active persisted run.",
            "simulation_id": simulation_id,
        }, 409)

    attempt_id = getattr(run_state, "attempt_id", None)
    fencing_token = getattr(run_state, "fencing_token", None)
    if not attempt_id or fencing_token is None:
        return None, ({
            "success": False,
            "code": "runtime_attempt_unavailable",
            "error": "runtime_attempt_unavailable",
            "message": "The active run has no durable ownership identity.",
        }, 409)

    control_store = RuntimeControlStore(
        _safe_sim_dir(simulation_id),
        attempt_id=attempt_id,
        fencing_token=fencing_token,
    )
    if command_type == "stop" and run_status == RunnerStatus.STOPPED.value:
        completed_stop = control_store.find_completed_control(
            "stop",
            attempt_id=attempt_id,
            fencing_token=fencing_token,
        )
        completed_targets = (
            completed_stop.get("expected_platforms", [])
            if completed_stop
            else []
        )
        retry_targets = list(requested_platforms or completed_targets)
        if completed_stop and set(retry_targets) == set(completed_targets):
            return completed_stop, None

    accepts_control = run_status in _CONTROL_ACTIVE_STATUSES or (
        command_type == "stop" and run_status == RunnerStatus.STOPPING.value
    )
    if not accepts_control:
        return None, ({
            "success": False,
            "code": "simulation_not_active",
            "error": "simulation_not_active",
            "message": "Runtime controls require an active persisted run.",
            "simulation_id": simulation_id,
        }, 409)

    active_platforms = _active_control_platforms(run_state)
    requested_targets = list(requested_platforms or active_platforms)
    targets = [
        platform for platform in active_platforms if platform in requested_targets
    ]
    if (
        not targets
        or len(targets) != len(requested_targets)
        or any(platform not in active_platforms for platform in requested_targets)
    ):
        return None, ({
            "success": False,
            "code": "runtime_platform_not_active",
            "error": "runtime_platform_not_active",
            "message": "Every target platform must be active in this run.",
            "active_platforms": active_platforms,
        }, 409)

    if command_type == "stop" and set(targets) != set(active_platforms):
        return None, ({
            "success": False,
            "code": "stop_requires_all_active_platforms",
            "error": "stop_requires_all_active_platforms",
            "message": "Stopping a run requires every active platform.",
            "active_platforms": active_platforms,
        }, 409)

    if command_type == "stop":
        idempotency_key = (
            f"stop:{attempt_id}:{fencing_token}:{','.join(targets)}"
        )

    control = control_store.enqueue(
        command_type,
        args,
        targets,
        idempotency_key=idempotency_key,
    )
    return control, None


def _queued_control_response(simulation_id, control):
    control_status = control.get("status", "queued")
    response = jsonify({
        "success": True,
        "simulation_id": simulation_id,
        "status": control_status,
        "data": control,
        "disclosure": synthetic_output_disclosure(),
    })
    response.status_code = 202
    response.headers["Location"] = (
        f"/api/simulation/{simulation_id}/control/{control['control_id']}"
    )
    return response



# P0 path-escape fix (audit §5 P0). The platform identifier is a request-
# Run-platform validation lives inline at the start route (the set includes
# "parallel", which has no single db file). The platform→db-filename map for
# the posts/comments reader lives in services/simulation_activity_reader.py.



@simulation_bp.route('/start', methods=['POST'])
@validate_schema(StartSimulationRequest)
def start_simulation():
    """
    Start running simulation

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",          // Required, Simulation ID
            "platform": "parallel",                // Optional: twitter / reddit / parallel (default)
            "max_rounds": 100,                     // Optional: max simulation rounds to truncate long simulations
            "force": false                         // Optional: clean terminal run artifacts before restart
        }

    About the force parameter:
        - Active or stopping runs return a conflict and must be durably stopped first
        - Terminal runs may have their prior run logs cleaned before restart
        - Cleans: run_state.json, actions.jsonl, simulation.log, etc.
        - Does not clean configuration files (simulation_config.json) or profile files
        - Suitable for scenarios where re-running simulation is needed

    Generated activity is retained only in the per-run observation store.
    Requests to write generated activity into any graph are rejected.

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "process_pid": 12345,
                "twitter_running": true,
                "reddit_running": true,
                "started_at": "2025-12-01T10:00:00",
                "graph_memory_update_enabled": false,
                "observation_storage": "simulation_observation_store",
                "source_graph_mutated": false,
                "force_restarted": true               // Whether forced restart
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400

        platform = data.get('platform', 'parallel')
        force = data.get('force', False)  # Optional: force restart
        enable_followers = data.get('enable_followers', False)
        try:
            max_rounds_value = data.get('max_rounds')
            max_rounds = (
                bounded_integer(
                    max_rounds_value,
                    field="max_rounds",
                    minimum=1,
                    maximum=SIMULATION_ROUNDS_MAX,
                )
                if max_rounds_value is not None
                else None
            )
            follower_count = bounded_integer(
                data.get('follower_count', Config.FOLLOWER_DEFAULT_COUNT),
                field="follower_count",
                minimum=0,
                maximum=FOLLOWER_COUNT_MAX,
            )
            follower_distribution = validate_weight_distribution(
                data.get('follower_distribution'),
                field="follower_distribution",
                allowed_keys={
                    "AMPLIFIER",
                    "CONTRARIAN",
                    "NEUTRAL",
                    "LURKER",
                },
            )
            if not isinstance(enable_followers, bool):
                raise InputPolicyError(
                    "invalid_boolean_field",
                    "enable_followers must be a JSON boolean.",
                )
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400

        if platform not in ['twitter', 'reddit', 'parallel']:
            return jsonify({
                "success": False,
                "error": f"Invalid platform type: {platform}, options: twitter/reddit/parallel"
            }), 400

        # Check if the simulation is ready
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404

        # Admission precedes force-stop, cleanup, task creation, dispatch, and
        # all simulation state mutation. READY alone is never authorization.
        sim_dir = _safe_sim_dir(simulation_id)
        try:
            assert_decision_lens_execution_admission(sim_dir)
        except DecisionLensAdmissionError as exc:
            return jsonify({
                "success": False,
                "code": exc.code,
                "error": exc.code,
                "message": (
                    "This run requires a current, approved decision-lens "
                    "boundary and matching runtime artifacts."
                ),
                "remediation": exc.remediation,
                "simulation_id": simulation_id,
            }), 409

        # Validate the write target before force-restart can stop a process or
        # remove run logs. Invalid provenance settings must have no side effects.
        enable_graph_memory_update, synthetic_graph_id = _resolve_graph_memory_request(
            data,
            source_graph_id=state.graph_id,
        )
        force_restarted = False
        
        
        # Intelligent status handling: if preparation work is complete, allow restart
        if state.status != SimulationStatus.READY:
            # Check if preparation work is complete
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)

            if is_prepared:
                # Preparation complete, check for running processes
                if state.status in {SimulationStatus.RUNNING, SimulationStatus.PAUSED}:
                    # Durable run state, not process-local memory, decides
                    # whether a new execution can be dispatched.
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if (
                        run_state is None
                        or _runner_status_value(run_state) in _RESTART_BLOCKED_STATUSES
                    ):
                        return jsonify({
                            "success": False,
                            "code": "active_run_stop_required",
                            "error": "active_run_stop_required",
                            "message": (
                                "Queue a durable stop request and wait for the "
                                "persisted run state to become stopped before restarting."
                            ),
                            "simulation_id": simulation_id,
                            "force_requested": bool(force),
                        }), 409

                # If force mode, clean up run logs
                if force:
                    logger.info(f"Force mode: cleaning up simulation logs {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Warning cleaning up logs: {cleanup_result.get('errors')}")
                    force_restarted = True

                # Process does not exist or has ended, reset status to ready
                logger.info(f"Simulation {simulation_id} preparation complete, reset state to ready (Original status: {state.status.value})")
                state.status = SimulationStatus.READY
                manager._save_simulation_state(state)
            else:
                # Preparation not complete
                return jsonify({
                    "success": False,
                    "error": f"Simulation not ready, current status: {state.status.value}, please call /prepare API first"
                }), 400

        # Create Task in TaskManager for background tracking
        from ...models.task import TaskManager
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_run",
            metadata={
                "simulation_id": simulation_id,
                "platform": platform,
                "max_rounds": max_rounds,
            }
        )

        config_path = os.path.join(sim_dir, "simulation_config.json")

        try:
            from ...tasks.simulation_tasks import run_simulation_task
            run_simulation_task.apply_async(
                kwargs={
                    "simulation_id": simulation_id,
                    "platform": platform,
                    "max_rounds": max_rounds,
                    "enable_graph_memory_update": enable_graph_memory_update,
                    "graph_id": synthetic_graph_id,
                    "enable_followers": enable_followers,
                    "follower_count": follower_count,
                    "follower_distribution": follower_distribution,
                    "source_graph_id": state.graph_id,
                    "task_id": task_id,
                    "config_path": config_path,
                },
                task_id=task_id,
            )
        except Exception as celery_err:
            logger.error(
                "Celery dispatch failed for simulation %s; refusing to run "
                "OASIS in the request process: %s",
                simulation_id,
                celery_err,
            )
            task_manager.fail_task(
                task_id,
                error=str(celery_err),
                public_error="simulation_dispatch_unavailable",
            )
            resp = jsonify({
                "success": False,
                "code": "simulation_dispatch_unavailable",
                "error": "simulation_dispatch_unavailable",
                "message": (
                    "Simulation execution could not be queued. "
                    "Try again after the worker service is available."
                ),
                "simulation_id": simulation_id,
                "task_id": task_id,
            })
            resp.status_code = 503
            resp.headers["Retry-After"] = "5"
            return resp

        response_runner_status = "queued"

        # Update simulation status in SimulationManager
        state.status = SimulationStatus.RUNNING
        manager._save_simulation_state(state)

        data_payload = {
            "simulation_id": simulation_id,
            "task_id": task_id,
            "status": "queued",
            "runner_status": response_runner_status,
            "graph_memory_update_enabled": enable_graph_memory_update,
            "observation_storage": "simulation_observation_store",
            "source_graph_mutated": False,
            "force_restarted": force_restarted,
        }
        if max_rounds:
            data_payload['max_rounds_applied'] = max_rounds

        resp = jsonify({
            "success": True,
            "task_id": task_id,
            "simulation_id": simulation_id,
            "status": "queued",
            "message": "Simulation execution queued.",
            "data": data_payload,
            "disclosure": synthetic_output_disclosure(),
        })
        resp.status_code = 202
        return resp

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Start simulation failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/stop', methods=['POST'])
@validate_schema(StopSimulationRequest)
def stop_simulation():
    """Queue an idempotent durable stop for the active runtime attempt."""
    try:
        simulation_id = request.validated_data.simulation_id
        control, error = _enqueue_runtime_control(
            simulation_id,
            "stop",
            {},
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        if error:
            payload, status = error
            return jsonify(payload), status
        return _queued_control_response(simulation_id, control)
    except ValueError as exc:
        status = 409 if str(exc) == "idempotency_key_conflict" else 400
        return jsonify({
            "success": False,
            "code": str(exc),
            "error": str(exc),
        }), status
    except Exception as exc:
        logger.error(f"Stop simulation enqueue failed: {str(exc)}")
        return jsonify({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/control', methods=['POST'])
@validate_schema(SimulationControlRequest)
def create_runtime_control(simulation_id: str):
    """Queue a typed control against the current durable run attempt."""
    control_request = request.validated_data
    try:
        control, error = _enqueue_runtime_control(
            simulation_id,
            control_request.command_type,
            control_request.args,
            control_request.platforms,
            request.headers.get("Idempotency-Key"),
        )
        if error:
            payload, status = error
            return jsonify(payload), status
        return _queued_control_response(simulation_id, control)
    except ValueError as exc:
        status = 409 if str(exc) == "idempotency_key_conflict" else 400
        return jsonify({
            "success": False,
            "code": str(exc),
            "error": str(exc),
        }), status


@simulation_bp.route('/<simulation_id>/control/<control_id>', methods=['GET'])
def get_runtime_control(simulation_id: str, control_id: str):
    """Return aggregate status across the control's complete target set."""
    manager = SimulationManager()
    if manager.get_simulation(simulation_id) is None:
        return jsonify({
            "success": False,
            "code": "simulation_not_found",
            "error": f"Simulation does not exist: {simulation_id}",
        }), 404
    status = RuntimeControlStore(_safe_sim_dir(simulation_id)).get_status(control_id)
    if status is None:
        return jsonify({
            "success": False,
            "code": "runtime_control_not_found",
            "error": "runtime_control_not_found",
        }), 404
    return jsonify({
        "success": True,
        "simulation_id": simulation_id,
        "data": status,
        "disclosure": synthetic_output_disclosure(),
    })


@simulation_bp.route('/<simulation_id>/inject', methods=['POST'])
def inject_simulation_event(simulation_id: str):
    """Compatibility endpoint that queues a typed durable inject_event."""
    try:
        data = request.get_json() or {}
        event_aliases = {
            "breaking_news": "media_breaking_news",
            "news": "media_breaking_news",
            "post": "seed_post",
        }
        requested_event_type = data.get("event_type") or "media_breaking_news"
        event_type = event_aliases.get(
            requested_event_type,
            requested_event_type,
        )
        payload = data.get("payload", data.get("content", data))
        if not isinstance(payload, dict):
            payload = {"content": payload}
        requested_platforms = data.get("platforms")
        if requested_platforms is None and data.get("platform") in {"twitter", "reddit"}:
            requested_platforms = [data["platform"]]

        compatibility_request = SimulationControlRequest.model_validate({
            "command_type": "inject_event",
            "args": {
                "event_type": event_type,
                "payload": payload,
                "targeting": data.get("targeting") or {},
                "reason": data.get("reason"),
            },
            "platforms": requested_platforms,
        })
        control, error = _enqueue_runtime_control(
            simulation_id,
            compatibility_request.command_type,
            compatibility_request.args,
            compatibility_request.platforms,
            request.headers.get("Idempotency-Key"),
        )
        if error:
            error_payload, status = error
            return jsonify(error_payload), status
        return _queued_control_response(simulation_id, control)
    except ValueError as exc:
        return jsonify({
            "success": False,
            "code": "invalid_runtime_control",
            "error": "invalid_runtime_control",
            "message": str(exc),
        }), 422
    except Exception as exc:
        logger.error(f"Failed to enqueue simulation event for {simulation_id}: {str(exc)}")
        return jsonify({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/<simulation_id>/run-status', methods=['GET'])
def get_run_status(simulation_id: str):
    """
    Get simulation run real-time status (for frontend polling)
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                "total_rounds": 144,
                "progress_percent": 3.5,
                "simulated_hours": 2,
                "total_simulation_hours": 72,
                "twitter_running": true,
                "reddit_running": true,
                "twitter_actions_count": 150,
                "reddit_actions_count": 200,
                "total_actions_count": 350,
                "started_at": "2025-12-01T10:00:00",
                "updated_at": "2025-12-01T10:30:00"
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "current_round": 0,
                    "total_rounds": 0,
                    "progress_percent": 0,
                    "twitter_actions_count": 0,
                    "reddit_actions_count": 0,
                    "total_actions_count": 0,
                },
                "disclosure": synthetic_output_disclosure(),
            })
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict(),
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Get run status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/<simulation_id>/status', methods=['GET'])
def get_simulation_status(simulation_id: str):
    """
    Get simulation execution status from the process-local task and run state.
    """
    from ...models.task import TaskManager
    try:
        task_manager = TaskManager()
        tasks = task_manager.list_tasks(task_type="simulation_run")
        matched_task = None
        for t in tasks:
            meta = t.get("metadata", {})
            if meta.get("simulation_id") == simulation_id:
                matched_task = t
                break

        run_state = SimulationRunner.get_run_state(simulation_id)
        
        status = "idle"
        progress = 0
        message = ""
        task_id = None
        
        if matched_task:
            task_id = matched_task.get("task_id")
            status = matched_task.get("status")
            progress = matched_task.get("progress", 0)
            message = matched_task.get("message", "")
        elif run_state:
            status = run_state.runner_status.value if hasattr(run_state.runner_status, 'value') else str(run_state.runner_status)
            if run_state.total_rounds > 0:
                progress = int((run_state.current_round / run_state.total_rounds) * 100)
            message = f"Simulation round {run_state.current_round}/{run_state.total_rounds}"

        return jsonify({
            "success": True,
            "simulation_id": simulation_id,
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "data": run_state.to_dict() if run_state else (matched_task or {}),
            "disclosure": synthetic_output_disclosure(),
        })
    except Exception as e:
        logger.error(f"Get simulation status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id: str):
    """
    Get task status from the process-local task manager.
    """
    from ...models.task import TaskManager
    try:
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({
                "success": False,
                "error": f"Task not found: {task_id}"
            }), 404
        return jsonify({
            "success": True,
            "data": task.to_public_dict(),
            "disclosure": synthetic_output_disclosure(),
        })
    except Exception as e:
        logger.error(f"Get task status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/env-status', methods=['POST'])
def get_env_status():
    """
    Get simulation environment status

    Check if the simulation environment is alive (can receive Interview commands)

    Request (JSON):
        {
            "simulation_id": "sim_xxxx"  // Required, simulation ID
        }

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "env_alive": true,
                "twitter_available": true,
                "reddit_available": true,
                "message": "Environment is running, can receive Interview commands"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400

        env_alive = SimulationRunner.check_env_alive(simulation_id)
        
        # Get more detailed status information
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        if env_alive:
            message = (
                "Environment is running and can receive generated profile "
                "follow-ups"
            )
        else:
            message = "Environment is not running or has been closed"

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "env_alive": env_alive,
                "twitter_available": env_status.get("twitter_available", False),
                "reddit_available": env_status.get("reddit_available", False),
                "message": message
            }
        })

    except Exception as e:
        logger.error(f"Failed to get environment status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/close-env', methods=['POST'])
def close_simulation_env():
    """
    Close simulation environment
    
    Send close environment command to simulation, allowing it to gracefully exit wait-for-command mode.
    
    Note: This is different from the /stop interface; /stop will forcibly terminate the process,
    while this interface will let the simulation gracefully close the environment and exit.
    
    Request (JSON):
        {
            "simulation_id": "sim_xxxx",  // Required, simulation ID
            "timeout": 30                  // Optional, timeout (seconds), default 30
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "message": "Environment close command sent",
                "result": {...},
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400
        
        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id,
            timeout=timeout
        )

        # Audit P1 fix ("Contradictory lifecycle semantics"): only mark the
        # simulation COMPLETED when the close actually succeeded. The old code
        # set COMPLETED unconditionally, so a failed close looked identical to
        # a successful one — the GET endpoints reported a "completed" run that
        # had not in fact closed cleanly. On failure, leave the prior status
        # (still RUNNING/STOPPED) so the discrepancy is visible; do not
        # silently upgrade a failure to COMPLETED.
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state and result.get("success"):
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)
        
        return jsonify({
            "success": result.get("success", False),
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Failed to close environment: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
