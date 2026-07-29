"""
OASIS Simulation Runner
Runs simulations in the background, records Agent actions, and supports real-time monitoring.
"""

import os
import sys
import json
import math
import time
import asyncio
import threading
import subprocess
import signal
import atexit
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue

from ..config import Config
from ..utils.logger import get_logger
from ..utils.input_policy import SIMULATION_ROUNDS_MAX
from .zep_graph_memory_updater import ZepGraphMemoryManager
from .simulation_ipc import SimulationIPCClient, CommandType, IPCResponse
from .simulation_observation_store import sync_observation_store
from .simulation_preflight import run_preflight

logger = get_logger('askthepeople.simulation_runner')

# Flag to track if cleanup function is registered
_cleanup_registered = False

# Platform detection
IS_WINDOWS = sys.platform == 'win32'


def resolve_total_rounds(
    time_config: Dict[str, Any],
    requested_max: int | None = None,
) -> int:
    """Resolve a positive run length under the global computational ceiling."""
    try:
        total_hours = float(time_config.get("total_simulation_hours", 72))
        minutes_per_round = float(time_config.get("minutes_per_round", 30))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "total_simulation_hours and minutes_per_round must be numbers"
        ) from exc
    if not math.isfinite(total_hours) or total_hours <= 0:
        raise ValueError("total_simulation_hours must be a positive finite number")
    if not math.isfinite(minutes_per_round) or minutes_per_round <= 0:
        raise ValueError("minutes_per_round must be a positive finite number")

    effective_limit = SIMULATION_ROUNDS_MAX
    if requested_max is not None:
        if isinstance(requested_max, bool):
            raise ValueError("requested max rounds must be an integer")
        try:
            req_int = int(requested_max)
        except (TypeError, ValueError) as exc:
            raise ValueError("requested max rounds must be an integer") from exc
        if req_int <= 0:
            raise ValueError("requested max rounds must be positive")
        effective_limit = min(effective_limit, req_int)

    calc_rounds = math.ceil((total_hours * 60.0) / minutes_per_round)
    return max(1, min(calc_rounds, effective_limit))


