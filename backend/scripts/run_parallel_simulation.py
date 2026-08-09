"""
OASIS Dual-Platform Parallel Simulation Preset Script
Runs Twitter and Reddit simulations simultaneously, reading from the same configuration file.

Features:
- Dual-platform (Twitter + Reddit) parallel simulation
- Enters command-wait mode instead of closing environment immediately after simulation
- Supports receiving Interview commands via IPC
- Supports single Agent interview and batch interviews
- Supports remote environment closure commands

Usage:
    python run_parallel_simulation.py --config simulation_config.json
    python run_parallel_simulation.py --config simulation_config.json --no-wait  # Close immediately after completion
    python run_parallel_simulation.py --config simulation_config.json --twitter-only
    python run_parallel_simulation.py --config simulation_config.json --reddit-only

Log Structure:
    sim_xxx/
    ├── twitter/
    │   └── actions.jsonl    # Twitter platform action logs
    ├── reddit/
    │   └── actions.jsonl    # Reddit platform action logs
    ├── simulation.log       # Main simulation process log
    └── run_state.json       # Running state (for API queries)
"""

# ============================================================
# Resolve Windows encoding issues: set UTF-8 encoding before any imports
# This fixes issues where OASIS third-party libraries read files without specifying encoding
# ============================================================
import sys
import os

if sys.platform == 'win32':
    # Set Python default I/O encoding to UTF-8
    # This affects all open() calls that do not specify an encoding
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    
    # Reconfigure standard output stream to UTF-8 (resolve console garbled characters)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    # Force set default encoding (affects default encoding of open() function)
    # Note: This needs to be set at Python startup, may not take effect if set during runtime
    # So we also need to monkey-patch the built-in open function
    import builtins
    _original_open = builtins.open
    
    def _utf8_open(file, mode='r', buffering=-1, encoding=None, errors=None, 
                   newline=None, closefd=True, opener=None):
        """
        Wrap open() function, default to UTF-8 encoding for text mode
        This fixes issues where third-party libraries (like OASIS) read files without specifying encoding
        """
        # Set default encoding only for text mode (non-binary) where encoding is not specified
        if encoding is None and 'b' not in mode:
            encoding = 'utf-8'
        return _original_open(file, mode, buffering, encoding, errors, 
                              newline, closefd, opener)
    
    builtins.open = _utf8_open

import argparse
import asyncio
import json
import logging
import multiprocessing
import random
import signal
import sqlite3
import warnings
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


# Global variables: used for signal handling
_shutdown_event = None
_cleanup_done = False

# Add backend directory to path
# Script is fixed in backend/scripts/ directory
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

# Load .env file from the project root (contains LLM_API_KEY and other configurations)
from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
    print(f"Loaded environment config: {_env_file}")
else:
    # Try loading backend/.env
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)
        print(f"Loaded environment config: {_backend_env}")


class MaxTokensWarningFilter(logging.Filter):
    """Filter out camel-ai warnings about max_tokens (we deliberately don't set max_tokens, let the model decide)"""
    
    def filter(self, record):
        # Filter out logs containing max_tokens warning
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


# Add filter immediately on module load to ensure it takes effect before camel code execution
logging.getLogger().addFilter(MaxTokensWarningFilter())


def disable_oasis_logging():
    """
    Disable detailed logging from OASIS library
    OASIS logs are too redundant (logging observations and actions for every agent), we use our own action_logger
    """
    # Disable all OASIS loggers
    oasis_loggers = [
        "social.agent",
        "social.twitter", 
        "social.rec",
        "oasis.env",
        "table",
    ]
    
    for logger_name in oasis_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)  # Only log critical errors
        logger.handlers.clear()
        logger.propagate = False


def init_logging_for_simulation(simulation_dir: str):
    """
    Initialize simulation logging configuration
    
    Args:
        simulation_dir: Path to simulation directory
    """
    # Disable detailed OASIS logs
    disable_oasis_logging()
    
    # Clean up old log directory if it exists
    old_log_dir = os.path.join(simulation_dir, "log")
    if os.path.exists(old_log_dir):
        import shutil
        shutil.rmtree(old_log_dir, ignore_errors=True)


from action_logger import SimulationLogManager, PlatformActionLogger
from app.config import Config
from app.services.simulation_limits import resolve_total_rounds
from app.services.simulation_runtime_contract import (
    apply_bootstrap_actions,
    apply_injected_events,
    apply_reflection_round,
    apply_scheduled_events,
    bootstrap_boost_agent_ids,
    build_agent_name_lookup,
    create_actor_model_for_runtime,
    scheduled_event_boost_agent_ids,
    select_active_agent_ids,
)


class RedisEventConsumer:
    """Redis Pub/Sub subscriber for real-time scenario injection events with in-memory fallback."""

    def __init__(
        self,
        simulation_id: str,
        redis_url: Optional[str] = None,
        platform: Optional[str] = None,
    ):
        self.simulation_id = simulation_id
        self.platform = platform
        self.channel_name = f"simulation:{simulation_id}:events"
        self.pubsub = None
        self.redis_client = None
        url = redis_url or getattr(Config, 'REDIS_URL', '')
        try:
            if url and not url.startswith("memory://"):
                import redis
                self.redis_client = redis.from_url(url, socket_timeout=1.0, socket_connect_timeout=1.0, decode_responses=True)
                self.pubsub = self.redis_client.pubsub()
                self.pubsub.subscribe(self.channel_name)
        except Exception:
            pass

    def consume_events(self) -> List[Dict[str, Any]]:
        events = []
        if self.pubsub:
            try:
                while True:
                    msg = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.01)
                    if not msg:
                        break
                    if isinstance(msg, dict) and msg.get("type") == "message":
                        data_str = msg.get("data")
                        if data_str:
                            try:
                                events.append(json.loads(data_str))
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

        try:
            from app.services.simulation_observation_store import pop_in_memory_events
            fallback_events = pop_in_memory_events(
                self.simulation_id, platform=self.platform
            )
            events.extend(fallback_events)
        except Exception:
            pass

        return events

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import (
        ActionType,
        LLMAction,
        ManualAction,
    )
    from app.services.decision_lens_oasis_agent import (
        generate_decision_lens_agent_graph,
        load_decision_lens_runtime_adapters,
    )
    from app.services.instruction_integrity import (
        InstructionIntegrityGuard,
        InstructionIntegrityViolation,
    )
    from app.services.network_topology import apply_network_topology, apply_homophily_rewiring
