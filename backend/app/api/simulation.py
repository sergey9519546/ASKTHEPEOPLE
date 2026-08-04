"""
Simulation API: read-oriented routes plus the shared request helpers.

Scope after the gate 1 decomposition
------------------------------------
The write/lifecycle handlers (prepare, start, stop, inject, interview, export,
entity listing) live in `api/routes/`, which is what `api/__init__.py`
registers. This module keeps two things:

  1. the read-oriented routes never moved out (list, history, profiles, config,
     observations, posts, comments, metrics, compare, timeline, ...)
  2. the helpers every `routes/` module imports from here — `_safe_sim_dir`,
     `_with_profile_truth`, `_with_config_truth`, `_resolve_graph_memory_request`,
     `_validate_prepare_controls`, `optimize_interview_prompt`,
     `_check_simulation_prepared`

It also used to carry undecorated copies of all 24 handlers that `routes/`
serves. Nothing could reach them, but they were kept in sync by hand and tests
called them directly — so a safety assertion could pass against code that never
answered a request. They are gone; edit the `routes/` module instead.
"""

import os
import json
import traceback
from datetime import datetime
from flask import request, jsonify
from werkzeug.utils import secure_filename

from . import simulation_bp
from ..config import Config
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_observation_store import search_observations
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..services.claim_boundary import (
    fictional_profile_disclosure,
    synthetic_activity_disclosure,
    synthetic_config_disclosure,
    synthetic_output_disclosure,
)
from ..utils.logger import get_logger
from ..utils.input_policy import (
    ARCHETYPE_COUNT_MAX,
    ARCHETYPE_EXPANSION_MAX,
    ENTITY_TYPE_FILTER_MAX,
    ENTITY_TYPE_NAME_MAX,
    InputPolicyError,
    PARALLEL_PROFILE_WORKERS_MAX,
    PREPARED_PROFILE_MAX,
    bounded_integer,
    bounded_text,
    validate_item_count,
)
from ..models.project import ProjectManager

logger = get_logger('askthepeople.api.simulation')

from ..utils.safe_path import safe_join, SafePathError


# P0 path-escape fix (audit §5 P0). The platform identifier is a request-
# controlled value; it MUST be parsed as a strict enum and resolved to a
# fixed filename. Do NOT interpolate request text into a filename.
ALLOWED_PLATFORMS = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}


def _safe_sim_dir(simulation_id: str) -> str:
    """Resolve a validated simulation run-state directory (path-traversal safe).

    Centralizes OASIS_SIMULATION_DATA_DIR joins; raises SafePathError on bad ids.
    """
    return safe_join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)


def _with_profile_truth(profiles):
    """Attach non-human provenance to detached API profile records."""
    disclosed = []
    for profile in profiles if isinstance(profiles, list) else []:
        if isinstance(profile, dict):
            disclosed.append({**profile, **fictional_profile_disclosure()})
        else:
            disclosed.append(profile)
    return disclosed


def _with_activity_truth(records):
    """Attach synthetic-run provenance to detached API activity records."""
    disclosed = []
    for record in records if isinstance(records, list) else []:
        if isinstance(record, dict):
            disclosed.append({**record, **synthetic_activity_disclosure()})
        else:
            disclosed.append(record)
    return disclosed


def _with_config_truth(config):
    """Ensure old and new config payloads carry the same truth contract."""
    if not isinstance(config, dict):
        return config
    disclosed = dict(config)
    disclosed["truth_status"] = synthetic_output_disclosure()
    disclosed["control_metadata"] = synthetic_config_disclosure()
    return disclosed


def _resolve_graph_memory_request(
    data: dict,
    *,
    source_graph_id: str | None,
) -> tuple[bool, str | None]:
    """Reject graph writes while keeping ordinary observation storage explicit."""
    requested = data.get("enable_graph_memory_update", False)
    if requested is False or requested is None:
        return False, None
    if requested is not True:
        raise InputPolicyError(
            "invalid_boolean_field",
            "enable_graph_memory_update must be a JSON boolean.",
        )
    raise InputPolicyError(
        "synthetic_graph_writes_unsupported",
        (
            "Writing generated activity to a graph is unsupported. Generated "
            "activity remains in the simulation observation store."
        ),
    )


