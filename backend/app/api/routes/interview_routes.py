"""
Simulation API Routes
Step 2: Zep Entity Reading & Filtering, OASIS Simulation Preparation & Running (Fully Automated)
"""

import traceback
from flask import request, jsonify

from .. import simulation_bp
from ..simulation import optimize_interview_prompt
from .. import limiter
from ...config import Config
from ...services.simulation_runner import SimulationRunner
from ...services.claim_boundary import synthetic_output_disclosure
from ...utils.logger import get_logger
from ...utils.input_policy import (
    INTERVIEW_BATCH_MAX,
    INTERVIEW_PROMPT_MAX,
    InputPolicyError,
    bounded_integer,
    bounded_text,
    validate_item_count,
)

logger = get_logger('askthepeople.api.simulation')



# P0 path-escape fix (audit §5 P0). The platform identifier is a request-
# controlled value; it MUST be parsed as a strict enum and resolved to a
# fixed filename. Do NOT interpolate request text into a filename.
ALLOWED_PLATFORMS = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}



@simulation_bp.route('/generated-response', methods=['POST'])
@simulation_bp.route('/interview', methods=['POST'])
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

@simulation_bp.route('/generated-response/batch', methods=['POST'])
@simulation_bp.route('/interview/batch', methods=['POST'])
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

@simulation_bp.route('/generated-response/all', methods=['POST'])
@simulation_bp.route('/interview/all', methods=['POST'])
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

@simulation_bp.route('/generated-response/history', methods=['POST'])
@simulation_bp.route('/interview/history', methods=['POST'])
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