except ImportError as e:
    print(f"Error: Missing dependency {e}")
    print("Please install: pip install oasis-ai camel-ai")
    sys.exit(1)


# Available Twitter actions (excluding INTERVIEW, which is triggered manually via ManualAction)
TWITTER_ACTIONS = [
    ActionType.CREATE_POST,
    ActionType.LIKE_POST,
    ActionType.REPOST,
    ActionType.FOLLOW,
    ActionType.DO_NOTHING,
    ActionType.QUOTE_POST,
]

# Available Reddit actions (excluding INTERVIEW, which is triggered manually via ManualAction)
REDDIT_ACTIONS = [
    ActionType.LIKE_POST,
    ActionType.DISLIKE_POST,
    ActionType.CREATE_POST,
    ActionType.CREATE_COMMENT,
    ActionType.LIKE_COMMENT,
    ActionType.DISLIKE_COMMENT,
    ActionType.SEARCH_POSTS,
    ActionType.SEARCH_USER,
    ActionType.TREND,
    ActionType.REFRESH,
    ActionType.DO_NOTHING,
    ActionType.FOLLOW,
    ActionType.MUTE,
]


# IPC-related constants
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"

class CommandType:
    """Command type constants"""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


class ParallelIPCHandler:
    """
    Dual-platform IPC command handler
    
    Manages environments for both platforms and processes Interview commands
    """
    
    def __init__(
        self,
        simulation_dir: str,
        twitter_env=None,
        twitter_agent_graph=None,
        twitter_instruction_guard=None,
        reddit_env=None,
        reddit_agent_graph=None,
        reddit_instruction_guard=None,
    ):
        self.simulation_dir = simulation_dir
        self.twitter_env = twitter_env
        self.twitter_agent_graph = twitter_agent_graph
        self.twitter_instruction_guard = twitter_instruction_guard
        self.reddit_env = reddit_env
        self.reddit_agent_graph = reddit_agent_graph
        self.reddit_instruction_guard = reddit_instruction_guard
        
        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)
        
        # Ensure directories exist
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def update_status(self, status: str):
        """Update environment status"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "twitter_available": self.twitter_env is not None,
                "reddit_available": self.reddit_env is not None,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def poll_command(self) -> Optional[Dict[str, Any]]:
        """Poll for pending commands"""
        if not os.path.exists(self.commands_dir):
            return None
        
        # Get command files (sorted by time)
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                command_files.append((filepath, os.path.getmtime(filepath)))
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return None
    
    def send_response(self, command_id: str, status: str, result: Dict = None, error: str = None):
        """Send response"""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        
        # Delete command file
        command_file = os.path.join(
            self.commands_dir, f"{command_id}.json"
        )
        try:
            os.remove(command_file)
        except OSError:
            pass
    
    def _get_env_and_graph(self, platform: str):
        """
        Get environment and agent_graph for the specified platform
        
        Args:
            platform: Platform name ("twitter" or "reddit")
            
        Returns:
            (env, agent_graph, integrity_guard, platform_name), or empty values
        """
        if platform == "twitter" and self.twitter_env:
            return (
                self.twitter_env,
                self.twitter_agent_graph,
                self.twitter_instruction_guard,
                "twitter",
            )
        elif platform == "reddit" and self.reddit_env:
            return (
                self.reddit_env,
                self.reddit_agent_graph,
                self.reddit_instruction_guard,
                "reddit",
            )
        else:
            return None, None, None, None
    
    async def _interview_single_platform(self, agent_id: int, prompt: str, platform: str) -> Dict[str, Any]:
        """
        Execute Interview on a single platform
        
        Returns:
            Dictionary containing the result, or dictionary containing the error
        """
        env, agent_graph, integrity_guard, actual_platform = (
            self._get_env_and_graph(platform)
        )
        
        if not env or not agent_graph:
            return {"platform": platform, "error": f"{platform}platform is unavailable"}
        
        try:
            agent = agent_graph.get_agent(agent_id)
            interview_action = ManualAction(
                action_type=ActionType.INTERVIEW,
                action_args={"prompt": prompt}
            )
            actions = {agent: interview_action}
            await integrity_checked_step(env, integrity_guard, actions)
            
            result = self._get_interview_result(agent_id, actual_platform)
            result["platform"] = actual_platform
            return result
            
        except InstructionIntegrityViolation:
            raise
        except Exception as e:
            return {"platform": platform, "error": str(e)}
    
    async def handle_interview(self, command_id: str, agent_id: int, prompt: str, platform: str = None) -> bool:
        """
        Process single agent interview command
        
        Args:
            command_id: Command ID
            agent_id: Agent ID
            prompt: Interview question
            platform: Specified platform (optional)
                - "twitter": Only interview on Twitter
                - "reddit": Only interview on Reddit
                - None/Not specified: Interview on both platforms and return combined results
            
        Returns:
            True for success, False for failure
        """
        # If platform is specified, only interview on that platform
        if platform in ("twitter", "reddit"):
            result = await self._interview_single_platform(agent_id, prompt, platform)
            
            if "error" in result:
                self.send_response(command_id, "failed", error=result["error"])
                print(f"  Interview failed: agent_id={agent_id}, platform={platform}, error={result['error']}")
                return False
            else:
                self.send_response(command_id, "completed", result=result)
                print(f"  Interview completed: agent_id={agent_id}, platform={platform}")
                return True
        
        # Unspecified platform: interview both simultaneously
        if not self.twitter_env and not self.reddit_env:
            self.send_response(command_id, "failed", error="No available simulation environment")
            return False
        
        results = {
            "agent_id": agent_id,
            "prompt": prompt,
            "platforms": {}
        }
        success_count = 0
        
        # Interview both platforms in parallel
        tasks = []
        platforms_to_interview = []
        
        if self.twitter_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "twitter"))
            platforms_to_interview.append("twitter")
        
        if self.reddit_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "reddit"))
            platforms_to_interview.append("reddit")
        
        # Execute in parallel
        platform_results = await asyncio.gather(*tasks)
        
        for platform_name, platform_result in zip(platforms_to_interview, platform_results):
            results["platforms"][platform_name] = platform_result
            if "error" not in platform_result:
                success_count += 1
        
        if success_count > 0:
            self.send_response(command_id, "completed", result=results)
            print(f"  Interview completed: agent_id={agent_id}, successful platforms={success_count}/{len(platforms_to_interview)}")
            return True
        else:
            errors = [f"{p}: {r.get('error', 'Unknown error')}" for p, r in results["platforms"].items()]
            self.send_response(command_id, "failed", error="; ".join(errors))
            print(f"  Interview failed: agent_id={agent_id}, all platforms failed")
            return False
    
    async def handle_batch_interview(self, command_id: str, interviews: List[Dict], platform: str = None) -> bool:
        """
        Process batch interview command
        
        Args:
            command_id: Command ID
            interviews: [{"agent_id": int, "prompt": str, "platform": str(optional)}, ...]
            platform: Default platform (can be overridden by each interview item)
                - "twitter": Only interview on Twitter
                - "reddit": Only interview on Reddit
                - None/Not specified: Interview both platforms for each agent
        """
        # Group by platform
        twitter_interviews = []
        reddit_interviews = []
        both_platforms_interviews = []  # Those needing interview on both platforms
        
        for interview in interviews:
            item_platform = interview.get("platform", platform)
            if item_platform == "twitter":
                twitter_interviews.append(interview)
            elif item_platform == "reddit":
                reddit_interviews.append(interview)
            else:
                # Unspecified platform: interview both
                both_platforms_interviews.append(interview)
        
        # Split both_platforms_interviews into two platforms
        if both_platforms_interviews:
            if self.twitter_env:
                twitter_interviews.extend(both_platforms_interviews)
            if self.reddit_env:
                reddit_interviews.extend(both_platforms_interviews)
        
        results = {}
        
        # Process Twitter platform interviews
        if twitter_interviews and self.twitter_env:
            try:
                twitter_actions = {}
                for interview in twitter_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.twitter_agent_graph.get_agent(agent_id)
                        twitter_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  Warning: Could not get Twitter Agent {agent_id}: {e}")
                
                if twitter_actions:
                    await integrity_checked_step(
                        self.twitter_env,
                        self.twitter_instruction_guard,
                        twitter_actions,
                    )
                    
                    for interview in twitter_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "twitter")
                        result["platform"] = "twitter"
                        results[f"twitter_{agent_id}"] = result
            except InstructionIntegrityViolation:
                raise
            except Exception as e:
                print(f"  Twitter batch Interview failed: {e}")
        
        # Process Reddit platform interviews
        if reddit_interviews and self.reddit_env:
            try:
                reddit_actions = {}
                for interview in reddit_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.reddit_agent_graph.get_agent(agent_id)
                        reddit_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  Warning: Could not get Reddit Agent {agent_id}: {e}")
                
                if reddit_actions:
                    await integrity_checked_step(
                        self.reddit_env,
                        self.reddit_instruction_guard,
                        reddit_actions,
                    )
                    
                    for interview in reddit_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "reddit")
                        result["platform"] = "reddit"
                        results[f"reddit_{agent_id}"] = result
            except InstructionIntegrityViolation:
                raise
            except Exception as e:
                print(f"  Reddit batch Interview failed: {e}")
        
        if results:
            self.send_response(command_id, "completed", result={
                "interviews_count": len(results),
                "results": results
            })
            print(f"  Batch Interview completed: {len(results)} agents")
            return True
        else:
            self.send_response(command_id, "failed", error="No successful interviews")
            return False
    
    def _get_interview_result(self, agent_id: int, platform: str) -> Dict[str, Any]:
        """Get latest Interview result from database"""
        db_path = os.path.join(self.simulation_dir, f"{platform}_simulation.db")
        
        result = {
            "agent_id": agent_id,
            "response": None,
            "timestamp": None
        }
        
        if not os.path.exists(db_path):
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Query latest Interview record
            cursor.execute("""
                SELECT user_id, info, created_at
                FROM trace
                WHERE action = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ActionType.INTERVIEW.value, agent_id))
            
            row = cursor.fetchone()
            if row:
                user_id, info_json, created_at = row
                try:
                    info = json.loads(info_json) if info_json else {}
                    result["response"] = info.get("response", info)
                    result["timestamp"] = created_at
                except json.JSONDecodeError:
                    result["response"] = info_json
            
            conn.close()
            
        except Exception as e:
            print(f"  Failed to read Interview result: {e}")
        
        return result
    
    async def process_commands(self) -> bool:
        """
        Process all pending commands
        
        Returns:
            True to continue running, False to exit
        """
        command = self.poll_command()
        if not command:
            return True
        
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})
        
        print(f"\nReceived IPC command: {command_type}, id={command_id}")
        
        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", ""),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", []),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.CLOSE_ENV:
            print("Received close environment command")
            self.send_response(command_id, "completed", result={"message": "Environment is about to close"})
            return False
        
        else:
            self.send_response(command_id, "failed", error=f"Unknown command type: {command_type}")
            return True


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Non-core action types to filter out (low analysis value)
FILTERED_ACTIONS = {'refresh', 'sign_up'}

