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

from . import simulation_bp
from . import limiter
from ..config import Config
from ..services.zep_entity_reader import ZepEntityReader
from ..services.oasis_profile_generator import OasisProfileGenerator
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_observation_store import search_observations
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..services.export_service import CSVExporter
from ..services.claim_boundary import (
    fictional_profile_disclosure,
    graph_record_disclosure,
    synthetic_activity_disclosure,
    synthetic_config_disclosure,
    synthetic_output_disclosure,
)
from ..services.zep_tools import ZepToolsService
from ..utils.logger import get_logger
from ..utils.response import truth_metadata
from ..utils.input_policy import (
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
from ..models.project import ProjectManager

logger = get_logger('askthepeople.api.simulation')

from ..utils.safe_path import safe_join, SafePathError


# Base directory for simulation run-state data, computed once. Used as the
# safe_join base for all user-supplied simulation_id values flowing into
# filesystem/sqlite paths (path-traversal defense).
_RUN_STATE_BASE = os.path.abspath(
    getattr(Config, 'OASIS_SIMULATION_DATA_DIR', os.path.join(os.path.dirname(__file__), '../../uploads/simulations'))
)


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

# MOVED TO routes/entity_routes.py
# @simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """
    Get all entities in the graph (filtered)
    
    Only return nodes matching predefined entity types (nodes with labels other than just 'Entity')
    
    Query parameters:
        entity_types: Comma-separated list of entity types (optional, for further filtering)
        enrich: Whether to retrieve related edge info (default true)
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is not configured"
            }), 500
        
        entity_types_str = request.args.get('entity_types', '')
        entity_types = [t.strip() for t in entity_types_str.split(',') if t.strip()] if entity_types_str else None
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        logger.info(f"Get graph entities: graph_id={graph_id}, entity_types={entity_types}, enrich={enrich}")
        
        reader = ZepEntityReader()
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=enrich
        )
        
        payload = result.to_dict()
        payload.update(graph_record_disclosure())
        return jsonify({
            "success": True,
            "data": payload,
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })
        
    except Exception as e:
        logger.error(f"Failed to get graph entities: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/entity_routes.py
# @simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """Get detailed information for a single entity"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is not configured"
            }), 500
        
        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(graph_id, entity_uuid)
        
        if not entity:
            return jsonify({
                "success": False,
                "error": f"Entity does not exist: {entity_uuid}"
            }), 404
        
        payload = entity.to_dict()
        payload.update(graph_record_disclosure())
        return jsonify({
            "success": True,
            "data": payload,
            "disclosure": synthetic_output_disclosure(),
            **truth_metadata()
        })
        
    except Exception as e:
        logger.error(f"Failed to get entity details: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/entity_routes.py
# @simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """Get all entities of a specified type"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is not configured"
            }), 500
        
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(
            graph_id=graph_id,
            entity_type=entity_type,
            enrich_with_edges=enrich
        )
        
        payload = {
            "entity_type": entity_type,
            "count": len(entities),
            "entities": [e.to_dict() for e in entities],
        }
        payload.update(graph_record_disclosure())
        return jsonify({
            "success": True,
            "data": payload,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to get entities: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Simulation Management Interfaces ==============

# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/create', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_MEDIUM)
def create_simulation():
    """
    Create new simulation
    
    Note: Parameters like max_rounds are intelligently generated by LLM, no manual setting needed
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",      // Required
            "graph_id": "atp_xxxx",    // Optional, retrieved from project if not provided
            "enable_twitter": true,          // Optional, default true
            "enable_reddit": true            // Optional, default true
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "project_id": "proj_xxxx",
                "graph_id": "atp_xxxx",
                "status": "created",
                "enable_twitter": true,
                "enable_reddit": true,
                "created_at": "2025-12-01T10:00:00"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        project_id = data.get('project_id')
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400
        
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {project_id}"
            }), 404
        
        graph_id = data.get('graph_id') or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "Graph not yet built for the project, please call /api/graph/build first"
            }), 400
        
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=data.get('enable_twitter', True),
            enable_reddit=data.get('enable_reddit', True),
        )
        
        return jsonify({
            "success": True,
            "data": state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to create simulation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


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


# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/prepare', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def prepare_simulation():
    """
    Prepare simulation environment (asynchronous task, LLM intelligently generates all parameters)
    
    This is a time-consuming operation, the interface will immediately return task_id,
    Use GET /api/simulation/prepare/status to query progress
    
    Features:
    - Automatically detect completed preparation to avoid duplicate generation
    - If already prepared, return existing results directly
    - Support force regeneration (force_regenerate=true)
    
    Steps:
    1. Check for existing completed preparation work
    2. Read and filter entities from Zep graph
    3. Generate OASIS Agent Profile for each entity (with retry mechanism)
    4. LLM intelligently generates simulation configuration (with retry mechanism)
    5. Save configuration files and preset scripts
    
    Request (JSON):
        {
            "simulation_id": "sim_xxxx",                   // Required, Simulation ID
            "entity_types": ["Student", "PublicFigure"],  // Optional, specify entity types
            "use_llm_for_profiles": true,                 // Optional, whether to use LLM for generating personas
            "parallel_profile_count": 5,                  // Optional, number of parallel persona generations, default 5
            "force_regenerate": false                     // Optional, force regeneration, default false
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",           // Returned for new task
                "status": "preparing|ready",
                "message": "Preparation task started|Existing preparation work found",
                "already_prepared": true|false    // Whether preparation is complete
            }
        }
    """
    import os
    from ..models.task import TaskManager
    from ..config import Config
    
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400

        try:
            prepare_controls = _validate_prepare_controls(data)
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation does not exist: {simulation_id}"
            }), 404
        
        # Check if force regenerate
        force_regenerate = prepare_controls["force_regenerate"]
        logger.info(f"Start processing /prepare request: simulation_id={simulation_id}, force_regenerate={force_regenerate}")
        
        # Check if already prepared (avoid duplicate generation)
        if not force_regenerate:
            logger.debug(f"Checking if simulation {simulation_id} is prepared...")
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            logger.debug(f"Check result: is_prepared={is_prepared}, prepare_info={prepare_info}")
            if is_prepared:
                logger.info(f"Simulation {simulation_id} Preparation complete, skipping duplicate generation")
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "message": "Existing preparation work found, no need to regenerate",
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
            else:
                logger.info(f"Simulation {simulation_id} Preparation not complete, starting preparation task")
        
        # Get required info from project
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {state.project_id}"
            }), 404
        
        # Get simulation requirements
        simulation_requirement = project.simulation_requirement or ""
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Project missing simulation requirement description (simulation_requirement)"
            }), 400
        
        # Get document text
        document_text = ProjectManager.get_extracted_text(state.project_id) or ""
        
        entity_types_list = prepare_controls["entity_types"]
        use_llm_for_profiles = prepare_controls["use_llm_for_profiles"]
        parallel_profile_count = prepare_controls["parallel_profile_count"]
        use_archetypes = prepare_controls["use_archetypes"]
        archetype_count = prepare_controls["archetype_count"]
        expansion_factor = prepare_controls["expansion_factor"]
        
        # ========== Synchronously get entity count (before background task start) ==========
        # This allows the frontend to get the expected total Agent count immediately after calling prepare
        try:
            logger.info(f"Synchronously get entity count: graph_id={state.graph_id}")
            reader = ZepEntityReader()
            # Fast read entities (count only, no edge info needed)
            filtered_preview = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=entity_types_list,
                enrich_with_edges=False  # Speed up by not retrieving edge info
            )
            if filtered_preview.filtered_count > PREPARE_ENTITY_MAX:
                return jsonify({
                    "success": False,
                    "error": "entity_count_out_of_range",
                    "message": (
                        "The selected graph contains "
                        f"{filtered_preview.filtered_count} profile entities; "
                        f"the maximum is {PREPARE_ENTITY_MAX}."
                    ),
                }), 400
            # Save entity count to state (for immediate frontend retrieval)
            state.entities_count = filtered_preview.filtered_count
            state.entity_types = list(filtered_preview.entity_types)
            logger.info(f"Expected entity count: {filtered_preview.filtered_count}, types: {filtered_preview.entity_types}")
        except Exception as e:
            logger.warning(f"Failed to synchronously get entity count (will retry in background task): {e}")
            # Failure does not affect subsequent steps as the background task will retry
        
        # Create background task
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_prepare",
            metadata={
                "simulation_id": simulation_id,
                "project_id": state.project_id
            }
        )
        
        # Update simulation state (including pre-fetched entity count)
        state.status = SimulationStatus.PREPARING
        manager._save_simulation_state(state)

        # P0 daemon-thread fix (audit §5 P0). The route enqueues work to
        # a Celery worker and returns 202 Accepted. The route no longer
        # creates a `threading.Thread(..., daemon=True)`; the work
        # runs in a worker process that can survive a web restart.
        # Full durable workflow (idempotency keys, leases, fencing
        # tokens, heartbeats, cancellation, retry classification)
        # lands with gate 2 in adr/ADR-0003-durable-run-orchestration.md.
        from ..tasks.simulation_tasks import prepare_simulation_task

        prepare_simulation_task.delay(
            simulation_id=simulation_id,
            task_id=task_id,
            entity_types=entity_types_list,
            use_llm_for_profiles=use_llm_for_profiles,
            parallel_profile_count=parallel_profile_count,
            use_archetypes=use_archetypes,
            archetype_count=archetype_count,
            expansion_factor=expansion_factor,
            document_text=document_text,
        )

        response = jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "task_id": task_id,
                "status": "preparing",
                "message": "Preparation task enqueued. Poll /api/simulation/prepare/status for progress.",
                "already_prepared": False,
                "expected_entities_count": state.entities_count,  # Expected total Agents
                "entity_types": state.entity_types  # Entity types list
            }
        })
        return response, 202, {"Location": f"/api/jobs/{task_id}"}
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Failed to start preparation task: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/prepare/status', methods=['POST'])
def get_prepare_status():
    """
    Query preparation task progress
    
    Supports two query methods:
    1. Query progress of an ongoing task via task_id
    2. Check for completed preparation work via simulation_id
    
    Request (JSON):
        {
            "task_id": "task_xxxx",          // Optional, task_id returned by prepare
            "simulation_id": "sim_xxxx"      // Optional, simulation ID (for checking completed preparation)
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|ready",
                "progress": 45,
                "message": "...",
                "already_prepared": true|false,  // Whether preparation is complete
                "prepare_info": {...}            // Detailed information when preparation is complete
            }
        }
    """
    from ..models.task import TaskManager
    
    try:
        data = request.get_json() or {}
        
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        # If simulation_id is provided, check if already prepared
        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "progress": 100,
                        "message": "Existing preparation work found",
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
        
        # If no task_id, return error
        if not task_id:
            if simulation_id:
                # With simulation_id but not prepared yet
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "not_started",
                        "progress": 0,
                        "message": "Preparation not started, please call /api/simulation/prepare to start",
                        "already_prepared": False
                    }
                })
            return jsonify({
                "success": False,
                "error": "Please provide task_id or simulation_id"
            }), 400
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            # Task does not exist, but if simulation_id is provided, check for completed preparation
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    return jsonify({
                        "success": True,
                        "data": {
                            "simulation_id": simulation_id,
                            "task_id": task_id,
                            "status": "ready",
                            "progress": 100,
                            "message": "Task completed (preparation work already exists)",
                            "already_prepared": True,
                            "prepare_info": prepare_info
                        }
                    })
            
            return jsonify({
                "success": False,
                "error": f"Task does not exist: {task_id}"
            }), 404
        
        task_dict = task.to_public_dict()
        task_dict["already_prepared"] = False
        
        return jsonify({
            "success": True,
            "data": task_dict
        })
        
    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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


def _get_report_id_for_simulation(simulation_id: str):
    """Return the latest report ID for backwards-compatible callers."""
    summary = _get_report_summary_for_simulation(simulation_id)
    return summary.get("report_id") if summary else None


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


# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/<simulation_id>/preflight', methods=['GET'])
def get_simulation_preflight(simulation_id: str):
    try:
        manager = SimulationManager()
        preflight = manager.get_preflight(simulation_id)
        if not preflight:
            return jsonify({
                "success": False,
                "error": "preflight.json does not exist, please complete /prepare first"
            }), 404
        return jsonify({
            "success": True,
            "data": preflight
        })
    except Exception as e:
        logger.error(f"Failed to get preflight: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/<simulation_id>/diagnostics', methods=['GET'])
def get_simulation_diagnostics(simulation_id: str):
    try:
        manager = SimulationManager()
        diagnostics = manager.get_diagnostics(simulation_id)
        return jsonify({
            "success": True,
            "data": diagnostics
        })
    except Exception as e:
        logger.error(f"Failed to get diagnostics: {str(e)}")
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


# MOVED TO routes/export_routes.py
# @simulation_bp.route('/<simulation_id>/config/download', methods=['GET'])
def download_simulation_config(simulation_id: str):
    """Download simulation configuration file"""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return jsonify({
                "success": False,
                "error": "Configuration file does not exist, please call /prepare interface first"
            }), 404
        
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = _with_config_truth(json.load(handle))
        payload = io.BytesIO(
            json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
        )
        payload.seek(0)

        return send_file(
            payload,
            mimetype="application/json",
            as_attachment=True,
            download_name="simulation_config.json"
        )

    except SafePathError:
        return jsonify({"success": False, "error": "invalid_id"}), 400
    except Exception as e:
        logger.error(f"Failed to download configuration: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/export_routes.py
# @simulation_bp.route('/script/<script_name>/download', methods=['GET'])
def download_simulation_script(script_name: str):
    """
    Download simulation run script file (generic script, located in backend/scripts/)
    
    script_name options:
        - run_twitter_simulation.py
        - run_reddit_simulation.py
        - run_parallel_simulation.py
        - action_logger.py
    """
    try:
        # Scripts are located in backend/scripts/ directory
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        # Validate script name
        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py", 
            "run_parallel_simulation.py",
            "action_logger.py"
        ]
        
        if script_name not in allowed_scripts:
            return jsonify({
                "success": False,
                "error": f"Unknown script: {script_name}, available options: {allowed_scripts}"
            }), 400
        
        script_path = os.path.join(scripts_dir, script_name)
        
        if not os.path.exists(script_path):
            return jsonify({
                "success": False,
                "error": f"Script file does not exist: {script_name}"
            }), 404
        
        return send_file(
            script_path,
            as_attachment=True,
            download_name=script_name
        )
        
    except Exception as e:
        logger.error(f"Failed to download script: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Profile Generation Interface (standalone) ==============

# MOVED TO routes/prep_routes.py
# @simulation_bp.route('/generate-profiles', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_MEDIUM)
def generate_profiles():
    """
    Generate OASIS Agent Profile directly from graph (without creating simulation)
    
    Request (JSON):
        {
            "graph_id": "atp_xxxx",           // Required
            "entity_types": ["Student"],      // Optional
            "use_llm": true,                  // Optional
            "platform": "reddit"              // Optional
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
        
        entity_types = data.get('entity_types')
        use_llm = data.get('use_llm', True)
        platform = data.get('platform', 'reddit')
        
        reader = ZepEntityReader()
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True
        )
        
        if filtered.filtered_count == 0:
            return jsonify({
                "success": False,
                "error": "No matching entities found"
            }), 400
        
        generator = OasisProfileGenerator()
        profiles = generator.generate_profiles_from_entities(
            entities=filtered.entities,
            use_llm=use_llm
        )
        
        if platform == "reddit":
            profiles_data = [p.to_reddit_format() for p in profiles]
        elif platform == "twitter":
            profiles_data = [p.to_twitter_format() for p in profiles]
        else:
            profiles_data = [p.to_dict() for p in profiles]
        profiles_data = _with_profile_truth(profiles_data)
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "entity_types": list(filtered.entity_types),
                "count": len(profiles_data),
                "profiles": profiles_data,
                **fictional_profile_disclosure(),
            },
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as e:
        logger.error(f"Failed to generate profile: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Simulation Run Control Interface ==============

# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/start', methods=['POST'])
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
        from ..models.task import TaskManager, TaskStatus
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
            from ..tasks.simulation_tasks import run_simulation_task
            async_res = run_simulation_task.delay(
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
            if async_res and getattr(async_res, 'id', None) and not task_id:
                task_id = async_res.id
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


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/<simulation_id>/inject', methods=['POST'])
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
            from ..services.simulation_observation_store import push_in_memory_event
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


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/stop', methods=['POST'])
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


# ============== Real-time status monitoring interface ==============

# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/<simulation_id>/run-status', methods=['GET'])
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


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/<simulation_id>/status', methods=['GET'])
def get_simulation_status(simulation_id: str):
    """
    Get simulation execution status from the process-local task and run state.
    """
    from ..models.task import TaskManager
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


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id: str):
    """
    Get task status from the process-local task manager.
    """
    from ..models.task import TaskManager
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

# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/generated-response', methods=['POST'])
# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/interview', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def interview_agent():
    """
    Ask one fictional generated profile a follow-up question.

    The legacy ``/interview`` path remains for compatibility. The returned text
    is another model output, not a human interview, testimony, or prediction.

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",       // Required, simulation ID
            "agent_id": 0,                     // Required, Agent ID
            "prompt": "What do you think about this?",  // Required, interview question
            "platform": "twitter",             // Optional, specify platform (twitter/reddit)
                                               // If not specified: Dual-platform simulation interviews both platforms simultaneously
            "timeout": 60                      // Optional, timeout in seconds, default 60
        }

    Returns (if platform not specified, dual-platform mode):
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "What do you think about this?",
                "result": {
                    "agent_id": 0,
                    "prompt": "...",
                    "platforms": {
                        "twitter": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit": {"agent_id": 0, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }

    Returns (if platform specified):
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "What do you think about this?",
                "result": {
                    "agent_id": 0,
                    "response": "I think...",
                    "platform": "twitter",
                    "timestamp": "2025-12-08T10:00:00"
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        agent_id = data.get('agent_id')
        platform = data.get('platform')  # Optional: twitter/reddit/None
        try:
            prompt = bounded_text(
                data.get('prompt'),
                field="prompt",
                max_length=INTERVIEW_PROMPT_MAX,
                required=True,
            )
            timeout = bounded_integer(
                data.get('timeout', 60),
                field="timeout",
                minimum=1,
                maximum=300,
            )
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
        
        if agent_id is None:
            return jsonify({
                "success": False,
                "error": "Please provide agent_id"
            }), 400
        
        # Validate platform parameter
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "The platform parameter can only be 'twitter' or 'reddit'"
            }), 400
        
        # Check environment status
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running or closed. Please ensure simulation is Completed and in waiting command mode."
            }), 400
        
        # Optimize prompt, add prefix to avoid Agent calling tools
        raw = Config.DEBUG and (
            data.get('raw', False)
            or data.get('bypass_prompt_optimization', False)
        )
        optimized_prompt = optimize_interview_prompt(prompt, bypass=raw)
        
        result = SimulationRunner.interview_agent(
            simulation_id=simulation_id,
            agent_id=agent_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Timeout waiting for generated profile response: {str(e)}"
        }), 504
        
    except Exception as e:
        logger.error(f"Generated profile follow-up failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/generated-response/batch', methods=['POST'])
# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/interview/batch', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def interview_agents_batch():
    """
    Ask multiple fictional generated profiles follow-up questions.

    The legacy ``/interview/batch`` path remains for compatibility. Every
    returned answer is synthetic and has zero human respondents.

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",       // Required, simulation ID
            "questions": [                     // Required, generated-profile questions
                {
                    "agent_id": 0,
                    "prompt": "What concern might this profile raise?",
                    "platform": "twitter"      // Optional fictional channel
                },
                {
                    "agent_id": 1,
                    "prompt": "What assumption should be tested?"
                }
            ],
            "platform": "reddit",              // Optional fictional channel
            "timeout": 120                     // Optional, timeout (seconds), default 120
        }

    Returns:
        {
            "success": true,
            "data": {
                "interviews_count": 2,
                "result": {
                    "interviews_count": 4,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        "twitter_1": {"agent_id": 1, "response": "...", "platform": "twitter"},
                        "reddit_1": {"agent_id": 1, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # Optional: twitter/reddit/None
        try:
            questions = validate_item_count(
                data.get('questions') or data.get('interviews') or [],
                field="questions",
                maximum=INTERVIEW_BATCH_MAX,
            )
            timeout = bounded_integer(
                data.get('timeout', 120),
                field="timeout",
                minimum=1,
                maximum=300,
            )
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

        if not questions or not isinstance(questions, list):
            return jsonify({
                "success": False,
                "error": "Please provide questions for generated profiles"
            }), 400

        # Validate platform parameter
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "platform parameter can only be 'twitter' or 'reddit'"
            }), 400

        # Validate each generated-profile question.
        for i, question in enumerate(questions):
            if 'agent_id' not in question:
                return jsonify({
                    "success": False,
                    "error": f"Question item {i+1} missing agent_id"
                }), 400
            if 'prompt' not in question:
                return jsonify({
                    "success": False,
                    "error": f"Question item {i+1} missing prompt"
                }), 400
            try:
                question["prompt"] = bounded_text(
                    question.get("prompt"),
                    field=f"questions[{i}].prompt",
                    max_length=INTERVIEW_PROMPT_MAX,
                    required=True,
                )
            except InputPolicyError as exc:
                return jsonify({
                    "success": False,
                    "error": exc.code,
                    "message": exc.message,
                }), 400
            # Validate platform for each item (if any)
            item_platform = question.get('platform')
            if item_platform and item_platform not in ("twitter", "reddit"):
                return jsonify({
                    "success": False,
                    "error": f"Platform for question item {i+1} can only be 'twitter' or 'reddit'"
                }), 400

        # Check environment status
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running or closed. Please ensure simulation is Completed and in waiting command mode."
            }), 400

        # Add the disclosure prefix and prevent generated profiles from calling tools.
        raw = Config.DEBUG and (
            data.get('raw', False)
            or data.get('bypass_prompt_optimization', False)
        )
        optimized_questions = []
        for question in questions:
            optimized_question = question.copy()
            # Also allow individual item bypass or global bypass
            item_raw = raw or (
                Config.DEBUG
                and (
                    question.get('raw', False)
                    or question.get('bypass_prompt_optimization', False)
                )
            )
            optimized_question['prompt'] = optimize_interview_prompt(
                question.get('prompt', ''),
                bypass=item_raw,
            )
            optimized_questions.append(optimized_question)

        result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=optimized_questions,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Timeout waiting for generated profile responses: {str(e)}"
        }), 504

    except Exception as e:
        logger.error(f"Generated profile batch follow-up failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/generated-response/all', methods=['POST'])
# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/interview/all', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def interview_all_agents():
    """
    Ask every fictional generated profile the same follow-up question.

    The legacy ``/interview/all`` path remains for compatibility. Returned
    answers are model outputs, not a population sample or public opinion.

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",            // Required, simulation ID
            "prompt": "What do you think about this whole thing?",  // Required, interview question (all Agents use the same question)
            "platform": "reddit",                   // Optional, specify platform (twitter/reddit)
                                                    // When not specified: Dual-platform simulation interviews each Agent on both platforms simultaneously
            "timeout": 180                          // Optional, timeout (seconds), default 180
        }

    Returns:
        {
            "success": true,
            "data": {
                "interviews_count": 50,
                "result": {
                    "interviews_count": 100,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        ...
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # Optional: twitter/reddit/None
        try:
            prompt = bounded_text(
                data.get('prompt'),
                field="prompt",
                max_length=INTERVIEW_PROMPT_MAX,
                required=True,
            )
            timeout = bounded_integer(
                data.get('timeout', 180),
                field="timeout",
                minimum=1,
                maximum=300,
            )
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

        # Validate platform parameter
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "platform parameter can only be 'twitter' or 'reddit'"
            }), 400

        # Check environment status
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running or closed. Please ensure simulation is Completed and in waiting command mode."
            }), 400

        # Optimize prompt, add prefix to prevent Agent from calling tools
        raw = Config.DEBUG and (
            data.get('raw', False)
            or data.get('bypass_prompt_optimization', False)
        )
        optimized_prompt = optimize_interview_prompt(prompt, bypass=raw)

        result = SimulationRunner.interview_all_agents(
            simulation_id=simulation_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
            "disclosure": synthetic_output_disclosure(),
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Timeout waiting for generated profile responses: {str(e)}"
        }), 504

    except Exception as e:
        logger.error(f"Generated profile all-follow-up failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/generated-response/history', methods=['POST'])
# MOVED TO routes/interview_routes.py
# @simulation_bp.route('/interview/history', methods=['POST'])
def get_interview_history():
    """
    Get saved fictional generated-profile follow-up records.

    The legacy ``/interview/history`` path remains for compatibility.

    Request (JSON):
        {
            "simulation_id": "sim_xxxx",  // Required, simulation ID
            "platform": "reddit",          // Optional, platform type (reddit/twitter)
                                           // Returns all history for both platforms if not specified
            "agent_id": 0,                 // Optional, only get interview history for this Agent
            "limit": 100                   // Optional, return quantity, default 100
        }

    Returns:
        {
            "success": true,
            "data": {
                "count": 10,
                "history": [
                    {
                        "agent_id": 0,
                        "response": "I think...",
                        "prompt": "What do you think about this thing?",
                        "timestamp": "2025-12-08T10:00:00",
                        "platform": "reddit"
                    },
                    ...
                ]
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # Returns both platforms' history if not specified
        agent_id = data.get('agent_id')
        limit = data.get('limit', 100)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_id"
            }), 400

        history = SimulationRunner.get_interview_history(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": {
                "count": len(history),
                "history": history
            },
            "disclosure": synthetic_output_disclosure(),
        })

    except Exception as e:
        logger.error(f"Failed to get generated profile response history: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/env-status', methods=['POST'])
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


# MOVED TO routes/execution_routes.py
# @simulation_bp.route('/close-env', methods=['POST'])
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


# MOVED TO routes/export_routes.py
# @simulation_bp.route('/<simulation_id>/export/generated-responses', methods=['POST'])
# MOVED TO routes/export_routes.py
# @simulation_bp.route('/<simulation_id>/export/survey', methods=['POST'])
def export_survey_csv(simulation_id: str):
    """
    Export model-generated profile responses as CSV.

    The legacy ``/export/survey`` route remains as a compatibility alias. These
    records are synthetic model outputs, not survey responses from people.
    
    Request (JSON):
        {
            "results": [
                {"agent_name": "...", "profession": "...", "answer": "..."},
                ...
            ]
        }
    """
    try:
        data = request.get_json() or {}
        results = data.get('results', [])
        
        if not results:
            return jsonify({
                "success": False,
                "error": "No results to export"
            }), 400
            
        exporter = CSVExporter(ZepToolsService())
        csv_content = exporter.export_survey_results(results)
        
        # Create bytes stream for file download
        mem = io.BytesIO()
        mem.write(csv_content.encode('utf-8'))
        mem.seek(0)
        
        filename = (
            f"ATP_GENERATED_RESPONSES_{simulation_id}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Failed to export generated-response CSV: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