def _validate_prepare_controls(data: dict) -> dict:
    """Validate bounded profile-generation controls before any provider I/O."""
    raw_entity_types = data.get("entity_types")
    entity_types = None
    if raw_entity_types is not None:
        entity_types = validate_item_count(
            raw_entity_types,
            field="entity_types",
            maximum=ENTITY_TYPE_FILTER_MAX,
        )
        entity_types = [
            bounded_text(
                item,
                field="entity_types item",
                max_length=ENTITY_TYPE_NAME_MAX,
                required=True,
            )
            for item in entity_types
        ]

    parallel_profile_count = bounded_integer(
        data.get("parallel_profile_count", 5),
        field="parallel_profile_count",
        minimum=1,
        maximum=PARALLEL_PROFILE_WORKERS_MAX,
    )

    use_archetypes = data.get("use_archetypes", False)
    use_llm_for_profiles = data.get("use_llm_for_profiles", True)
    force_regenerate = data.get("force_regenerate", False)
    for field, value in (
        ("use_archetypes", use_archetypes),
        ("use_llm_for_profiles", use_llm_for_profiles),
        ("force_regenerate", force_regenerate),
    ):
        if not isinstance(value, bool):
            raise InputPolicyError(
                "invalid_boolean_field",
                f"{field} must be a JSON boolean.",
            )

    archetype_count = data.get("archetype_count")
    expansion_factor = data.get("expansion_factor")
    if use_archetypes or archetype_count is not None or expansion_factor is not None:
        archetype_count = bounded_integer(
            (
                Config.ARCHETYPE_DEFAULT_COUNT
                if archetype_count is None
                else archetype_count
            ),
            field="archetype_count",
            minimum=1,
            maximum=ARCHETYPE_COUNT_MAX,
        )
        expansion_factor = bounded_integer(
            (
                Config.ARCHETYPE_DEFAULT_EXPANSION_FACTOR
                if expansion_factor is None
                else expansion_factor
            ),
            field="expansion_factor",
            minimum=1,
            maximum=ARCHETYPE_EXPANSION_MAX,
        )
        if archetype_count * expansion_factor > PREPARED_PROFILE_MAX:
            raise InputPolicyError(
                "profile_count_out_of_range",
                (
                    "archetype_count multiplied by expansion_factor may not "
                    f"exceed {PREPARED_PROFILE_MAX} prepared profiles."
                ),
            )

    return {
        "entity_types": entity_types,
        "parallel_profile_count": parallel_profile_count,
        "use_archetypes": use_archetypes,
        "use_llm_for_profiles": use_llm_for_profiles,
        "force_regenerate": force_regenerate,
        "archetype_count": archetype_count,
        "expansion_factor": expansion_factor,
    }


# Compatibility routes still use "interview" in their URLs. The operation is a
# generated profile follow-up: another model output, never human testimony.
INTERVIEW_PROMPT_PREFIX = (
    "You are a fictional generated profile inside one synthetic scenario. "
    "Your answer is another model output, not testimony, public opinion, or a "
    "prediction. Use only the profile assumptions and records from this run. "
    "Reply directly with text without calling tools: "
)


def optimize_interview_prompt(prompt: str, bypass: bool = False) -> str:
    """
    Add the synthetic-output disclosure and prevent tool calls.
    
    Args:
        prompt: Original question
        bypass: If True, bypass prefix optimization (raw mode)
        
    Returns:
        Optimized question
    """
    if not prompt or bypass:
        return prompt
    # Avoid duplicate prefix additions
    if prompt.startswith(INTERVIEW_PROMPT_PREFIX):
        return prompt
    return f"{INTERVIEW_PROMPT_PREFIX}{prompt}"


# ============== Entity Reading Interfaces ==============


# ============== Simulation Management Interfaces ==============