# Action type mapping table (name in database -> standard name)
ACTION_TYPE_MAP = {
    'create_post': 'CREATE_POST',
    'like_post': 'LIKE_POST',
    'dislike_post': 'DISLIKE_POST',
    'repost': 'REPOST',
    'quote_post': 'QUOTE_POST',
    'follow': 'FOLLOW',
    'mute': 'MUTE',
    'create_comment': 'CREATE_COMMENT',
    'like_comment': 'LIKE_COMMENT',
    'dislike_comment': 'DISLIKE_COMMENT',
    'search_posts': 'SEARCH_POSTS',
    'search_user': 'SEARCH_USER',
    'trend': 'TREND',
    'do_nothing': 'DO_NOTHING',
    'interview': 'INTERVIEW',
}


def get_agent_names_from_config(config: Dict[str, Any]) -> Dict[int, str]:
    """
    Get agent_id -> entity_name mapping from simulation_config
    
    This allows displaying real entity names in actions.jsonl instead of code names like "Agent_0"
    
    Args:
        config: Content of simulation_config.json
        
    Returns:
        Mapping dictionary of agent_id -> entity_name
    """
    agent_names = {}
    agent_configs = config.get("agent_configs", [])
    
    for agent_config in agent_configs:
        agent_id = agent_config.get("agent_id")
        entity_name = agent_config.get("entity_name", f"Agent_{agent_id}")
        if agent_id is not None:
            agent_names[agent_id] = entity_name
    
    return agent_names


