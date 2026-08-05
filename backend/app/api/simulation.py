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
from datetime import datetime

from . import simulation_bp
from ..config import Config
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner
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


# All read-only query routes (history, profiles, config, observations, metrics,
# compare, run-status/detail, actions, timeline, agent-stats, posts, comments,
# opinions, and the list/get-status handlers above) now live in
# `api/routes/read_routes.py`. They are registered through the same
# `simulation_bp` and import the helpers in this module (`_safe_sim_dir`,
# `_with_*_truth`, `_enrich_simulation_summary`, `_get_report_summary_for_*`).
# The platform allowlist they validate against lives in
# `services/simulation_activity_reader.py` (the data layer). Edit the
# read_routes module for any read-route change.