def _check_simulation_prepared(simulation_id: str) -> tuple:
    """
    Check if simulation is already prepared
    
    Checking conditions:
    1. state.json exists and status is 'ready'
    2. Required files exist: reddit_profiles.json, twitter_profiles.csv, simulation_config.json
    
    Note: Running scripts (run_*.py) are kept in the backend/scripts/ directory and no longer copied to the simulation directory
    
    Args:
        simulation_id: Simulation ID
        
    Returns:
        (is_prepared: bool, info: dict)
    """
    import os
    from ..config import Config
    
    simulation_dir = _safe_sim_dir(simulation_id)
    
    # Check if directory exists
    if not os.path.exists(simulation_dir):
        return False, {"reason": "Simulation directory does not exist"}
    
    # List of required files (excluding scripts, which are in backend/scripts/)
    required_files = [
        "state.json",
        "simulation_config.json",
        "agent_profiles.canonical.json",
        "entity_type_registry.json",
        "reddit_profiles.json",
        "twitter_profiles.csv",
        "preflight.json",
    ]
    
    # Check if files exist
    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)
    
    if missing_files:
        return False, {
            "reason": "Missing required files",
            "missing_files": missing_files,
            "existing_files": existing_files
        }
    
    # Check status in state.json
    state_file = os.path.join(simulation_dir, "state.json")
    try:
        import json
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)
        
        # Detailed logs
        logger.debug(f"Detect simulation preparation status: {simulation_id}, status={status}, config_generated={config_generated}")
        
        # If config_generated=True and files exist, consider preparation complete
        # The following statuses indicate preparation work is complete:
        # - ready: Preparation complete, ready to run
        # - preparing: Complete if config_generated=True
        # - running: Running, preparation obviously complete
        # - completed: Completed, preparation obviously complete
        # - stopped: Stopped, preparation obviously complete
        # - failed: Run failed (but preparation is complete)
        prepared_statuses = ["ready", "preparing", "running", "completed", "stopped", "interrupted", "failed"]
        preflight_file = os.path.join(simulation_dir, "preflight.json")
        preflight_passed = False
        if os.path.exists(preflight_file):
            with open(preflight_file, 'r', encoding='utf-8') as pf:
                preflight_data = json.load(pf)
            preflight_passed = preflight_data.get("status") == "passed"

        if status in prepared_statuses and config_generated and preflight_passed:
            # Get file statistics
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")
            config_file = os.path.join(simulation_dir, "simulation_config.json")
            
            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0
            
            # If status is preparing but file complete, auto-update status to ready
            if status == "preparing":
                try:
                    state_data["status"] = "ready"
                    from datetime import datetime
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Automatically update simulation status: {simulation_id} preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Failed to automatically update status: {e}")
            
            logger.info(f"Simulation {simulation_id} Detection result: Prepared (status={status}, config_generated={config_generated})")
            return True, {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "config_generated": config_generated,
                "preflight_passed": preflight_passed,
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files
            }
        else:
            logger.info(f"Simulation {simulation_id} Detection result: Not prepared (status={status}, config_generated={config_generated})")
            return False, {
                "reason": f"Status not in prepared list or config_generated is false: status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated,
                "preflight_passed": preflight_passed,
            }
            
    except Exception as e:
        return False, {"reason": f"Failed to read state file: {str(e)}"}


@simulation_bp.route('/<simulation_id>', methods=['GET'])
def get_simulation(simulation_id: str):
    """Get simulation status"""
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        result = state.to_dict()
        
        # Attach run instructions if simulation is ready
        if state.status == SimulationStatus.READY:
            result["run_instructions"] = manager.get_run_instructions(simulation_id)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Get simulation status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/list', methods=['GET'])
def list_simulations():
    """
    List all simulations
    
    Query parameters:
        project_id: Filter by project ID (optional)
    """
    try:
        project_id = request.args.get('project_id')
        
        manager = SimulationManager()
        simulations = sorted(
            manager.list_simulations(project_id=project_id),
            key=lambda simulation: simulation.updated_at or simulation.created_at or "",
            reverse=True,
        )
        summaries = [
            _enrich_simulation_summary(simulation, manager)
            for simulation in simulations
        ]
        
        return jsonify({
            "success": True,
            "data": summaries,
            "count": len(summaries)
        })
        
    except Exception as e:
        logger.error(f"Failed to list simulations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def _get_report_summary_for_simulation(simulation_id: str):
    """
    Get the latest report_id for a simulation
    
    Iterate through the reports directory to find reports matching simulation_id,
    and return the latest one (sorted by created_at)
    
    Args:
        simulation_id: Simulation ID
        
    Returns:
        Latest report summary or None.
    """
    import json
    
    # reports directory path: backend/uploads/reports
    # __file__ is app/api/simulation.py, need to go up two levels to backend/
    reports_dir = os.path.join(os.path.dirname(__file__), '../../uploads/reports')
    if not os.path.exists(reports_dir):
        return None
    
    matching_reports = []
    
    try:
        for report_folder in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_folder)
            if not os.path.isdir(report_path):
                continue
            
            meta_file = os.path.join(report_path, "meta.json")
            if not os.path.exists(meta_file):
                continue
            
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                if meta.get("simulation_id") == simulation_id:
                    matching_reports.append({
                        "report_id": meta.get("report_id"),
                        "created_at": meta.get("created_at", ""),
                        "status": meta.get("status", "")
                    })
            except Exception:
                continue
        
        if not matching_reports:
            return None
        
        # Sort by creation time in descending order and return the latest one
        matching_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return matching_reports[0]
        
    except Exception as e:
        logger.warning(f"Failed to find report for simulation {simulation_id}: {e}")
        return None


