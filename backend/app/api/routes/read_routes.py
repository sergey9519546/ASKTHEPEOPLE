"""
Simulation read-only query routes (decomposed from simulation.py).

Gate 1 of the incremental-modernization program (ADR-0011). These are the
read endpoints that remained in the controller after the write/lifecycle
handlers moved out: list/history/profiles/config/observations/metrics/
compare/status/actions/timeline/agent-stats/posts/comments/opinions.

The shared helpers they depend on (`_safe_sim_dir`, `_with_profile_truth`,
`_with_activity_truth`, `_with_config_truth`,
`_enrich_simulation_summary`, `_get_report_summary_for_simulation`,
`ALLOWED_PLATFORMS`) stay in `api/simulation.py` because the write/lifecycle
route modules import them from there too. This module imports them through
that same seam so there is exactly one definition of each.
"""

import json
import os
import traceback
from datetime import datetime

from flask import jsonify, request
from werkzeug.utils import secure_filename

from .. import simulation_bp
from ..simulation import (
    ALLOWED_PLATFORMS,
    _enrich_simulation_summary,
    _get_report_summary_for_simulation,
    _safe_sim_dir,
    _with_activity_truth,
    _with_config_truth,
    _with_profile_truth,
)
from ...config import Config
from ...models.project import ProjectManager
from ...services.claim_boundary import (
    fictional_profile_disclosure,
    synthetic_output_disclosure,
)
from ...services.simulation_manager import SimulationManager, SimulationStatus
from ...services.simulation_observation_store import search_observations
from ...services.simulation_runner import RunnerStatus, SimulationRunner
from ...utils.logger import get_logger
from ...utils.safe_path import SafePathError

logger = get_logger('askthepeople.api.routes.read')


# ============== Simulation status and listing ==============


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


@simulation_bp.route('/history', methods=['GET'])
def get_simulation_history():
    """
    Get historical simulation list (with project details)

    Used for historical project display on the home page, returning a simulation list containing rich information such as project name and description

    Query parameters:
        limit: Return quantity limit (default 20)
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


# ============== Profiles and config ==============


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
    """
    import csv

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
    """
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


# ============== Simulation metrics and comparison ==============


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

        from ...services.validation_engine import ValidationEngine
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

        from ...services.validation_engine import ValidationEngine
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


# ============== Real-time status and activity ==============


@simulation_bp.route('/<simulation_id>/run-status/detail', methods=['GET'])
def get_run_status_detail(simulation_id: str):
    """
    Get simulation run detailed status (contains all actions)

    Used for frontend display of real-time dynamics

    Query parameters:
        platform: Filter platform (twitter/reddit, optional)
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
        include_followers: Whether to include follower actions (default true)
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

    Returns post list (read from the simulation activity database via the
    SimulationActivityReader service).
    """
    from ...services.simulation_activity_reader import (
        DatabaseCorrupt,
        DatabaseLocked,
        DatabaseUnavailable,
        read_posts,
    )

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

        try:
            posts, total = read_posts(sim_dir, platform, limit, offset)
        except DatabaseUnavailable:
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
        except DatabaseLocked:
            return jsonify({"success": False, "error": "database_locked"}), 423
        except DatabaseCorrupt:
            return jsonify({"success": False, "error": "database_corrupt"}), 500

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
    from ...services.simulation_activity_reader import (
        DatabaseCorrupt,
        DatabaseLocked,
        DatabaseUnavailable,
        read_comments,
    )

    try:
        post_id = request.args.get('post_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        sim_dir = _safe_sim_dir(simulation_id)

        try:
            comments = read_comments(sim_dir, limit, offset, post_id=post_id)
        except DatabaseUnavailable:
            comments = []
        except DatabaseLocked:
            return jsonify({"success": False, "error": "database_locked"}), 423
        except DatabaseCorrupt:
            return jsonify({"success": False, "error": "database_corrupt"}), 500

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