def fetch_new_actions_from_db(
    db_path: str,
    last_rowid: int,
    agent_names: Dict[int, str]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetch new action records from database and supplement with full context information
    
    Args:
        db_path: Database file path
        last_rowid: Last rowid value read (use rowid instead of created_at because created_at formats differ across platforms)
        agent_names: agent_id -> agent_name mapping
        
    Returns:
        (actions_list, new_last_rowid)
        - actions_list: List of actions, each containing agent_id, agent_name, action_type, action_args (with context)
        - new_last_rowid: New maximum rowid value
    """
    actions = []
    new_last_rowid = last_rowid
    
    if not os.path.exists(db_path):
        return actions, new_last_rowid
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Use rowid to track processed records (rowid is SQLite's built-in autoincrement field)
        # This avoids issues with created_at format differences (Twitter uses integers, Reddit uses datetime strings)
        cursor.execute("""
            SELECT rowid, user_id, action, info
            FROM trace
            WHERE rowid > ?
            ORDER BY rowid ASC
        """, (last_rowid,))
        
        for rowid, user_id, action, info_json in cursor.fetchall():
            # Update maximum rowid
            new_last_rowid = rowid
            
            # Filter non-core actions
            if action in FILTERED_ACTIONS:
                continue
            
            # Parse action parameters
            try:
                action_args = json.loads(info_json) if info_json else {}
            except json.JSONDecodeError:
                action_args = {}
            
            # Streamline action_args, keeping only key fields (keep full content, no truncation)
            simplified_args = {}
            if 'content' in action_args:
                simplified_args['content'] = action_args['content']
            if 'post_id' in action_args:
                simplified_args['post_id'] = action_args['post_id']
            if 'comment_id' in action_args:
                simplified_args['comment_id'] = action_args['comment_id']
            if 'quoted_id' in action_args:
                simplified_args['quoted_id'] = action_args['quoted_id']
            if 'new_post_id' in action_args:
                simplified_args['new_post_id'] = action_args['new_post_id']
            if 'follow_id' in action_args:
                simplified_args['follow_id'] = action_args['follow_id']
            if 'query' in action_args:
                simplified_args['query'] = action_args['query']
            if 'like_id' in action_args:
                simplified_args['like_id'] = action_args['like_id']
            if 'dislike_id' in action_args:
                simplified_args['dislike_id'] = action_args['dislike_id']
            
            # Convert action type name
            action_type = ACTION_TYPE_MAP.get(action, action.upper())
            
            # Supplement context information (post content, username, etc.)
            _enrich_action_context(cursor, action_type, simplified_args, agent_names)
            
            actions.append({
                'agent_id': user_id,
                'agent_name': agent_names.get(user_id, f'Agent_{user_id}'),
                'action_type': action_type,
                'action_args': simplified_args,
            })
        
        conn.close()
    except Exception as e:
        print(f"Failed to read database actions: {e}")
    
    return actions, new_last_rowid


def _enrich_action_context(
    cursor,
    action_type: str,
    action_args: Dict[str, Any],
    agent_names: Dict[int, str]
) -> None:
    """
    Supplement actions with context information (post content, username, etc.)
    
    Args:
        cursor: Database cursor
        action_type: Action type
        action_args: Action parameters (will be modified)
        agent_names: agent_id -> agent_name mapping
    """
    try:
        # Like/Dislike post: supplement post content and author
        if action_type in ('LIKE_POST', 'DISLIKE_POST'):
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
        
        # Repost: supplement original post content and author
        elif action_type == 'REPOST':
            new_post_id = action_args.get('new_post_id')
            if new_post_id:
                # Repost original_post_id points to the original post
                cursor.execute("""
                    SELECT original_post_id FROM post WHERE post_id = ?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    original_post_id = row[0]
                    original_info = _get_post_info(cursor, original_post_id, agent_names)
                    if original_info:
                        action_args['original_content'] = original_info.get('content', '')
                        action_args['original_author_name'] = original_info.get('author_name', '')
        
        # Quote post: supplement original post content, author, and quote comment
        elif action_type == 'QUOTE_POST':
            quoted_id = action_args.get('quoted_id')
            new_post_id = action_args.get('new_post_id')
            
            if quoted_id:
                original_info = _get_post_info(cursor, quoted_id, agent_names)
                if original_info:
                    action_args['original_content'] = original_info.get('content', '')
                    action_args['original_author_name'] = original_info.get('author_name', '')
            
            
            # Get comment content of the quoted post (quote_content)
            if new_post_id:
                cursor.execute("""
                    SELECT quote_content FROM post WHERE post_id = ?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    action_args['quote_content'] = row[0]
        
        # Follow user: supplement followed user's name
        elif action_type == 'FOLLOW':
            follow_id = action_args.get('follow_id')
            if follow_id:
                # Get followee_id from follow table
                cursor.execute("""
                    SELECT followee_id FROM follow WHERE follow_id = ?
                """, (follow_id,))
                row = cursor.fetchone()
                if row:
                    followee_id = row[0]
                    target_name = _get_user_name(cursor, followee_id, agent_names)
                    if target_name:
                        action_args['target_user_name'] = target_name
        
        # Mute user: supplement muted user's name
        elif action_type == 'MUTE':
            # Get user_id or target_id from action_args
            target_id = action_args.get('user_id') or action_args.get('target_id')
            if target_id:
                target_name = _get_user_name(cursor, target_id, agent_names)
                if target_name:
                    action_args['target_user_name'] = target_name
        
        # Like/Dislike comment: supplement comment content and author
        elif action_type in ('LIKE_COMMENT', 'DISLIKE_COMMENT'):
            comment_id = action_args.get('comment_id')
            if comment_id:
                comment_info = _get_comment_info(cursor, comment_id, agent_names)
                if comment_info:
                    action_args['comment_content'] = comment_info.get('content', '')
                    action_args['comment_author_name'] = comment_info.get('author_name', '')
        
        # Create comment: supplement information of the post being commented on
        elif action_type == 'CREATE_COMMENT':
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
    
    except Exception as e:
        # Failure to supplement context does not affect main process
        print(f"Failed to supplement action context: {e}")


def _get_post_info(
    cursor,
    post_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    Get post information
    
    Args:
        cursor: Database cursor
        post_id: Post ID
        agent_names: agent_id -> agent_name mapping
        
    Returns:
        Dictionary containing content and author_name, or None
    """
    try:
        cursor.execute("""
            SELECT p.content, p.user_id, u.agent_id
            FROM post p
            LEFT JOIN user u ON p.user_id = u.user_id
            WHERE p.post_id = ?
        """, (post_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # Prioritize names from agent_names
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # Get name from user table
                cursor.execute("SELECT name, user_name FROM user WHERE user_id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''
            
            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def _get_user_name(
    cursor,
    user_id: int,
    agent_names: Dict[int, str]
) -> Optional[str]:
    """
    Get username
    
    Args:
        cursor: Database cursor
        user_id: User ID
        agent_names: agent_id -> agent_name mapping
        
    Returns:
        Username, or None
    """
    try:
        cursor.execute("""
            SELECT agent_id, name, user_name FROM user WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            agent_id = row[0]
            name = row[1]
            user_name = row[2]
            
            # Prioritize names from agent_names
            if agent_id is not None and agent_id in agent_names:
                return agent_names[agent_id]
            return name or user_name or ''
    except Exception:
        pass
    return None


def _get_comment_info(
    cursor,
    comment_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    Get comment information
    
    Args:
        cursor: Database cursor
        comment_id: Comment ID
        agent_names: agent_id -> agent_name mapping
        
    Returns:
        Dictionary containing content and author_name, or None
    """
    try:
        cursor.execute("""
            SELECT c.content, c.user_id, u.agent_id
            FROM comment c
            LEFT JOIN user u ON c.user_id = u.user_id
            WHERE c.comment_id = ?
        """, (comment_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # Prioritize names from agent_names
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # Get name from user table
                cursor.execute("SELECT name, user_name FROM user WHERE user_id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''
            
            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def create_model(simulation_dir: str, use_boost: bool = False):
    """
    Create LLM model
    
    Supports dual LLM configuration to speed up parallel simulation:
    - General config: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
    - Boost config (optional): LLM_BOOST_API_KEY, LLM_BOOST_BASE_URL, LLM_BOOST_MODEL_NAME
    
    If boost LLM is configured, parallel simulation can use different API providers for different platforms to increase concurrency.
    
    Args:
        simulation_dir: Simulation directory path
        use_boost: Whether to use boost LLM configuration (if available)
    """
    model, settings = create_actor_model_for_runtime(
        simulation_dir,
        prefer_boost=use_boost,
    )
    provider_mode = settings.get("provider_mode", "unknown")
    model_name = settings.get("model_name", "unknown")
    base_url = settings.get("base_url", "")
    semaphore = settings.get("semaphore", 30)
    print(
        f"[actor-model] provider={provider_mode}, model={model_name}, "
        f"base_url={base_url[:60] if base_url else 'default'}, semaphore={semaphore}"
    )
    return model, settings


def get_active_agents_for_round(
    config: Dict[str, Any],
    platform: str,
    current_hour: int,
    round_num: int,
    event_boost_agent_ids: Optional[List[int]] = None,
) -> List:
    """Determine which agents to activate this round based on time and configuration"""
    return select_active_agent_ids(
        config=config,
        platform=platform,
        current_hour=current_hour,
        round_num=round_num,
        event_boost_agent_ids=event_boost_agent_ids,
    )


def _extract_and_record_reflections(simulation_dir: str, platform: str, round_num: int, agent_names: Dict[int, str]):
    """Extract reflection results from oasis trace DB and persist to the canonical simulation observations DB."""
    db_path = os.path.join(simulation_dir, f"{platform}_simulation.db")
    if not os.path.exists(db_path):
        return
        
    try:
        from app.services.simulation_observation_store import add_reflection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for agent_id, agent_name in agent_names.items():
            cursor.execute("""
                SELECT info
                FROM trace
                WHERE action = ? AND user_id = ?
                ORDER BY rowid DESC
                LIMIT 1
            """, ("INTERVIEW", agent_id))
            row = cursor.fetchone()
            if row and row[0]:
                info = row[0]
                # The info string is the JSON string of the agent's response to the interview prompt.
                # Default importance is 1.0.
                add_reflection(simulation_dir, agent_name, round_num, info, 1.0)
        conn.close()
    except Exception as e:
        print(f"Failed to extract and record reflections: {e}")


class PlatformSimulation:
    """Platform simulation result container"""
    def __init__(self):
        self.env = None
        self.agent_graph = None
        self.instruction_guard = None
        self.total_actions = 0


async def integrity_checked_step(env, integrity_guard, actions):
    """Verify immutable instructions and tools around every OASIS step."""
    if integrity_guard is None:
        raise InstructionIntegrityViolation(
            agent_id=None,
            expected_sha256="",
            actual_sha256="",
        )
    integrity_guard.verify(env.agent_graph)
    try:
        await env.step(actions)
    finally:
        integrity_guard.verify(env.agent_graph)


async def run_twitter_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Run Twitter simulation"""
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Twitter] {msg}")
        print(f"[Twitter] {msg}")
    
    log_info("Initializing...")
    
    # Twitter actor model
    model, actor_settings = create_model(simulation_dir, use_boost=False)
    
    adapters = load_decision_lens_runtime_adapters(simulation_dir)
    result.agent_graph = await generate_decision_lens_agent_graph(
        adapters=adapters,
        platform="twitter",
        model=model,
        available_actions=TWITTER_ACTIONS,
    )
    result.instruction_guard = InstructionIntegrityGuard.capture(
        result.agent_graph
    )
    
    # Apply initial network topology before starting the simulation
    apply_network_topology(result.agent_graph, config)
    
    # Get Agent real name mapping from configuration (using entity_name instead of default Agent_X)
    agent_names = build_agent_name_lookup(config)
    # If an agent is not in the configuration, use the OASIS default name
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')
    
    db_path = os.path.join(simulation_dir, "twitter_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
        semaphore=actor_settings.get("semaphore", 30),
    )
    
    await result.env.reset()
    result.instruction_guard.verify(result.env.agent_graph)
    log_info("Environment started")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # Track last rowid processed in database (rowid avoids created_at format issues)
    
    # Record round 0 start (bootstrap/initial events phase)
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0
    
    initial_action_count = await apply_bootstrap_actions(
        env=result.env,
        simulation_dir=simulation_dir,
        config=config,
        platform="twitter",
        agent_names=agent_names,
        manual_action_cls=ManualAction,
        action_type_cls=ActionType,
        action_logger=None,
    )
    bootstrap_actions, last_rowid = fetch_new_actions_from_db(
        db_path, last_rowid, agent_names
    )
    initial_action_count = 0
    for action_data in bootstrap_actions:
        if action_logger:
            action_logger.log_action(
                round_num=0,
                agent_id=action_data['agent_id'],
                agent_name=action_data['agent_name'],
                action_type=action_data['action_type'],
                action_args=action_data['action_args']
            )
        total_actions += 1
        initial_action_count += 1
    if initial_action_count:
        log_info(f"Executed {initial_action_count} round 0 bootstrap actions")
    
    # Record round 0 end
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # Main simulation loop
    time_config = config.get("time_config", {})
    minutes_per_round = float(time_config.get("minutes_per_round", 30))
    configured_rounds = resolve_total_rounds(config)
    total_rounds = resolve_total_rounds(config, max_rounds)
    if total_rounds < configured_rounds:
        log_info(
            f"Rounds truncated: {configured_rounds} -> {total_rounds} "
            f"(max_rounds={max_rounds})"
        )
    
    start_time = datetime.now()
    event_consumer = RedisEventConsumer(
        simulation_id=os.path.basename(simulation_dir),
        platform="twitter",
    )
    
    for round_num in range(total_rounds):
        # Check for shutdown signal
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"Shutdown signal received, stopping simulation at round {round_num + 1} ")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = int((simulated_minutes // 60) % 24)
        simulated_day = int(simulated_minutes // (60 * 24) + 1)

        # Record round start regardless of active agents
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)
        
        injected_events = event_consumer.consume_events()
        if injected_events:
            await apply_injected_events(
                env=result.env,
                simulation_dir=simulation_dir,
                config=config,
                platform="twitter",
                current_round=round_num + 1,
                events=injected_events,
                agent_names=agent_names,
                manual_action_cls=ManualAction,
                action_type_cls=ActionType,
                action_logger=action_logger,
            )
        
        scheduled_count = await apply_scheduled_events(
            env=result.env,
            simulation_dir=simulation_dir,
            config=config,
            platform="twitter",
            current_round=round_num + 1,
            agent_names=agent_names,
            manual_action_cls=ManualAction,
            action_type_cls=ActionType,
            action_logger=None,
        )
        scheduled_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        scheduled_count = 0
        for action_data in scheduled_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
            total_actions += 1
            scheduled_count += 1
        event_boost_agent_ids = []
        if round_num == 0:
            event_boost_agent_ids.extend(bootstrap_boost_agent_ids(simulation_dir, config, "twitter"))
        event_boost_agent_ids.extend(
            scheduled_event_boost_agent_ids(simulation_dir, config, "twitter", round_num + 1)
        )
        active_agent_ids = get_active_agents_for_round(
            config,
            "twitter",
            simulated_hour,
            round_num,
            event_boost_agent_ids=list(sorted(set(event_boost_agent_ids))),
        )
        
        if not active_agent_ids:
            # Record round end even if no active agents (actions_count=0)
            if action_logger:
                action_logger.log_round_end(round_num + 1, scheduled_count)
            continue
        
        actions = {}
        for agent_id in active_agent_ids:
            try:
                actions[result.env.agent_graph.get_agent(agent_id)] = LLMAction()
            except Exception:
                pass
        if not actions:
            if action_logger:
                action_logger.log_round_end(round_num + 1, scheduled_count)
            continue
        await integrity_checked_step(
            result.env,
            result.instruction_guard,
            actions,
        )
        
        # Fetch actions actually performed from database and record
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = scheduled_count
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
        
        # Trigger reflection every N rounds (default 4 = 2 hours simulated time)
        reflection_interval = time_config.get("reflection_interval_rounds", 4)
        if reflection_interval > 0 and (round_num + 1) % reflection_interval == 0:
            log_info(f"Starting scheduled reflection phase for Twitter Round {round_num + 1}...")
            reflected_count = await apply_reflection_round(
                env=result.env,
                platform="twitter",
                round_num=round_num + 1,
                agent_names=agent_names,
                manual_action_cls=ManualAction,
                action_type_cls=ActionType,
                action_logger=action_logger
            )
            # Fetch the just-generated reflection interviews and store them canonically
            _extract_and_record_reflections(simulation_dir, "twitter", round_num + 1, agent_names)
            
            # Use reflections to apply homophily-based rewiring (filter bubbles)
            await apply_homophily_rewiring(result.agent_graph, simulation_dir, round_num + 1, config)
            
            log_info(f"Twitter Reflection phase complete: {reflected_count} agents processed.")

    
    # Note: Do not close environment, keep it for Interview
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)

    result.instruction_guard.verify(result.agent_graph)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"Simulation loop completed! Elapsed: {elapsed:.1f}s, Total actions: {total_actions}")
    
    return result


async def run_reddit_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Run Reddit simulation"""
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Reddit] {msg}")
        print(f"[Reddit] {msg}")
    
    log_info("Initializing...")
    
    # Reddit actor model
    model, actor_settings = create_model(simulation_dir, use_boost=True)
    
    adapters = load_decision_lens_runtime_adapters(simulation_dir)
    result.agent_graph = await generate_decision_lens_agent_graph(
        adapters=adapters,
        platform="reddit",
        model=model,
        available_actions=REDDIT_ACTIONS,
    )
    result.instruction_guard = InstructionIntegrityGuard.capture(
        result.agent_graph
    )
    
    # Apply initial network topology before starting the simulation
    apply_network_topology(result.agent_graph, config)
    
    # Get Agent real name mapping from configuration (using entity_name instead of default Agent_X)
    agent_names = build_agent_name_lookup(config)
    # If an agent is not in the configuration, use the OASIS default name
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')
    
    db_path = os.path.join(simulation_dir, "reddit_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
        semaphore=actor_settings.get("semaphore", 30),
    )
    
    await result.env.reset()
    result.instruction_guard.verify(result.env.agent_graph)
    log_info("Environment started")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # Track last rowid processed in database (rowid avoids created_at format issues)
    
    # Record round 0 start (bootstrap/initial events phase)
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0
    
    initial_action_count = await apply_bootstrap_actions(
        env=result.env,
        simulation_dir=simulation_dir,
        config=config,
        platform="reddit",
        agent_names=agent_names,
        manual_action_cls=ManualAction,
        action_type_cls=ActionType,
        action_logger=None,
    )
    bootstrap_actions, last_rowid = fetch_new_actions_from_db(
        db_path, last_rowid, agent_names
    )
    initial_action_count = 0
    for action_data in bootstrap_actions:
        if action_logger:
            action_logger.log_action(
                round_num=0,
                agent_id=action_data['agent_id'],
                agent_name=action_data['agent_name'],
                action_type=action_data['action_type'],
                action_args=action_data['action_args']
            )
        total_actions += 1
        initial_action_count += 1
    if initial_action_count:
        log_info(f"Executed {initial_action_count} round 0 bootstrap actions")
    
    # Record round 0 end
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # Main simulation loop
    time_config = config.get("time_config", {})
    minutes_per_round = float(time_config.get("minutes_per_round", 30))
    configured_rounds = resolve_total_rounds(config)
    total_rounds = resolve_total_rounds(config, max_rounds)
    if total_rounds < configured_rounds:
        log_info(
            f"Rounds truncated: {configured_rounds} -> {total_rounds} "
            f"(max_rounds={max_rounds})"
        )
    
    start_time = datetime.now()
    event_consumer = RedisEventConsumer(
        simulation_id=os.path.basename(simulation_dir),
        platform="reddit",
    )
    
    for round_num in range(total_rounds):
        # Check for shutdown signal
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"Shutdown signal received, stopping simulation at round {round_num + 1} ")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = int((simulated_minutes // 60) % 24)
        simulated_day = int(simulated_minutes // (60 * 24) + 1)

        # Record round start regardless of active agents
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)
        
        injected_events = event_consumer.consume_events()
        if injected_events:
            await apply_injected_events(
                env=result.env,
                simulation_dir=simulation_dir,
                config=config,
                platform="reddit",
                current_round=round_num + 1,
                events=injected_events,
                agent_names=agent_names,
                manual_action_cls=ManualAction,
                action_type_cls=ActionType,
                action_logger=action_logger,
            )
        
        scheduled_count = await apply_scheduled_events(
            env=result.env,
            simulation_dir=simulation_dir,
            config=config,
            platform="reddit",
            current_round=round_num + 1,
            agent_names=agent_names,
            manual_action_cls=ManualAction,
            action_type_cls=ActionType,
            action_logger=None,
        )
        scheduled_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        scheduled_count = 0
        for action_data in scheduled_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
            total_actions += 1
            scheduled_count += 1
        event_boost_agent_ids = []
        if round_num == 0:
            event_boost_agent_ids.extend(bootstrap_boost_agent_ids(simulation_dir, config, "reddit"))
        event_boost_agent_ids.extend(
            scheduled_event_boost_agent_ids(simulation_dir, config, "reddit", round_num + 1)
        )
        active_agent_ids = get_active_agents_for_round(
            config,
            "reddit",
            simulated_hour,
            round_num,
            event_boost_agent_ids=list(sorted(set(event_boost_agent_ids))),
        )
        
        if not active_agent_ids:
            # Record round end even if no active agents (actions_count=0)
            if action_logger:
                action_logger.log_round_end(round_num + 1, scheduled_count)
            continue
        
        actions = {}
        for agent_id in active_agent_ids:
            try:
                agent = result.env.agent_graph.get_agent(agent_id)
            except Exception:
                continue
            actions[agent] = LLMAction()
        if not actions:
            if action_logger:
                action_logger.log_round_end(round_num + 1, scheduled_count)
            continue
        await integrity_checked_step(
            result.env,
            result.instruction_guard,
            actions,
        )
        
        # Fetch actions actually performed from database and record
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = scheduled_count
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
        
        # Trigger reflection every N rounds (default 4 = 2 hours simulated time)
        reflection_interval = time_config.get("reflection_interval_rounds", 4)
        if reflection_interval > 0 and (round_num + 1) % reflection_interval == 0:
            log_info(f"Starting scheduled reflection phase for Reddit Round {round_num + 1}...")
            reflected_count = await apply_reflection_round(
                env=result.env,
                platform="reddit",
                round_num=round_num + 1,
                agent_names=agent_names,
                manual_action_cls=ManualAction,
                action_type_cls=ActionType,
                action_logger=action_logger
            )
            # Fetch the just-generated reflection interviews and store them canonically
            _extract_and_record_reflections(simulation_dir, "reddit", round_num + 1, agent_names)
            
            # Use reflections to apply homophily-based rewiring (filter bubbles)
            await apply_homophily_rewiring(result.agent_graph, simulation_dir, round_num + 1, config)
            
            log_info(f"Reddit Reflection phase complete: {reflected_count} agents processed.")

    
    # Note: Do not close environment, keep it for Interview
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)

    result.instruction_guard.verify(result.agent_graph)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"Simulation loop completed! Elapsed: {elapsed:.1f}s, Total actions: {total_actions}")
    
    return result


async def main():
    parser = argparse.ArgumentParser(description='OASIS dual platform parallel simulation')
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='Configuration file path (simulation_config.json)'
    )
    parser.add_argument(
        '--twitter-only',
        action='store_true',
        help='Only run Twitter simulation'
    )
    parser.add_argument(
        '--reddit-only',
        action='store_true',
        help='Only run Reddit simulation'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='Maximum simulation rounds (optional, used to truncate long simulations)'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='Close environment immediately after simulation, do not enter command-wait mode'
    )
    
    args = parser.parse_args()
    
    # Create shutdown event at the start of main function to ensure the entire program can respond to exit signals
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    
    if not os.path.exists(args.config):
        print(f"Error: Configuration file does not exist: {args.config}")
        sys.exit(1)
    
    config = load_config(args.config)
    simulation_dir = os.path.dirname(args.config) or "."
    wait_for_commands = not args.no_wait
    
    # Initialize logging configuration (disable OASIS logs, clean up old files)
    init_logging_for_simulation(simulation_dir)
    
    # Create log manager
    log_manager = SimulationLogManager(simulation_dir)
    twitter_logger = log_manager.get_twitter_logger()
    reddit_logger = log_manager.get_reddit_logger()
    
    log_manager.info("=" * 60)
    log_manager.info("OASIS dual platform parallel simulation")
    log_manager.info(f"Configuration file: {args.config}")
    log_manager.info(f"Simulation ID: {config.get('simulation_id', 'unknown')}")
    log_manager.info(f"Wait-for-command mode: {'Enabled' if wait_for_commands else 'Disabled'}")
    log_manager.info("=" * 60)
    
    time_config = config.get("time_config", {})
    total_hours = time_config.get('total_simulation_hours', 72)
    minutes_per_round = time_config.get('minutes_per_round', 30)
    config_total_rounds = resolve_total_rounds(config)
    execution_total_rounds = resolve_total_rounds(config, args.max_rounds)
    
    log_manager.info(f"Simulation parameters:")
    log_manager.info(f"  - Total simulation duration: {total_hours}hours")
    log_manager.info(f"  - Minutes per round: {minutes_per_round}minutes")
    log_manager.info(f"  - Configured Total rounds: {config_total_rounds}")
    if args.max_rounds is not None:
        log_manager.info(f"  - Max rounds limit: {args.max_rounds}")
        if execution_total_rounds < config_total_rounds:
            log_manager.info(
                f"  - Actual execution rounds: {execution_total_rounds} (Truncated)"
            )
    log_manager.info(f"  - Agent count: {len(config.get('agent_configs', []))}")
    
    log_manager.info("Log structure:")
    log_manager.info(f"  - Main log: simulation.log")
    log_manager.info(f"  - Twitter actions: twitter/actions.jsonl")
    log_manager.info(f"  - Reddit actions: reddit/actions.jsonl")
    log_manager.info("=" * 60)
    
    start_time = datetime.now()
    
    # Store simulation results for both platforms
    twitter_result: Optional[PlatformSimulation] = None
    reddit_result: Optional[PlatformSimulation] = None
    
    if args.twitter_only:
        twitter_result = await run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds)
    elif args.reddit_only:
        reddit_result = await run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds)
    else:
        # Run in parallel (each platform uses an independent logger)
        results = await asyncio.gather(
            run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds),
            run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds),
        )
        twitter_result, reddit_result = results
    
    total_elapsed = (datetime.now() - start_time).total_seconds()
    log_manager.info("=" * 60)
    log_manager.info(f"Simulation loop complete! Total elapsed time: {total_elapsed:.1f}s")
    
    # Whether to enter command-wait mode
    if wait_for_commands:
        log_manager.info("")
        log_manager.info("=" * 60)
        log_manager.info("Entering wait-for-command mode - environment kept running")
        log_manager.info("Supported commands: interview, batch_interview, close_env")
        log_manager.info("=" * 60)
        
        # Create IPC handler
        ipc_handler = ParallelIPCHandler(
            simulation_dir=simulation_dir,
            twitter_env=twitter_result.env if twitter_result else None,
            twitter_agent_graph=twitter_result.agent_graph if twitter_result else None,
            twitter_instruction_guard=(
                twitter_result.instruction_guard if twitter_result else None
            ),
            reddit_env=reddit_result.env if reddit_result else None,
            reddit_agent_graph=reddit_result.agent_graph if reddit_result else None,
            reddit_instruction_guard=(
                reddit_result.instruction_guard if reddit_result else None
            ),
        )
        ipc_handler.update_status("alive")
        
        # Wait for command loop (using global _shutdown_event)
        try:
            while not _shutdown_event.is_set():
                should_continue = await ipc_handler.process_commands()
                if not should_continue:
                    break
                # Use wait_for instead of sleep, so it can respond to shutdown_event
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                    break  # Received exit signal
                except asyncio.TimeoutError:
                    pass  # Timeout continues the loop
        except KeyboardInterrupt:
            print("\nReceived interruption signal")
        except asyncio.CancelledError:
            print("\nTask cancelled")
        except InstructionIntegrityViolation:
            raise
        except Exception as e:
            print(f"\nCommand processing error: {e}")
        
        log_manager.info("\nClosing environment...")
        ipc_handler.update_status("stopped")
    
    # Close environment
    if twitter_result and twitter_result.env:
        twitter_result.instruction_guard.verify(twitter_result.agent_graph)
        await twitter_result.env.close()
        twitter_result.instruction_guard.verify(twitter_result.agent_graph)
        log_manager.info("[Twitter] Environment closed")
    
    if reddit_result and reddit_result.env:
        reddit_result.instruction_guard.verify(reddit_result.agent_graph)
        await reddit_result.env.close()
        reddit_result.instruction_guard.verify(reddit_result.agent_graph)
        log_manager.info("[Reddit] Environment closed")
    
    log_manager.info("=" * 60)
    log_manager.info(f"All complete!")
    log_manager.info(f"Log files:")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'simulation.log')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'twitter', 'actions.jsonl')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'reddit', 'actions.jsonl')}")
    log_manager.info("=" * 60)


def setup_signal_handlers(loop=None):
    """
    Set up signal handlers to ensure clean exit on SIGTERM/SIGINT
    
    Persistent simulation scenario: do not exit after simulation, wait for interview command
    When a termination signal is received, need to:
    1. Notify asyncio loop to exit wait
    2. Allow the program to perform necessary cleanup (closing DB, env, etc)
    3. Then exit
    """
    def signal_handler(signum, frame):
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\nReceived {sig_name} signal, exiting...")
        
        if not _cleanup_done:
            _cleanup_done = True
            # Set event to notify asyncio loop to exit (allowing resource cleanup)
            if _shutdown_event:
                _shutdown_event.set()
        
        # Do not call sys.exit() directly, let the asyncio loop exit normally and clean up
        # If repeated signals are received, force exit
        else:
            print("Force exiting...")
            sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except SystemExit:
        pass
    finally:
        # Clean up multiprocessing resource tracker (prevent warnings on exit)
        try:
            from multiprocessing import resource_tracker
            resource_tracker._resource_tracker._stop()
        except Exception:
            pass
        print("Simulation process exited")