def _enrich_simulation_summary(simulation, manager: SimulationManager):
    """Build the persisted resume DTO shared by history and project listings."""
    summary = simulation.to_dict()
    project = ProjectManager.get_project(simulation.project_id)
    config = manager.get_simulation_config(simulation.simulation_id) or {}
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 0)
    minutes_per_round = max(time_config.get("minutes_per_round", 60), 1)
    recommended_rounds = int(total_hours * 60 / minutes_per_round)

    summary["project_name"] = project.name if project else ""
    summary["simulation_requirement"] = (
        config.get("simulation_requirement")
        or (project.simulation_requirement if project else "")
        or ""
    )
    summary["total_simulation_hours"] = total_hours

    run_state = SimulationRunner.get_run_state(simulation.simulation_id)
    if run_state:
        summary["current_round"] = run_state.current_round
        summary["runner_status"] = run_state.runner_status.value
        summary["total_rounds"] = (
            run_state.total_rounds
            if run_state.total_rounds > 0
            else recommended_rounds
        )
    else:
        summary["current_round"] = 0
        summary["runner_status"] = "idle"
        summary["total_rounds"] = recommended_rounds

    summary["files"] = [
        {"filename": item.get("filename", "Unknown file")}
        for item in ((project.files if project else []) or [])[:3]
    ]

    report = _get_report_summary_for_simulation(simulation.simulation_id)
    summary["report_id"] = report.get("report_id") if report else None
    summary["report_status"] = report.get("status") if report else None

    runner_status = summary["runner_status"]
    if summary["report_id"]:
        summary["workflow_step"] = 4
        summary["resume_target"] = "report"
    elif runner_status in {
        "starting",
        "running",
        "stopping",
        "completed",
        "stopped",
        "failed",
        "interrupted",
    } or summary.get("status") in {
        "running",
        "completed",
        "stopped",
        "interrupted",
    }:
        summary["workflow_step"] = 3
        summary["resume_target"] = "run"
    else:
        summary["workflow_step"] = 2
        summary["resume_target"] = "setup"

    summary["version"] = "v1.0.2"
    created_at = summary.get("created_at", "")
    summary["created_date"] = created_at[:10] if isinstance(created_at, str) else ""
    return summary


