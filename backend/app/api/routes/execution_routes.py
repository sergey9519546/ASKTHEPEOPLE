"""
Simulation API Routes
Step 2: Zep Entity Reading & Filtering, OASIS Simulation Preparation & Running (Fully Automated)
"""

import os
import io
import json
import traceback
from datetime import datetime
from flask import request, jsonify, send_file, make_response
from werkzeug.utils import secure_filename

from .. import simulation_bp
from ..simulation import (
    _with_profile_truth,
    _with_config_truth,
    _resolve_graph_memory_request,
    _validate_prepare_controls,
    optimize_interview_prompt,
    _check_simulation_prepared,
    _safe_sim_dir
)
from .. import limiter
from ...config import Config
from ...services.zep_entity_reader import ZepEntityReader
from ...services.oasis_profile_generator import OasisProfileGenerator
from ...services.simulation_manager import SimulationManager, SimulationStatus
from ...services.simulation_observation_store import search_observations
from ...services.simulation_runner import SimulationRunner, RunnerStatus
from ...services.export_service import CSVExporter
from ...services.claim_boundary import (
    fictional_profile_disclosure,
    graph_record_disclosure,
    synthetic_activity_disclosure,
    synthetic_config_disclosure,
    synthetic_output_disclosure,
)
from ...services.zep_tools import ZepToolsService
from ...utils.logger import get_logger
from ...utils.input_policy import (
    ARCHETYPE_COUNT_MAX,
    ARCHETYPE_EXPANSION_MAX,
    ENTITY_TYPE_FILTER_MAX,
    ENTITY_TYPE_NAME_MAX,
    FOLLOWER_COUNT_MAX,
    INTERVIEW_BATCH_MAX,
    INTERVIEW_PROMPT_MAX,
    InputPolicyError,
    PARALLEL_PROFILE_WORKERS_MAX,
    PREPARE_ENTITY_MAX,
    PREPARED_PROFILE_MAX,
    SIMULATION_ROUNDS_MAX,
    bounded_integer,
    bounded_text,
    validate_item_count,
    validate_weight_distribution,
)
from ...models.project import ProjectManager

logger = get_logger('askthepeople.api.simulation')

from ...utils.safe_path import safe_join, SafePathError


# Base directory for simulation run-state data, computed once. Used as the
# safe_join base for all user-supplied simulation_id values flowing into
# filesystem/sqlite paths (path-traversal defense).
_RUN_STATE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../uploads/simulations')
)


# P0 path-escape fix (audit §5 P0). The platform identifier is a request-
# controlled value; it MUST be parsed as a strict enum and resolved to a
# fixed filename. Do NOT interpolate request text into a filename.
ALLOWED_PLATFORMS = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}



@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    """
    Start running simulation

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",          // Required, Simulation ID
            "platform": "parallel",                // Optional: twitter / reddit / parallel (default)
            "max_rounds": 100,                     // Optional: max simulation rounds to truncate long simulations
            "force": false                         // Optional: force restart (stops running simulation and cleans logs)
        }

    About the force parameter:
        - When enabled, if simulation is running or completed, it stops first and cleans run logs
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
                if state.status == SimulationStatus.RUNNING:
                    # Check if simulation process is actually running
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        # Process is indeed running
                        if force:
                            # Force mode: stop running simulation
                            logger.info(f"Force mode: stopping running simulation {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Warning stopping simulation: {str(e)}")
                        else:
                            return jsonify({
                                "success": False,
                                "error": f"Simulation is running, please call /stop API first, or use force=true to force restart"
                            }), 400

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
        from ...models.task import TaskManager, TaskStatus
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_run",
            metadata={
                "simulation_id": simulation_id,
                "platform": platform,
                "max_rounds": max_rounds,
            }
        )

        sim_dir = _safe_sim_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")

        celery_dispatched = False
        try:
            from ...tasks.simulation_tasks import run_simulation_task
            run_simulation_task.delay(
                simulation_id=simulation_id,
                platform=platform,
                max_rounds=max_rounds,
                enable_graph_memory_update=enable_graph_memory_update,
                graph_id=synthetic_graph_id,
                enable_followers=enable_followers,
                follower_count=follower_count,
                follower_distribution=follower_distribution,
                source_graph_id=state.graph_id,
                task_id=task_id,
                config_path=config_path,
            )
            # Keep the TaskManager id as the client-facing handle. The Celery
            # result id is not known to TaskManager, so returning it would make
            # GET /api/simulation/task/<task_id>/status 404.
            celery_dispatched = True
        except Exception as celery_err:
            logger.warning(f"Celery dispatch unavailable or failed, falling back to direct runner: {celery_err}")

        if not celery_dispatched:
            # Fallback runner mode (when Celery broker is not running in test mode)
            run_state = SimulationRunner.start_simulation(
                simulation_id=simulation_id,
                platform=platform,
                max_rounds=max_rounds,
                enable_graph_memory_update=enable_graph_memory_update,
                graph_id=synthetic_graph_id,
                source_graph_id=state.graph_id,
                enable_followers=enable_followers,
                follower_count=follower_count,
                follower_distribution=follower_distribution,
            )
            task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                message="Simulation execution started via runner",
                progress=10,
                result=run_state.to_dict(),
            )
            r_status = getattr(run_state, 'runner_status', 'running')
            response_runner_status = r_status.value if hasattr(r_status, 'value') else str(r_status)
        else:
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
def stop_simulation():
    """
    Stop simulation
    
    Request (JSON):
        {
            "simulation_id": "sim_xxxx"  # Required, simulation ID
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "stopped",
                "completed_at": "2025-12-01T12:00:00"
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
        
        run_state = SimulationRunner.stop_simulation(simulation_id)
        
        # Update simulation status
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.PAUSED
            manager._save_simulation_state(state)
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict(),
            "disclosure": synthetic_output_disclosure(),
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Stop simulation failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@simulation_bp.route('/<simulation_id>/inject', methods=['POST'])
def inject_simulation_event(simulation_id: str):
    """Publish real-time scenario injection intervention payload to Redis Pub/Sub.

    Publishes intervention payloads (breaking news, persona modifications, dynamic instructions)
    to Redis Pub/Sub channel `simulation:<simulation_id>:events` for live ingestion by the simulation tick loop.
    """
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404

        data = request.get_json() or {}
        event_type = data.get("event_type", "inject_event")
        payload = data.get("payload", data.get("content", data))
        timestamp = data.get("timestamp") or datetime.now().isoformat()

        event_message = {
            "simulation_id": simulation_id,
            "event_type": event_type,
            "payload": payload if isinstance(payload, dict) else {"content": payload},
            "timestamp": timestamp,
            "raw_data": data,
        }

        channel = f"simulation:{simulation_id}:events"
        published_redis = False

        try:
            redis_url = Config.REDIS_URL
            if redis_url and not redis_url.startswith("memory://"):
                import redis
                r = redis.from_url(redis_url, socket_timeout=1.0, socket_connect_timeout=1.0, decode_responses=True)
                r.publish(channel, json.dumps(event_message))
                published_redis = True
        except Exception as e:
            logger.warning(f"Redis publish failed for {channel}: {e}")

        if not published_redis:
            from ...services.simulation_observation_store import push_in_memory_event
            push_in_memory_event(simulation_id, event_message)

        return jsonify({
            "success": True,
            "message": "Scenario injection event published successfully",
            "simulation_id": simulation_id,
            "channel": channel,
            "event": event_message,
            "published_redis": published_redis,
        }), 200
    except Exception as e:
        logger.error(f"Failed to inject simulation event for {simulation_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
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
        
        # Update simulation status
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
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