class RunnerStatus(str, Enum):
    """Runner status"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


@dataclass
class AgentAction:
    """Agent action record"""
    round_num: int
    timestamp: str
    platform: str  # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str  # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class RoundSummary:
    """Round summary"""
    round_num: int
    start_time: str
    end_time: Optional[str] = None
    simulated_hour: int = 0
    twitter_actions: int = 0
    reddit_actions: int = 0
    active_agents: List[int] = field(default_factory=list)
    actions: List[AgentAction] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "simulated_hour": self.simulated_hour,
            "twitter_actions": self.twitter_actions,
            "reddit_actions": self.reddit_actions,
            "active_agents": self.active_agents,
            "actions_count": len(self.actions),
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class SimulationRunState:
    """Simulation run state (real-time)"""
    simulation_id: str
    runner_status: RunnerStatus = RunnerStatus.IDLE
    
    # Progress info
    current_round: int = 0
    total_rounds: int = 0
    simulated_hours: int = 0
    total_simulation_hours: int = 0
    
    # Independent rounds/time per platform (for dual-platform display)
    twitter_current_round: int = 0
    reddit_current_round: int = 0
    twitter_simulated_hours: int = 0
    reddit_simulated_hours: int = 0
    
    # Platform status
    twitter_running: bool = False
    reddit_running: bool = False
    twitter_actions_count: int = 0
    reddit_actions_count: int = 0
    
    # Platform completion status (via simulation_end event in actions.jsonl)
    twitter_completed: bool = False
    reddit_completed: bool = False
    
    # Round summaries
    rounds: List[RoundSummary] = field(default_factory=list)
    
    # Recent actions (for real-time frontend display)
    recent_actions: List[AgentAction] = field(default_factory=list)
    max_recent_actions: int = 50
    
    # Timestamps
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    # Error message
    error: Optional[str] = None

    # Process ID (for stopping)
    process_pid: Optional[int] = None

    # Follower action counts (populated when enable_followers=True)
    follower_twitter_count: int = 0
    follower_reddit_count: int = 0
    
    def add_action(self, action: AgentAction):
        """Add action to recent actions list"""
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]
        
        if action.platform == "twitter":
            self.twitter_actions_count += 1
        else:
            self.reddit_actions_count += 1
        
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "simulated_hours": self.simulated_hours,
            "total_simulation_hours": self.total_simulation_hours,
            "progress_percent": round(self.current_round / max(self.total_rounds, 1) * 100, 1),
            # Independent rounds/time per platform
            "twitter_current_round": self.twitter_current_round,
            "reddit_current_round": self.reddit_current_round,
            "twitter_simulated_hours": self.twitter_simulated_hours,
            "reddit_simulated_hours": self.reddit_simulated_hours,
            "twitter_running": self.twitter_running,
            "reddit_running": self.reddit_running,
            "twitter_completed": self.twitter_completed,
            "reddit_completed": self.reddit_completed,
            "twitter_actions_count": self.twitter_actions_count,
            "reddit_actions_count": self.reddit_actions_count,
            "total_actions_count": self.twitter_actions_count + self.reddit_actions_count,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "process_pid": self.process_pid,
            "follower_twitter_count": self.follower_twitter_count,
            "follower_reddit_count": self.follower_reddit_count,
        }
    
    def to_detail_dict(self) -> Dict[str, Any]:
        """Include detailed info for recent actions"""
        result = self.to_dict()
        result["recent_actions"] = [a.to_dict() for a in self.recent_actions]
        result["rounds_count"] = len(self.rounds)
        return result


class SimulationRunner:
    """
    Simulation Runner
    
    Responsibilities:
    1. Run OASIS simulation in background process
    2. Parse logs, record Agent actions
    3. Provide real-time status API
    4. Support pause/stop/resume operations
    """
    
    # Run state storage directory
    RUN_STATE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    @classmethod
    def _get_run_state_dir(cls, simulation_id: str) -> str:
        """Validate and resolve a simulation run-state directory (path-traversal safe)."""
        from ..utils.safe_path import safe_join
        return safe_join(cls.RUN_STATE_DIR, simulation_id)

    # Scripts directory
    SCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../scripts'
    )
    
    # In-memory run state
    _run_states: Dict[str, SimulationRunState] = {}
    _processes: Dict[str, subprocess.Popen] = {}
    _action_queues: Dict[str, Queue] = {}
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stdout_files: Dict[str, Any] = {}  # stdout file handles
    _stderr_files: Dict[str, Any] = {}  # stderr file handles
    
    # Graph memory update configuration
    _graph_memory_enabled: Dict[str, bool] = {}  # simulation_id -> enabled

    # Follower engine state (populated by start_simulation when enable_followers=True)
    _follower_engines: Dict[str, Any] = {}   # simulation_id -> FollowerEngine
    _follower_agents: Dict[str, List] = {}   # simulation_id -> List[FollowerAgent]

    @classmethod
    def _release_runtime_resources(cls, simulation_id: str) -> None:
        """Release process-local resources after a run reaches a terminal state."""
        if cls._graph_memory_enabled.pop(simulation_id, False):
            try:
                ZepGraphMemoryManager.stop_updater(simulation_id)
                logger.info(
                    "Graph memory update stopped: simulation_id=%s",
                    simulation_id,
                )
            except Exception as exc:
                logger.error("Failed to stop graph memory updater: %s", exc)

        cls._follower_engines.pop(simulation_id, None)
        cls._follower_agents.pop(simulation_id, None)
        cls._processes.pop(simulation_id, None)
        cls._monitor_threads.pop(simulation_id, None)
        cls._action_queues.pop(simulation_id, None)

        for handles in (cls._stdout_files, cls._stderr_files):
            handle = handles.pop(simulation_id, None)
            if handle:
                try:
                    handle.close()
                except Exception as exc:
                    logger.error(
                        "Failed to close a runtime file handle for %s: %s",
                        simulation_id,
                        exc,
                    )

    @classmethod
    def _mark_interrupted(cls, simulation_id: str, state: SimulationRunState, reason: str) -> None:
        """Mark simulation as interrupted"""
        state.runner_status = RunnerStatus.INTERRUPTED
        state.twitter_running = False
        state.reddit_running = False
        state.completed_at = datetime.now().isoformat()
        state.error = reason
        cls._save_run_state(state)

    @classmethod
    def get_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Get simulation run state from the intentional single-worker runtime."""
        if simulation_id in cls._run_states:
            return cls._run_states[simulation_id]

        state = cls._load_run_state(simulation_id)
        if state:
            cls._run_states[simulation_id] = state
        return state

    @classmethod
    def _load_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Load run state from file"""
        state_file = os.path.join(cls._get_run_state_dir(simulation_id), "run_state.json")
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus(data.get("runner_status", "idle")),
                current_round=data.get("current_round", 0),
                total_rounds=data.get("total_rounds", 0),
                simulated_hours=data.get("simulated_hours", 0),
                total_simulation_hours=data.get("total_simulation_hours", 0),
                # Independent rounds/time per platform
                twitter_current_round=data.get("twitter_current_round", 0),
                reddit_current_round=data.get("reddit_current_round", 0),
                twitter_simulated_hours=data.get("twitter_simulated_hours", 0),
                reddit_simulated_hours=data.get("reddit_simulated_hours", 0),
                twitter_running=data.get("twitter_running", False),
                reddit_running=data.get("reddit_running", False),
                twitter_completed=data.get("twitter_completed", False),
                reddit_completed=data.get("reddit_completed", False),
                twitter_actions_count=data.get("twitter_actions_count", 0),
                reddit_actions_count=data.get("reddit_actions_count", 0),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                error=data.get("error"),
                process_pid=data.get("process_pid"),
            )
            
            # Load recent actions
            actions_data = data.get("recent_actions", [])
            for a in actions_data:
                state.recent_actions.append(AgentAction(
                    round_num=a.get("round_num", 0),
                    timestamp=a.get("timestamp", ""),
                    platform=a.get("platform", ""),
                    agent_id=a.get("agent_id", 0),
                    agent_name=a.get("agent_name", ""),
                    action_type=a.get("action_type", ""),
                    action_args=a.get("action_args", {}),
                    result=a.get("result"),
                    success=a.get("success", True),
                ))

            if state.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING, RunnerStatus.STOPPING]:
                cls._mark_interrupted(
                    simulation_id,
                    state,
                    "interrupted by restart before the runtime completed",
                )
            return state
        except Exception as e:
            logger.error(f"Failed to load run state: {str(e)}")
            return None
    
    @classmethod
    def _save_run_state(cls, state: SimulationRunState):
        """Save run state to file"""
        sim_dir = cls._get_run_state_dir(state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state_file = os.path.join(sim_dir, "run_state.json")
        
        data = state.to_detail_dict()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        cls._run_states[state.simulation_id] = state
    
    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        platform: str = "parallel",  # twitter / reddit / parallel
        max_rounds: int = None,  # Maximum rounds (optional)
        enable_graph_memory_update: bool = False,  # Dynamically update Agent activities to Zep graph
        graph_id: str = None,  # Zep Graph ID (required if update enabled)
        source_graph_id: Optional[str] = None,
        enable_followers: bool = False,
        follower_count: int = 100,
        follower_distribution: Optional[Dict[str, float]] = None,
    ) -> SimulationRunState:
        """
        Start simulation
        
        Args:
            simulation_id: Simulation ID
            platform: Platform (twitter/reddit/parallel)
            max_rounds: Maximum rounds (optional)
            enable_graph_memory_update: Dynamically update Agent activities to Zep graph
            graph_id: Zep Graph ID (required if update enabled)
            
        Returns:
            SimulationRunState
        """
        if enable_graph_memory_update:
            raise ValueError(
                "Synthetic graph writes are unsupported; generated activity "
                "remains in the simulation observation store."
            )

        # Check if already running
        existing = cls.get_run_state(simulation_id)
        if existing and existing.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING]:
            raise ValueError(f"Simulation already running: {simulation_id}")
        
        # Load simulation config
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        # Get all agent info from config file
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"Simulation config not found, please call /prepare first")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        preflight = run_preflight(sim_dir)
        if preflight.get("status") != "passed":
            raise ValueError(f"Preflight failed: {preflight.get('failed_checks', [])}")
        
        # Initialize run state
        time_config = config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = int(total_hours * 60 / minutes_per_round)
        
        # Truncate if max_rounds specified
        if max_rounds is not None and max_rounds > 0:
            original_rounds = total_rounds
            total_rounds = min(total_rounds, max_rounds)
            if total_rounds < original_rounds:
                logger.info(f"Rounds truncated: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
        
        state = SimulationRunState(
            simulation_id=simulation_id,
            runner_status=RunnerStatus.STARTING,
            total_rounds=total_rounds,
            total_simulation_hours=total_hours,
            started_at=datetime.now().isoformat(),
        )
        
        cls._save_run_state(state)
        
        # Create updater if graph memory update enabled
        if enable_graph_memory_update:
            if not graph_id:
                raise ValueError("graph_id must be provided when enabling graph updates")
            
            try:
                ZepGraphMemoryManager.create_updater(simulation_id, graph_id)
                cls._graph_memory_enabled[simulation_id] = True
                logger.info(f"Graph memory update enabled: simulation_id={simulation_id}, graph_id={graph_id}")
            except Exception as e:
                logger.error(f"Failed to create graph memory updater: {e}")
                cls._graph_memory_enabled[simulation_id] = False
        else:
            cls._graph_memory_enabled[simulation_id] = False

        # Initialize follower engine if requested
        if enable_followers:
            from .follower_engine import FollowerEngine
            from .simulation_artifacts import read_json, canonical_agents_path
            canonical_path = canonical_agents_path(sim_dir)
            canonical_agents = read_json(canonical_path, default=[])
            id_base = max(len(canonical_agents), 1000)
            engine = FollowerEngine(id_base=id_base)
            followers = engine.generate_followers(follower_count, follower_distribution)
            cls._follower_engines[simulation_id] = engine
            cls._follower_agents[simulation_id] = followers
            logger.info(f"Follower engine initialized: simulation_id={simulation_id}, count={len(followers)}, id_base={id_base}")
        else:
            cls._follower_engines.pop(simulation_id, None)
            cls._follower_agents.pop(simulation_id, None)

        # Determine which script to run (located in backend/scripts/)
        if platform == "twitter":
            script_name = "run_twitter_simulation.py"
            state.twitter_running = True
        elif platform == "reddit":
            script_name = "run_reddit_simulation.py"
            state.reddit_running = True
        else:
            script_name = "run_parallel_simulation.py"
            state.twitter_running = True
            state.reddit_running = True
        
        script_path = os.path.join(cls.SCRIPTS_DIR, script_name)
        
        if not os.path.exists(script_path):
            raise ValueError(f"Script does not exist: {script_path}")
        
        # Create action queue
        action_queue = Queue()
        cls._action_queues[simulation_id] = action_queue
        
        # Start simulation process
        try:
            # Command with full paths.
            # Log structure:
            #   twitter/actions.jsonl - Twitter action log
            #   reddit/actions.jsonl  - Reddit action log
            #   simulation.log        - Main process log
            
            cmd = [
                sys.executable,  # Python interpreter
                script_path,
                "--config", config_path,  # Full config file path
            ]
            
            # Add max_rounds to command line args if specified
            if max_rounds is not None and max_rounds > 0:
                cmd.extend(["--max-rounds", str(max_rounds)])
            
            # Create main log file (prevents stdout/stderr blocking)
            main_log_path = os.path.join(sim_dir, "simulation.log")
            main_log_file = open(main_log_path, 'w', encoding='utf-8')
            
            # Set child process env for UTF-8 on Windows
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'  # Python 3.7+ support
            env['PYTHONIOENCODING'] = 'utf-8'  # Ensure stdout/stderr use UTF-8
            
            # Inject dynamic API configurations from in-memory Config
            if getattr(Config, 'LLM_API_KEY', None):
                env['LLM_API_KEY'] = Config.LLM_API_KEY
            if getattr(Config, 'LLM_BASE_URL', None):
                env['LLM_BASE_URL'] = Config.LLM_BASE_URL
            if getattr(Config, 'LLM_MODEL_NAME', None):
                env['LLM_MODEL_NAME'] = Config.LLM_MODEL_NAME
            if getattr(Config, 'ZEP_API_KEY', None):
                env['ZEP_API_KEY'] = Config.ZEP_API_KEY
            
            # Set working dir to simulation dir
            # start_new_session=True to ensure process group termination
            process = subprocess.Popen(
                cmd,
                cwd=sim_dir,
                stdout=main_log_file,
                stderr=subprocess.STDOUT,  # stderr to same file
                text=True,
                encoding='utf-8',  # Explicitly specify encoding
                bufsize=1,
                env=env,
                start_new_session=True,  # New session for termination
            )
            
            # Save file handles for later closing
            cls._stdout_files[simulation_id] = main_log_file
            cls._stderr_files[simulation_id] = None  # No longer need separate stderr
            
            state.process_pid = process.pid
            state.runner_status = RunnerStatus.RUNNING
            cls._processes[simulation_id] = process
            cls._save_run_state(state)
            
            # Start monitor thread
            monitor_thread = threading.Thread(
                target=cls._monitor_simulation,
                args=(simulation_id,),
                daemon=True
            )
            monitor_thread.start()
            cls._monitor_threads[simulation_id] = monitor_thread
            
            logger.info(f"Simulation started successfully: {simulation_id}, pid={process.pid}, platform={platform}")
            
        except Exception as e:
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)
            raise
        
        return state
    
    @classmethod
    def _monitor_simulation(cls, simulation_id: str):
        """Monitor simulation process, parse action logs"""
        sim_dir = cls._get_run_state_dir(simulation_id)
        
        # Log structure: platform-specific action logs
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        
        process = cls._processes.get(simulation_id)
        state = cls.get_run_state(simulation_id)
        
        if not process or not state:
            return
        
        twitter_position = 0
        reddit_position = 0

        # Build follower round callback (no-op when followers not enabled)
        def _follower_round_callback(round_num: int, platform: str, sim_dir: str) -> None:
            engine = cls._follower_engines.get(simulation_id)
            followers = cls._follower_agents.get(simulation_id)
            if not engine or not followers:
                return
            round_leader_actions = cls._read_round_actions_raw(simulation_id, round_num, platform)
            follower_dicts = engine.compute_round_actions(followers, round_leader_actions, round_num, platform)
            if not follower_dicts:
                return
            follower_log = os.path.join(sim_dir, platform, "follower_actions.jsonl")
            os.makedirs(os.path.dirname(follower_log), exist_ok=True)
            with open(follower_log, "a", encoding="utf-8") as _f:
                for _d in follower_dicts:
                    _f.write(json.dumps(_d, ensure_ascii=False) + "\n")
            run_state = cls._run_states.get(simulation_id)
            if run_state:
                if platform == "twitter":
                    run_state.follower_twitter_count += len(follower_dicts)
                else:
                    run_state.follower_reddit_count += len(follower_dicts)

        try:
            while process.poll() is None:  # Process still running
                # Read Twitter action log
                if os.path.exists(twitter_actions_log):
                    twitter_position = cls._read_action_log(
                        twitter_actions_log, twitter_position, state, "twitter",
                        on_round_end=_follower_round_callback,
                    )

                # Read Reddit action log
                if os.path.exists(reddit_actions_log):
                    reddit_position = cls._read_action_log(
                        reddit_actions_log, reddit_position, state, "reddit",
                        on_round_end=_follower_round_callback,
                    )

                # Update state
                cls._save_run_state(state)
                time.sleep(2)

            # Read logs once more after process ends (drain pass — no follower callback)
            if os.path.exists(twitter_actions_log):
                cls._read_action_log(twitter_actions_log, twitter_position, state, "twitter")
            if os.path.exists(reddit_actions_log):
                cls._read_action_log(reddit_actions_log, reddit_position, state, "reddit")
            
            # Process ended
            exit_code = process.returncode
            
            if state.runner_status in (RunnerStatus.STOPPING, RunnerStatus.STOPPED):
                state.runner_status = RunnerStatus.STOPPED
                state.error = None
                logger.info("Simulation stopped: %s", simulation_id)
            elif exit_code == 0:
                state.runner_status = RunnerStatus.COMPLETED
                logger.info(f"Simulation completed: {simulation_id}")
            else:
                state.runner_status = RunnerStatus.FAILED
                # Read error from main log
                main_log_path = os.path.join(sim_dir, "simulation.log")
                error_info = ""
                try:
                    if os.path.exists(main_log_path):
                        with open(main_log_path, 'r', encoding='utf-8') as f:
                            error_info = f.read()[-2000:]  # Last 2000 chars
                except Exception:
                    pass
                state.error = f"Exit code: {exit_code}, error: {error_info}"
                logger.error(f"Simulation failed: {simulation_id}, error={state.error}")
            
        except Exception as exc:
            if state.runner_status in (RunnerStatus.STOPPING, RunnerStatus.STOPPED):
                state.runner_status = RunnerStatus.STOPPED
                state.error = None
                logger.info(
                    "Simulation monitor exited during an intentional stop: %s",
                    simulation_id,
                )
            else:
                logger.error(
                    "Monitor thread error: %s, error=%s",
                    simulation_id,
                    exc,
                )
                state.runner_status = RunnerStatus.FAILED
                state.error = str(exc)
        finally:
            state.twitter_running = False
            state.reddit_running = False
            if state.runner_status in (
                RunnerStatus.STOPPED,
                RunnerStatus.COMPLETED,
                RunnerStatus.INTERRUPTED,
                RunnerStatus.FAILED,
            ):
                state.completed_at = state.completed_at or datetime.now().isoformat()
            try:
                cls._save_run_state(state)
                sync_observation_store(
                    sim_dir,
                    run_state=state.to_detail_dict(),
                )
            except Exception as exc:
                logger.error(
                    "Failed to persist terminal run state for %s: %s",
                    simulation_id,
                    exc,
                )
            cls._release_runtime_resources(simulation_id)

        logger.info(
            "Simulation monitor thread finished for %s. Terminal state: %s",
            simulation_id,
            state.runner_status,
        )
        return state
    
    @classmethod
    def _read_action_log(
        cls,
        log_path: str,
        position: int,
        state: SimulationRunState,
        platform: str,
        on_round_end: Optional[Any] = None,  # callable(round_num, platform, sim_dir) or None
    ) -> int:
        """
        Read action log file
        
        Args:
            log_path: Log file path
            position: Last read position
            state: Run state object
            platform: Platform name (twitter/reddit)
            
        Returns:
            New read position
        """
        if not os.path.exists(log_path):
            return position
        
        with open(log_path, 'r', encoding='utf-8') as f:
            f.seek(position)
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    action_data = json.loads(line)
                    
                    # Handle event entries
                    if "event_type" in action_data:
                        event_type = action_data.get("event_type")
                        
                        # Detect simulation_end, mark platform completed
                        if event_type == "simulation_end":
                            if platform == "twitter":
                                state.twitter_completed = True
                                state.twitter_running = False
                                logger.info(f"Twitter simulation completed: {state.simulation_id}, total_rounds={action_data.get('total_rounds')}, total_actions={action_data.get('total_actions')}")
                            elif platform == "reddit":
                                state.reddit_completed = True
                                state.reddit_running = False
                                logger.info(f"Reddit simulation completed: {state.simulation_id}, total_rounds={action_data.get('total_rounds')}, total_actions={action_data.get('total_actions')}")
                            
                            # Check if all enabled platforms completed
                            all_completed = cls._check_all_platforms_completed(state)
                            if all_completed:
                                state.runner_status = RunnerStatus.COMPLETED
                                state.completed_at = datetime.now().isoformat()
                                logger.info(f"All platform simulations completed: {state.simulation_id}")
                        
                        # Update round info (from round_end event)
                        elif event_type == "round_end":
                            round_num = action_data.get("round", 0)
                            simulated_hours = action_data.get("simulated_hours", 0)

                            # Update per-platform rounds/time
                            if platform == "twitter":
                                if round_num > state.twitter_current_round:
                                    state.twitter_current_round = round_num
                                state.twitter_simulated_hours = simulated_hours
                            elif platform == "reddit":
                                if round_num > state.reddit_current_round:
                                    state.reddit_current_round = round_num
                                state.reddit_simulated_hours = simulated_hours

                            # Overall round is max of platforms
                            if round_num > state.current_round:
                                state.current_round = round_num
                            # Overall time is max of platforms
                            state.simulated_hours = max(state.twitter_simulated_hours, state.reddit_simulated_hours)

                            # Fire follower callback (only during live monitoring, not drain pass)
                            if on_round_end:
                                sim_dir = cls._get_run_state_dir(state.simulation_id)
                                try:
                                    on_round_end(round_num, platform, sim_dir)
                                except Exception as _fe:
                                    logger.error(f"Follower round callback error: {_fe}")

                        continue  # Skip event entries for action processing
                    
                    # Skip records without agent_id (non-Agent actions)
                    if "agent_id" not in action_data:
                        continue
                    
                    action = AgentAction(
                        round_num=action_data.get("round", 0),
                        timestamp=action_data.get("timestamp", ""),
                        platform=platform,
                        agent_id=action_data.get("agent_id", 0),
                        agent_name=action_data.get("agent_name", ""),
                        action_type=action_data.get("action_type", ""),
                        action_args=action_data.get("action_args", {}),
                        result=action_data.get("result"),
                        success=action_data.get("success", True),
                    )
                    state.add_action(action)
                    
                    # Update graph memory
                    if cls._graph_memory_enabled.get(state.simulation_id, False):
                        ZepGraphMemoryManager.update_memory(state.simulation_id, action)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse action log line: {line}, error: {e}")
                except Exception as e:
                    logger.error(f"Error processing action log line: {line}, error: {e}")
            
            position = f.tell()
        return position
    
    @classmethod
    def _read_round_actions_raw(
        cls, simulation_id: str, round_num: int, platform: str
    ) -> List[Dict[str, Any]]:
        """Read raw action dicts for a specific round from actions.jsonl (already written by OASIS)."""
        sim_dir = cls._get_run_state_dir(simulation_id)
        log_path = os.path.join(sim_dir, platform, "actions.jsonl")
        if not os.path.exists(log_path):
            return []
        results: List[Dict[str, Any]] = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if "event_type" not in d and d.get("round") == round_num:
                        results.append(d)
                except json.JSONDecodeError:
                    pass
        return results

    @classmethod
    def _check_all_platforms_completed(cls, state: SimulationRunState) -> bool:
        """
        Check if all enabled platforms have completed
        
        Detects enabled platforms by checking for actions.jsonl presence.
        
        Returns:
            True if all enabled platforms completed
        """
        sim_dir = cls._get_run_state_dir(state.simulation_id)
        
        twitter_log_exists = os.path.exists(os.path.join(sim_dir, "twitter", "actions.jsonl"))
        reddit_log_exists = os.path.exists(os.path.join(sim_dir, "reddit", "actions.jsonl"))
        
        all_completed = True
        
        if twitter_log_exists and not state.twitter_completed:
            all_completed = False
        if reddit_log_exists and not state.reddit_completed:
            all_completed = False
            
        return all_completed

    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        default_platform: Optional[str] = None,
        platform_filter: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        Reads actions from a single action file.
        
        Args:
            file_path: Path to the action log file.
            default_platform: Default platform (used when the action record does not have a 'platform' field).
            platform_filter: Filter by platform.
            agent_id: Filter by Agent ID.
            round_num: Filter by round number.
        """
        if not os.path.exists(file_path):
            return []
        
        actions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Skip non-action records (e.g., simulation_start, round_start, round_end events)
                    if "event_type" in data:
                        continue
                    
                    # Skip records without agent_id (non-Agent actions)
                    if "agent_id" not in data:
                        continue
                    
                    # Get platform: prioritize 'platform' in record, otherwise use default platform
                    record_platform = data.get("platform") or default_platform or ""
                    
                    # Filter
                    if platform_filter and record_platform != platform_filter:
                        continue
                    if agent_id is not None and data.get("agent_id") != agent_id:
                        continue
                    if round_num is not None and data.get("round") != round_num:
                        continue
                    
                    actions.append(AgentAction(
                        round_num=data.get("round", 0),
                        timestamp=data.get("timestamp", ""),
                        platform=record_platform,
                        agent_id=data.get("agent_id", 0),
                        agent_name=data.get("agent_name", ""),
                        action_type=data.get("action_type", ""),
                        action_args=data.get("action_args", {}),
                        result=data.get("result"),
                        success=data.get("success", True),
                    ))
                    
                except json.JSONDecodeError:
                    continue
        
        return actions
    
    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None,
        include_followers: bool = True,
    ) -> List[AgentAction]:
        """
        Get the complete action history for all platforms (without pagination limit).

        Args:
            simulation_id: Simulation ID.
            platform: Filter by platform (twitter/reddit).
            agent_id: Filter by Agent.
            round_num: Filter by round number.
            include_followers: Whether to include follower actions from follower_actions.jsonl.

        Returns:
            Complete list of actions (sorted by timestamp, newest first).
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        actions = []

        # Read Twitter action file (automatically set platform to twitter based on file path)
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        if not platform or platform == "twitter":
            actions.extend(cls._read_actions_from_file(
                twitter_actions_log,
                default_platform="twitter",
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            ))

        # Read Reddit action file (automatically set platform to reddit based on file path)
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        if not platform or platform == "reddit":
            actions.extend(cls._read_actions_from_file(
                reddit_actions_log,
                default_platform="reddit",
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            ))

        # If platform-specific files don't exist, try reading the old single file format
        if not actions:
            actions_log = os.path.join(sim_dir, "actions.jsonl")
            actions = cls._read_actions_from_file(
                actions_log,
                default_platform=None,
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            )

        # Append follower actions if requested
        if include_followers:
            for plat in ("twitter", "reddit"):
                if platform and platform != plat:
                    continue
                follower_log = os.path.join(sim_dir, plat, "follower_actions.jsonl")
                actions.extend(cls._read_actions_from_file(
                    follower_log,
                    default_platform=plat,
                    platform_filter=platform,
                    agent_id=agent_id,
                    round_num=round_num
                ))

        # Sort by timestamp (newest first)
        actions.sort(key=lambda x: x.timestamp, reverse=True)

        return actions
    
    @classmethod
    def get_actions(
        cls,
        simulation_id: str,
        limit: int = 100,
        offset: int = 0,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        Get action history (with pagination).
        
        Args:
            simulation_id: Simulation ID.
            limit: Limit on the number of results.
            offset: Offset for pagination.
            platform: Filter by platform.
            agent_id: Filter by Agent.
            round_num: Filter by round number.
            
        Returns:
            List of actions.
        """
        actions = cls.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        # Pagination
        return actions[offset:offset + limit]
    
    @classmethod
    def get_timeline(
        cls,
        simulation_id: str,
        start_round: int = 0,
        end_round: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get simulation timeline (summarized by round).
        
        Args:
            simulation_id: Simulation ID.
            start_round: Starting round.
            end_round: Ending round.
            
        Returns:
            Summary information for each round.
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        # Group by round
        rounds: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            round_num = action.round_num
            
            if round_num < start_round:
                continue
            if end_round is not None and round_num > end_round:
                continue
            
            if round_num not in rounds:
                rounds[round_num] = {
                    "round_num": round_num,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "active_agents": set(),
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            r = rounds[round_num]
            
            if action.platform == "twitter":
                r["twitter_actions"] += 1
            else:
                r["reddit_actions"] += 1
            
            r["active_agents"].add(action.agent_id)
            r["action_types"][action.action_type] = r["action_types"].get(action.action_type, 0) + 1
            r["last_action_time"] = action.timestamp
        
        # Convert to list
        result = []
        for round_num in sorted(rounds.keys()):
            r = rounds[round_num]
            result.append({
                "round_num": round_num,
                "twitter_actions": r["twitter_actions"],
                "reddit_actions": r["reddit_actions"],
                "total_actions": r["twitter_actions"] + r["reddit_actions"],
                "active_agents_count": len(r["active_agents"]),
                "active_agents": list(r["active_agents"]),
                "action_types": r["action_types"],
                "first_action_time": r["first_action_time"],
                "last_action_time": r["last_action_time"],
            })
        
        return result
    
    @classmethod
    def get_agent_stats(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """
        Get statistics for each agent.
        
        Returns:
            List of agent stats.
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        agent_stats: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            agent_id = action.agent_id
            
            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": action.agent_name,
                    "total_actions": 0,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            stats = agent_stats[agent_id]
            stats["total_actions"] += 1
            
            if action.platform == "twitter":
                stats["twitter_actions"] += 1
            else:
                stats["reddit_actions"] += 1
            
            stats["action_types"][action.action_type] = stats["action_types"].get(action.action_type, 0) + 1
            stats["last_action_time"] = action.timestamp
        
        # Sort by total actions
        result = sorted(agent_stats.values(), key=lambda x: x["total_actions"], reverse=True)
        
        return result
    
    @classmethod
    def cleanup_simulation_logs(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Clean up simulation run logs (used to force restart a simulation).
        
        The following files will be deleted:
        - run_state.json
        - twitter/actions.jsonl
        - reddit/actions.jsonl
        - simulation.log
        - stdout.log / stderr.log
        - twitter_simulation.db (simulation database)
        - reddit_simulation.db (simulation database)
        - env_status.json (environment status)
        
        Note: Configuration files (simulation_config.json) and profile files will not be deleted.
        
        Args:
            simulation_id: Simulation ID.
            
        Returns:
            Cleanup result information.
        """
        import shutil
        
        sim_dir = cls._get_run_state_dir(simulation_id)
        
        if not os.path.exists(sim_dir):
            return {"success": True, "message": "Simulation directory does not exist, no cleanup needed"}
        
        cleaned_files = []
        errors = []
        
        # List of files to delete (including database files)
        files_to_delete = [
            "run_state.json",
            "simulation.log",
            "stdout.log",
            "stderr.log",
            "twitter_simulation.db",  # Twitter platform database
            "reddit_simulation.db",   # Reddit platform database
            "env_status.json",        # Environment status file
        ]
        
        # List of directories to clean (including action logs)
        dirs_to_clean = ["twitter", "reddit"]
        
        # Delete files
        for filename in files_to_delete:
            file_path = os.path.join(sim_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(filename)
                except Exception as e:
                    errors.append(f"Failed to delete {filename}: {str(e)}")
        
        # Clean up action logs in platform directories
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(sim_dir, dir_name)
            if os.path.exists(dir_path):
                for log_name in ("actions.jsonl", "follower_actions.jsonl"):
                    log_file = os.path.join(dir_path, log_name)
                    if os.path.exists(log_file):
                        try:
                            os.remove(log_file)
                            cleaned_files.append(f"{dir_name}/{log_name}")
                        except Exception as e:
                            errors.append(f"Failed to delete {dir_name}/{log_name}: {str(e)}")
        
        # Clean up run state in memory
        if simulation_id in cls._run_states:
            del cls._run_states[simulation_id]
        
        logger.info(f"Simulation log cleanup completed: {simulation_id}, deleted files: {cleaned_files}")
        
        return {
            "success": len(errors) == 0,
            "cleaned_files": cleaned_files,
            "errors": errors if errors else None
        }
    
    # Flag to prevent duplicate cleanup
    _cleanup_done = False
    
    @classmethod
    def _terminate_process(cls, process: subprocess.Popen, simulation_id: str, timeout: int = 10):
        """
        Cross-platform termination of process and children
        
        Args:
            process: Process to terminate
            simulation_id: Simulation ID
            timeout: Timeout to wait for exit
        """
        if IS_WINDOWS:
            # Windows: use taskkill to terminate process tree
            # /F = Force, /T = Tree
            logger.info(f"Terminating process tree (Windows): simulation={simulation_id}, pid={process.pid}")
            try:
                # Try graceful termination first
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T'],
                    capture_output=True,
                    timeout=5
                )
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # Force termination
                    logger.warning(f"Process unresponsive, force terminating: {simulation_id}")
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(process.pid), '/T'],
                        capture_output=True,
                        timeout=5
                    )
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"taskkill failed, trying terminate: {e}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            # Unix: use process group termination
            pgid = os.getpgid(process.pid)
            logger.info(f"Terminating process group (Unix): simulation={simulation_id}, pgid={pgid}")
            
            # Send SIGTERM to entire process group
            os.killpg(pgid, signal.SIGTERM)
            
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force SIGKILL if still running
                logger.warning(f"Process group unresponsive to SIGTERM, force killing: {simulation_id}")
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=5)

    @classmethod
    def cleanup_all_simulations(cls):
        """
        Cleanup all running simulation processes.
        
        Called when the server shuts down to ensure all child processes are terminated.
        """
        # Prevent duplicate cleanup
        if cls._cleanup_done:
            return
        cls._cleanup_done = True
        
        # Check if there is anything to clean up (avoid printing useless logs for empty processes)
        has_processes = bool(cls._processes)
        has_updaters = bool(cls._graph_memory_enabled)
        
        if not has_processes and not has_updaters:
            return  # Nothing to clean up, return silently
        
        logger.info("Cleaning up all simulation processes...")
        
        # First stop all graph memory updaters (stop_all handles logging internally)
        try:
            ZepGraphMemoryManager.stop_all()
        except Exception as e:
            logger.error(f"Failed to stop graph memory updaters: {e}")
        cls._graph_memory_enabled.clear()
        
        # Copy dictionary to avoid modification during iteration
        processes = list(cls._processes.items())
        
        for simulation_id, process in processes:
            try:
                if process.poll() is None:  # Process is still running
                    logger.info(f"Terminating simulation process: {simulation_id}, pid={process.pid}")
                    
                    try:
                        # Use cross-platform process termination method
                        cls._terminate_process(process, simulation_id, timeout=5)
                    except (ProcessLookupError, OSError):
                        # Process might already be gone, try to terminate directly
                        try:
                            process.terminate()
                            process.wait(timeout=3)
                        except Exception:
                            process.kill()
                    
                    # Update run_state.json
                    state = cls.get_run_state(simulation_id)
                    if state:
                        state.runner_status = RunnerStatus.INTERRUPTED
                        state.twitter_running = False
                        state.reddit_running = False
                        state.completed_at = datetime.now().isoformat()
                        state.error = "interrupted by server shutdown"
                        cls._save_run_state(state)
                        sync_observation_store(cls._get_run_state_dir(simulation_id), run_state=state.to_detail_dict())
                    
                    # Also update state.json, set status to stopped
                    try:
                        sim_dir = cls._get_run_state_dir(simulation_id)
                        state_file = os.path.join(sim_dir, "state.json")
                        logger.info(f"Attempting to update state.json: {state_file}")
                        if os.path.exists(state_file):
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state_data = json.load(f)
                            state_data['status'] = 'interrupted'
                            state_data['updated_at'] = datetime.now().isoformat()
                            with open(state_file, 'w', encoding='utf-8') as f:
                                json.dump(state_data, f, indent=2, ensure_ascii=False)
                            logger.info(f"Updated state.json status to interrupted: {simulation_id}")
                        else:
                            logger.warning(f"state.json does not exist: {state_file}")
                    except Exception as state_err:
                        logger.warning(f"Failed to update state.json: {simulation_id}, error={state_err}")
                        
            except Exception as e:
                logger.error(f"Failed to clean up process: {simulation_id}, error={e}")
        
        # Clean up file handles
        for simulation_id, file_handle in list(cls._stdout_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        
        for simulation_id, file_handle in list(cls._stderr_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stderr_files.clear()
        
        # Clean up state in memory
        cls._processes.clear()
        cls._action_queues.clear()
        
        logger.info("Simulation process cleanup completed")
    
    @classmethod
    def register_cleanup(cls):
        """
        Register cleanup function.
        
        Called when the Flask app starts to ensure all simulation processes are cleaned up when the server shuts down.
        """
        global _cleanup_registered
        
        if _cleanup_registered:
            return
        
        # In Flask debug mode, only register cleanup in the reloader sub-process (the process actually running the app).
        # WERKZEUG_RUN_MAIN=true indicates it is the reloader sub-process.
        # If not in debug mode, there is no such environment variable, and it still needs to be registered.
        is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('WERKZEUG_RUN_MAIN') is not None
        
        # In debug mode, only register in the reloader sub-process; in non-debug mode, always register.
        if is_debug_mode and not is_reloader_process:
            _cleanup_registered = True  # Mark as registered to prevent child processes from trying again
            return
        
        # Save original signal handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        # SIGHUP only exists on Unix systems (macOS/Linux), not Windows
        original_sighup = None
        has_sighup = hasattr(signal, 'SIGHUP')
        if has_sighup:
            original_sighup = signal.getsignal(signal.SIGHUP)
        
        def cleanup_handler(signum=None, frame=None):
            """Signal handler: first clean up simulation processes, then call original handler"""
            # Only log if there are processes to clean up
            if cls._processes or cls._graph_memory_enabled:
                logger.info(f"Received signal {signum}, starting cleanup...")
            cls.cleanup_all_simulations()
            
            # Call the original signal handler to allow Flask to exit gracefully
            if signum == signal.SIGINT and callable(original_sigint):
                original_sigint(signum, frame)
            elif signum == signal.SIGTERM and callable(original_sigterm):
                original_sigterm(signum, frame)
            elif has_sighup and signum == signal.SIGHUP:
                # SIGHUP: sent when terminal closes
                if callable(original_sighup):
                    original_sighup(signum, frame)
                else:
                    # Default behavior: exit normally
                    sys.exit(0)
            else:
                # If original handler is not callable (e.g., SIG_DFL), use default behavior
                raise KeyboardInterrupt
        
        # Register atexit handler (as a fallback)
        atexit.register(cls.cleanup_all_simulations)
        
        # Register signal handlers (only in the main thread)
        try:
            # SIGTERM: default signal for kill command
            signal.signal(signal.SIGTERM, cleanup_handler)
            # SIGINT: Ctrl+C
            signal.signal(signal.SIGINT, cleanup_handler)
            # SIGHUP: terminal close (Unix systems only)
            if has_sighup:
                signal.signal(signal.SIGHUP, cleanup_handler)
        except ValueError:
            # Not in main thread, can only use atexit
            logger.warning("Cannot register signal handlers (not in main thread), only using atexit")
        
        _cleanup_registered = True
    
    @classmethod
    def get_running_simulations(cls) -> List[str]:
        """
        Get a list of all running simulation IDs.
        """
        running = []
        for sim_id, process in cls._processes.items():
            if process.poll() is None:
                running.append(sim_id)
        return running
    
    # ============== Interview Functionality ==============
    
    @classmethod
    def check_env_alive(cls, simulation_id: str) -> bool:
        """
        Check if the simulation environment is alive (can receive Interview commands).

        Args:
            simulation_id: Simulation ID.

        Returns:
            True if the environment is alive, False if it is closed.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            return False

        ipc_client = SimulationIPCClient(sim_dir)
        return ipc_client.check_env_alive()

    @classmethod
    def get_env_status_detail(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Get detailed status information of the simulation environment.

        Args:
            simulation_id: Simulation ID.

        Returns:
            Status details dictionary containing status, twitter_available, reddit_available, timestamp.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        status_file = os.path.join(sim_dir, "env_status.json")
        
        default_status = {
            "status": "stopped",
            "twitter_available": False,
            "reddit_available": False,
            "timestamp": None
        }
        
        if not os.path.exists(status_file):
            return default_status
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            return {
                "status": status.get("status", "stopped"),
                "twitter_available": status.get("twitter_available", False),
                "reddit_available": status.get("reddit_available", False),
                "timestamp": status.get("timestamp")
            }
        except (json.JSONDecodeError, OSError):
            return default_status

    @classmethod
    def interview_agent(
        cls,
        simulation_id: str,
        agent_id: int,
        prompt: str,
        platform: str = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Interview a single Agent.

        Args:
            simulation_id: Simulation ID.
            agent_id: Agent ID.
            prompt: Interview question.
            platform: Specific platform (optional).
                - "twitter": Only interview on Twitter platform.
                - "reddit": Only interview on Reddit platform.
                - None: Interview on both platforms simultaneously in dual-platform simulations, returning integrated results.
            timeout: Timeout in seconds.

        Returns:
            Interview result dictionary.

        Raises:
            ValueError: Simulation does not exist or environment is not running.
            TimeoutError: Wait for response timed out.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Simulation environment is not running or has been closed, cannot perform Interview: {simulation_id}")

        logger.info(f"Sending Interview command: simulation_id={simulation_id}, agent_id={agent_id}, platform={platform}")

        response = ipc_client.send_interview(
            agent_id=agent_id,
            prompt=prompt,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "agent_id": agent_id,
                "prompt": prompt,
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "agent_id": agent_id,
                "prompt": prompt,
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_agents_batch(
        cls,
        simulation_id: str,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Batch interview multiple agents.

        Args:
            simulation_id: Simulation ID.
            interviews: List of interviews, each element containing {"agent_id": int, "prompt": str, "platform": str(optional)}.
            platform: Default platform (optional, will be overridden by platform in each interview item).
                - "twitter": Default to only interview on Twitter platform.
                - "reddit": Default to only interview on Reddit platform.
                - None: Each agent is interviewed on both platforms simultaneously in dual-platform simulations.
            timeout: Timeout in seconds.

        Returns:
            Batch interview results dictionary.

        Raises:
            ValueError: Simulation does not exist or environment is not running.
            TimeoutError: Wait for response timed out.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Simulation environment is not running or has been closed, cannot perform Interview: {simulation_id}")

        logger.info(f"Sending batch Interview command: simulation_id={simulation_id}, count={len(interviews)}, platform={platform}")

        response = ipc_client.send_batch_interview(
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "interviews_count": len(interviews),
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "interviews_count": len(interviews),
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_all_agents(
        cls,
        simulation_id: str,
        prompt: str,
        platform: str = None,
        timeout: float = 180.0
    ) -> Dict[str, Any]:
        """
        Interview all Agents (global interview).

        Interviews all agents in the simulation with the same question.

        Args:
            simulation_id: Simulation ID.
            prompt: Interview question (all agents use the same question).
            platform: Specific platform (optional).
                - "twitter": Only interview on Twitter platform.
                - "reddit": Only interview on Reddit platform.
                - None: Each agent is interviewed on both platforms simultaneously in dual-platform simulations.
            timeout: Timeout in seconds.

        Returns:
            Global interview results dictionary.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        # Get all agent info from config file
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"Simulation config does not exist: {simulation_id}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        agent_configs = config.get("agent_configs", [])
        if not agent_configs:
            raise ValueError(f"No agents in simulation config: {simulation_id}")

        # Build batch interview list
        interviews = []
        for agent_config in agent_configs:
            agent_id = agent_config.get("agent_id")
            if agent_id is not None:
                interviews.append({
                    "agent_id": agent_id,
                    "prompt": prompt
                })

        logger.info(f"Sending global Interview command: simulation_id={simulation_id}, agent_count={len(interviews)}, platform={platform}")

        return cls.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )
    
    @classmethod
    def close_simulation_env(
        cls,
        simulation_id: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Close the simulation environment (instead of stopping the simulation process).
        
        Sends a close environment command to the simulation, letting it exit the wait-for-command mode gracefully.
        
        Args:
            simulation_id: Simulation ID.
            timeout: Timeout in seconds.
            
        Returns:
            Operation result dictionary.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        ipc_client = SimulationIPCClient(sim_dir)
        
        if not ipc_client.check_env_alive():
            return {
                "success": True,
                "message": "Environment already closed"
            }
        
        logger.info(f"Sending close environment command: simulation_id={simulation_id}")
        
        try:
            response = ipc_client.send_close_env(timeout=timeout)
            
            return {
                "success": response.status.value == "completed",
                "message": "Environment close command sent",
                "result": response.result,
                "timestamp": response.timestamp
            }
        except TimeoutError:
            # Timeout might be because the environment is already closing
            return {
                "success": True,
                "message": "Environment close command sent (wait for response timeout, environment may be closing)"
            }
    
    @classmethod
    def _get_interview_history_from_db(
        cls,
        db_path: str,
        platform_name: str,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get interview history from a single database."""
        import sqlite3
        
        if not os.path.exists(db_path):
            return []
        
        results = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if agent_id is not None:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview' AND user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (agent_id, limit))
            else:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview'
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            for user_id, info_json, created_at in cursor.fetchall():
                try:
                    info = json.loads(info_json) if info_json else {}
                except json.JSONDecodeError:
                    info = {"raw": info_json}
                
                results.append({
                    "agent_id": user_id,
                    "response": info.get("response", info),
                    "prompt": info.get("prompt", ""),
                    "timestamp": created_at,
                    "platform": platform_name
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to read Interview history ({platform_name}): {e}")
        
        return results

    @classmethod
    def get_interview_history(
        cls,
        simulation_id: str,
        platform: str = None,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get Interview history records (read from database).
        
        Args:
            simulation_id: Simulation ID.
            platform: Platform type (reddit/twitter/None).
                - "reddit": Only get history for Reddit platform.
                - "twitter": Only get history for Twitter platform.
                - None: Get all history for both platforms.
            agent_id: Specific Agent ID (optional, only get history for this Agent).
            limit: Limit on the number of results per platform.
            
        Returns:
            List of Interview history records.
        """
        sim_dir = cls._get_run_state_dir(simulation_id)
        
        results = []
        
        # Determine platforms to query
        if platform in ("reddit", "twitter"):
            platforms = [platform]
        else:
            # Query both platforms when platform is not specified
            platforms = ["twitter", "reddit"]
        
        for p in platforms:
            db_path = os.path.join(sim_dir, f"{p}_simulation.db")
            platform_results = cls._get_interview_history_from_db(
                db_path=db_path,
                platform_name=p,
                agent_id=agent_id,
                limit=limit
            )
            results.extend(platform_results)
        
        # Sort by timestamp descending
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit total count if multiple platforms were queried
        if len(platforms) > 1 and len(results) > limit:
            results = results[:limit]
        
        return results

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> SimulationRunState:
        """Stop a live run without allowing the monitor to relabel it failed."""
        state = cls.get_run_state(simulation_id)
        if state is None:
            raise ValueError(f"Simulation run does not exist: {simulation_id}")

        terminal_statuses = {
            RunnerStatus.STOPPED,
            RunnerStatus.COMPLETED,
            RunnerStatus.INTERRUPTED,
            RunnerStatus.FAILED,
        }
        if state.runner_status in terminal_statuses:
            return state
        if state.runner_status not in {
            RunnerStatus.STARTING,
            RunnerStatus.RUNNING,
            RunnerStatus.PAUSED,
            RunnerStatus.STOPPING,
        }:
            raise ValueError(
                f"Simulation is not running: {simulation_id}, "
                f"status={state.runner_status.value}"
            )

        state.runner_status = RunnerStatus.STOPPING
        cls._save_run_state(state)

        process = cls._processes.get(simulation_id)
        if process and process.poll() is None:
            try:
                cls._terminate_process(process, simulation_id)
            except (ProcessLookupError, OSError):
                # The process exited between poll() and termination.
                pass
            except Exception as exc:
                logger.error(
                    "Failed to terminate process group for %s: %s",
                    simulation_id,
                    exc,
                )
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as fallback_exc:
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except Exception as kill_exc:
                        state.runner_status = RunnerStatus.FAILED
                        state.error = "runtime process could not be stopped"
                        state.completed_at = datetime.now().isoformat()
                        cls._save_run_state(state)
                        sync_observation_store(
                            cls._get_run_state_dir(simulation_id),
                            run_state=state.to_detail_dict(),
                        )
                        raise RuntimeError(
                            f"Failed to stop simulation runtime: {simulation_id}"
                        ) from kill_exc
                    logger.warning(
                        "Graceful fallback stop failed for %s: %s",
                        simulation_id,
                        fallback_exc,
                    )

        monitor = cls._monitor_threads.get(simulation_id)
        if (
            monitor
            and monitor is not threading.current_thread()
            and monitor.is_alive()
        ):
            monitor.join(timeout=3)

        state = cls._run_states.get(simulation_id, state)
        if state.runner_status not in {
            RunnerStatus.COMPLETED,
            RunnerStatus.INTERRUPTED,
            RunnerStatus.FAILED,
        }:
            state.runner_status = RunnerStatus.STOPPED
            state.error = None
            state.twitter_running = False
            state.reddit_running = False
            state.completed_at = state.completed_at or datetime.now().isoformat()
            cls._save_run_state(state)
            sync_observation_store(
                cls._get_run_state_dir(simulation_id),
                run_state=state.to_detail_dict(),
            )

        if not monitor or not monitor.is_alive():
            cls._release_runtime_resources(simulation_id)

        return state