@simulation_bp.route('/history', methods=['GET'])
def get_simulation_history():
    """
    Get historical simulation list (with project details)
    
    Used for historical project display on the home page, returning a simulation list containing rich information such as project name and description
    
    Query parameters:
        limit: Return quantity limit (default 20)
    
    Returns:
        {
            "success": true,
            "data": [
                {
                    "simulation_id": "sim_xxxx",
                    "project_id": "proj_xxxx",
                    "project_name": "Project Name",
                    "simulation_requirement": "Simulation requirements...",
                    "status": "completed",
                    "entities_count": 68,
                    "profiles_count": 68,
                    "entity_types": ["Student", "Professor", ...],
                    "created_at": "2024-12-10",
                    "updated_at": "2024-12-10",
                    "total_rounds": 120,
                    "current_round": 120,
                    "report_id": "report_xxxx",
                    "version": "v1.0.2"
                },
                ...
            ],
            "count": 7
        }
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        manager = SimulationManager()
        simulations = sorted(
            manager.list_simulations(),
            key=lambda simulation: simulation.updated_at or simulation.created_at or "",
            reverse=True,
        )[:limit]
        enriched_simulations = [
            _enrich_simulation_summary(simulation, manager)
            for simulation in simulations
        ]
        
        return jsonify({
            "success": True,
            "data": enriched_simulations,
            "count": len(enriched_simulations)
        })
        
    except Exception as e:
        logger.error(f"Failed to get simulation history: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles', methods=['GET'])
def get_simulation_profiles(simulation_id: str):
    """
    Get Agent Profile for simulation
    
    Query parameters:
        platform: Platform type (reddit/twitter, default reddit)
    """
    try:
        platform = request.args.get('platform', 'reddit')
        
        manager = SimulationManager()
        profiles = manager.get_profiles(simulation_id, platform=platform)
        profiles = _with_profile_truth(profiles)
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "count": len(profiles),
                "profiles": profiles,
                **fictional_profile_disclosure(),
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Failed to get profile: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles/realtime', methods=['GET'])
def get_simulation_profiles_realtime(simulation_id: str):
    """
    Get real-time Agent Profile for simulation (for viewing progress during generation)
    
    Difference from /profiles interface:
    - Direct file read, bypassing SimulationManager
    - Suitable for real-time viewing during generation
    - Returns additional metadata (e.g., file modification time, generation status)
    
    Query parameters:
        platform: Platform type (reddit/twitter, default reddit)
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "platform": "reddit",
                "count": 15,
                "total_expected": 93,  // Total expected (if available)
                "is_generating": true,  // Whether generating
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "profiles": [...]
            }
        }
    """
    import json
    import csv
    from datetime import datetime
    
    try:
        platform = request.args.get('platform', 'reddit')
        
        # Get simulation directory
        sim_dir = _safe_sim_dir(simulation_id)
        
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        # Determine file path
        if platform == "reddit":
            profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        else:
            profiles_file = os.path.join(sim_dir, "twitter_profiles.csv")
        
        # Check if files exist
        file_exists = os.path.exists(profiles_file)
        profiles = []
        file_modified_at = None
        
        if file_exists:
            # Get file modification time
            file_stat = os.stat(profiles_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            try:
                if platform == "reddit":
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                else:
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        profiles = list(reader)
                profiles = _with_profile_truth(profiles)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to read profiles file (may be being written): {e}")
                profiles = []
        
        # Check if generating (determined by state.json)
        is_generating = False
        total_expected = None
        
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    total_expected = state_data.get("entities_count")
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "platform": platform,
                "count": len(profiles),
                "total_expected": total_expected,
                "is_generating": is_generating,
                "file_exists": file_exists,
                "file_modified_at": file_modified_at,
                "profiles": profiles,
                **fictional_profile_disclosure(),
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get profile real-time: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config/realtime', methods=['GET'])
def get_simulation_config_realtime(simulation_id: str):
    """
    Get real-time simulation configuration (for viewing progress during generation)
    
    Difference from /config interface:
    - Direct file read, bypassing SimulationManager
    - Suitable for real-time viewing during generation
    - Returns additional metadata (e.g., file modification time, generation status)
    - Returns partial info even if configuration generation is not yet complete
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "is_generating": true,  // Whether generating
                "generation_stage": "generating_config",  // Current generation stage
                "config": {...}  // Config content (if exists)
            }
        }
    """
    import json
    from datetime import datetime
    
    try:
        # Get simulation directory
        sim_dir = _safe_sim_dir(simulation_id)
        
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        # Config file path
        config_file = os.path.join(sim_dir, "simulation_config.json")
        
        # Check if files exist
        file_exists = os.path.exists(config_file)
        config = None
        file_modified_at = None
        
        if file_exists:
            # Get file modification time
            file_stat = os.stat(config_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = _with_config_truth(json.load(f))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to read config file (may be being written): {e}")
                config = None
        
        # Check if generating (determined by state.json)
        is_generating = False
        generation_stage = None
        config_generated = False
        
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    config_generated = state_data.get("config_generated", False)
                    
                    # Determine current stage
                    if is_generating:
                        if state_data.get("profiles_generated", False):
                            generation_stage = "generating_config"
                        else:
                            generation_stage = "generating_profiles"
                    elif status == "ready":
                        generation_stage = "completed"
            except Exception:
                pass
        
        # Build return data
        response_data = {
            "simulation_id": simulation_id,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "is_generating": is_generating,
            "generation_stage": generation_stage,
            "config_generated": config_generated,
            "config": config
        }
        
        # If config exists, extract key stats
        if config:
            response_data["summary"] = {
                "total_agents": len(config.get("agent_configs", [])),
                "simulation_hours": config.get("time_config", {}).get("total_simulation_hours"),
                "initial_posts_count": len(config.get("bootstrap_posts", config.get("event_config", {}).get("initial_posts", []))),
                "hot_topics_count": len(config.get("event_config", {}).get("hot_topics", [])),
                "has_twitter_config": "twitter_config" in config,
                "has_reddit_config": "reddit_config" in config,
                "has_context_profile": "context_profile" in config,
                "generated_at": config.get("generated_at"),
                "llm_model": config.get("llm_model")
            }
        
        return jsonify({
            "success": True,
            "data": response_data,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get Config real-time: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config', methods=['GET'])
def get_simulation_config(simulation_id: str):
    """
    Get simulation configuration (full configuration intelligently generated by LLM)
    
    Includes:
        - time_config: Time configuration (simulation duration, rounds, peak/off-peak periods)
        - agent_configs: Activity configuration for each Agent (activity level, posting frequency, stance, etc.)
        - event_config: Event configuration (initial posts, hot topics)
        - platform_configs: Platform configuration
        - generation_reasoning: LLM reasoning for configuration
    """
    try:
        manager = SimulationManager()
        config = manager.get_simulation_config(simulation_id)
        
        if not config:
            return jsonify({
                "success": False,
                "error": f"Simulation configuration does not exist, please call /prepare interface first"
            }), 404
        
        return jsonify({
            "success": True,
            "data": _with_config_truth(config),
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/observations/search', methods=['GET'])
def search_simulation_observations(simulation_id: str):
    try:
        sim_dir = _safe_sim_dir(simulation_id)
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        result = search_observations(
            simulation_dir=sim_dir,
            query=request.args.get('q', ''),
            platform=request.args.get('platform'),
            agent_id=request.args.get('agent_id', type=int),
            limit=request.args.get('limit', 50, type=int),
        )
        result = dict(result)
        result["results"] = _with_activity_truth(result.get("results", []))
        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
    except Exception as e:
        logger.error(f"Failed to search observations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Profile Generation Interface (standalone) ==============


# ============== Simulation Run Control Interface ==============


@simulation_bp.route('/<simulation_id>/run-patterns', methods=['GET'])
@simulation_bp.route('/<simulation_id>/metrics', methods=['GET'])
def get_simulation_metrics(simulation_id: str):
    """
    Get descriptive calculations over generated activity in one run.

    Returns 200 with success=False and error="simulation_not_complete" if simulation is still running.
    Accepts ?force=true to recompute even if cached metrics.json exists.
    """
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation does not exist: {simulation_id}"}), 404

        run_state = SimulationRunner.get_run_state(simulation_id)
        if run_state and run_state.runner_status in (RunnerStatus.RUNNING, RunnerStatus.STARTING):
            return jsonify({
                "success": False,
                "error": "simulation_not_complete",
                "status": run_state.runner_status.value,
            })

        force = request.args.get('force', 'false').lower() == 'true'

        from ..services.validation_engine import ValidationEngine
        engine = ValidationEngine()
        metrics = engine.compute_metrics(simulation_id, force=force)
        return jsonify({
            "success": True,
            "data": metrics.to_dict(),
            "disclosure": synthetic_output_disclosure(),
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        logger.error(f"Failed to compute simulation metrics: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/compare', methods=['GET'])
def compare_simulations_route():
    """
    Compare two simulation runs side-by-side and return delta matrix.
    Query parameters:
        sim_a: Simulation ID A (required)
        sim_b: Simulation ID B (required)
        force: Whether to force recomputation (default false)
    """
    try:
        sim_a = request.args.get('sim_a')
        sim_b = request.args.get('sim_b')
        if not sim_a or not sim_b:
            return jsonify({"success": False, "error": "Please provide both sim_a and sim_b query parameters"}), 400

        sim_a_clean = secure_filename(sim_a)
        sim_b_clean = secure_filename(sim_b)

        force = request.args.get('force', 'false').lower() == 'true'

        from ..services.validation_engine import ValidationEngine
        engine = ValidationEngine()
        result = engine.compare_simulations(sim_a_clean, sim_b_clean, force=force)

        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to compare simulations {sim_a} vs {sim_b}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== Real-time status monitoring interface ==============


@simulation_bp.route('/<simulation_id>/run-status/detail', methods=['GET'])
def get_run_status_detail(simulation_id: str):
    """
    Get simulation run detailed status (contains all actions)
    
    Used for frontend display of real-time dynamics
    
    Query parameters:
        platform: Filter platform (twitter/reddit, optional)
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                ...
                "all_actions": [
                    {
                        "round_num": 5,
                        "timestamp": "2025-12-01T10:30:00",
                        "platform": "twitter",
                        "agent_id": 3,
                        "agent_name": "Agent Name",
                        "action_type": "CREATE_POST",
                        "action_args": {"content": "..."},
                        "result": null,
                        "success": true
                    },
                    ...
                ],
                "twitter_actions": [...],  # All actions for Twitter platform
                "reddit_actions": [...]    # All actions for Reddit platform
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        platform_filter = request.args.get('platform')
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "all_actions": [],
                    "twitter_actions": [],
                    "reddit_actions": []
                },
                "disclosure": synthetic_output_disclosure(),
            })
        
        # Get complete action list
        all_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter
        )
        
        # Get actions by platform
        twitter_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="twitter"
        ) if not platform_filter or platform_filter == "twitter" else []
        
        reddit_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="reddit"
        ) if not platform_filter or platform_filter == "reddit" else []
        
        # Get actions for current round (recent_actions only shows the latest round)
        current_round = run_state.current_round
        recent_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter,
            round_num=current_round
        ) if current_round > 0 else []
        
        # Get basic status information
        result = run_state.to_dict()
        result["all_actions"] = _with_activity_truth(
            [a.to_dict() for a in all_actions]
        )
        result["twitter_actions"] = _with_activity_truth(
            [a.to_dict() for a in twitter_actions]
        )
        result["reddit_actions"] = _with_activity_truth(
            [a.to_dict() for a in reddit_actions]
        )
        result["rounds_count"] = len(run_state.rounds)
        # recent_actions only shows content from both platforms for the latest round
        result["recent_actions"] = _with_activity_truth(
            [a.to_dict() for a in recent_actions]
        )
        
        return jsonify({
            "success": True,
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Get detailed status failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/actions', methods=['GET'])
def get_simulation_actions(simulation_id: str):
    """
    Get Agent action history in simulation
    
    Query parameters:
        limit: Return quantity (default 100)
        offset: Offset (default 0)
        platform: Filter platform (twitter/reddit)
        agent_id: Filter Agent ID
        round_num: Filter round
    
    Returns:
        {
            "success": true,
            "data": {
                "count": 100,
                "actions": [...]
            }
        }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        platform = request.args.get('platform')
        agent_id = request.args.get('agent_id', type=int)
        round_num = request.args.get('round_num', type=int)
        include_followers = request.args.get('include_followers', 'true').lower() == 'true'

        actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num,
            include_followers=include_followers,
        )
        actions = actions[offset:offset + limit]
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(actions),
                "actions": _with_activity_truth(
                    [a.to_dict() for a in actions]
                )
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Get action history failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/timeline', methods=['GET'])
def get_simulation_timeline(simulation_id: str):
    """
    Get simulation timeline (summarized by rounds)
    
    Used for frontend display of progress bars and timeline views
    
    Query parameters:
        start_round: starting round (default 0)
        end_round: ending round (default all)
    
    Returns summary information for each round
    """
    try:
        start_round = request.args.get('start_round', 0, type=int)
        end_round = request.args.get('end_round', type=int)
        
        timeline = SimulationRunner.get_timeline(
            simulation_id=simulation_id,
            start_round=start_round,
            end_round=end_round
        )
        
        return jsonify({
            "success": True,
            "data": {
                "rounds_count": len(timeline),
                "timeline": _with_activity_truth(timeline)
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Get timeline failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/agent-stats', methods=['GET'])
def get_agent_stats(simulation_id: str):
    """
    Get statistics for each Agent
    
    Used for frontend display of Agent activity ranking, action distribution, etc.
    """
    try:
        stats = SimulationRunner.get_agent_stats(simulation_id)
        
        return jsonify({
            "success": True,
            "data": {
                "agents_count": len(stats),
                "stats": _with_activity_truth(stats)
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get Agent statistics: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Database Query Interface ==============

@simulation_bp.route('/<simulation_id>/posts', methods=['GET'])
def get_simulation_posts(simulation_id: str):
    """
    Get posts in the simulation

    Query parameters:
        platform: platform type (twitter/reddit)
        limit: return count (default 50)
        offset: offset

    Returns post list (read from SQLite database)
    """
    try:
        # P0 path-escape fix (audit §5 P0). Parse the platform as a strict
        # enum and resolve to a fixed filename. Never interpolate request
        # text into a path.
        platform_param = request.args.get('platform', 'reddit')
        if platform_param not in ALLOWED_PLATFORMS:
            return jsonify({
                "success": False,
                "error": "invalid_platform",
                "allowed": sorted(ALLOWED_PLATFORMS.keys()),
            }), 422
        platform = platform_param

        # P1 input bounding (audit §5 P1). Bounded int parsing via the
        # request parser + manual clamps as a second line of defense.
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "invalid_limit_or_offset",
            }), 422
        if limit < 0 or offset < 0 or limit > 500:
            return jsonify({
                "success": False,
                "error": "limit_out_of_range",
                "limit_max": 500,
            }), 422

        sim_dir = _safe_sim_dir(simulation_id)

        # Fixed allowlist, not interpolation.
        db_file = ALLOWED_PLATFORMS[platform]
        db_path = os.path.join(sim_dir, db_file)

        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "platform": platform,
                    "count": 0,
                    "posts": [],
                    "message": "Database does not exist, simulation may not have run yet"
                },
                "disclosure": synthetic_output_disclosure(),
            })

        import sqlite3
        # Read-only mode, bounded busy timeout. Distinguishes missing
        # table, locked database, corrupt database, and query timeout
        # (audit §5 P0 required correction).
        db_uri = f"file:{db_path}?mode=ro"
        try:
            conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "unable to open" in msg or "no such file" in msg:
                return jsonify({
                    "success": True,
                    "data": {
                        "platform": platform,
                        "count": 0,
                        "posts": [],
                        "message": "Database does not exist, simulation may not have run yet"
                    },
                    "disclosure": synthetic_output_disclosure(),
                })
            if "database disk image is malformed" in msg:
                logger.error("Posts sqlite is corrupt: %s", db_path)
                return jsonify({"success": False, "error": "database_corrupt"}), 500
            return jsonify({
                "success": False,
                "error": "database_unavailable",
                "detail": str(exc),
            }), 500
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            try:
                cursor.execute("""
                    SELECT * FROM post
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                posts = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT COUNT(*) FROM post")
                total = cursor.fetchone()[0]
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if "no such table" in msg:
                    # Missing table is not an error; the simulation may
                    # not have produced any posts yet.
                    posts = []
                    total = 0
                elif "database is locked" in msg:
                    conn.close()
                    return jsonify({"success": False, "error": "database_locked"}), 423
                elif "database disk image is malformed" in msg:
                    conn.close()
                    return jsonify({"success": False, "error": "database_corrupt"}), 500
                else:
                    conn.close()
                    return jsonify({
                        "success": False,
                        "error": "database_query_failed",
                        "detail": str(exc),
                    }), 500
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "total": total,
                "count": len(posts),
                "posts": _with_activity_truth(posts)
            },
            "disclosure": synthetic_output_disclosure(),
        })

    except SafePathError:
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Get posts failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/comments', methods=['GET'])
def get_simulation_comments(simulation_id: str):
    """
    Get comments in simulation (Reddit only)
    
    Query parameters:
        post_id: Filter post ID (optional)
        limit: Return quantity
        offset: Offset
    """
    try:
        post_id = request.args.get('post_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        sim_dir = _safe_sim_dir(simulation_id)

        db_path = os.path.join(sim_dir, "reddit_simulation.db")
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "count": 0,
                    "comments": []
                },
                "disclosure": synthetic_output_disclosure(),
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if post_id:
                cursor.execute("""
                    SELECT * FROM comment 
                    WHERE post_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (post_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM comment 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            comments = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError:
            comments = []
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(comments),
                "comments": _with_activity_truth(comments)
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except SafePathError:
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Get comments failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Generated Profile Follow-up Interface ==============


@simulation_bp.route('/<simulation_id>/generated-interactions', methods=['GET'])
@simulation_bp.route('/<simulation_id>/opinions', methods=['GET'])
def get_simulation_opinions(simulation_id: str):
    """
    Get generated interaction records saved by the legacy opinions scorer.

    Query parameters:
        limit: Maximum number of records to return (default 1000, most recent)
    """
    try:
        limit = int(request.args.get('limit', 1000))
        sim_dir = _safe_sim_dir(simulation_id)
        opinion_file = os.path.join(sim_dir, 'opinions.jsonl')

        opinions = []
        if os.path.exists(opinion_file):
            with open(opinion_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            opinions.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        if len(opinions) > limit:
            opinions = opinions[-limit:]

        return jsonify({
            "success": True,
            "data": {
                "opinions": opinions
            },
            "disclosure": synthetic_output_disclosure(),
        })

    except Exception as e:
        logger.error(f"Failed to get opinions for {simulation_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
