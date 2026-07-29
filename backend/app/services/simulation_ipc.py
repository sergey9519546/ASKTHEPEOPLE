"""
Simulation IPC Communication Module
Used for inter-process communication between Flask backend and simulation scripts

Implements simple command/response pattern via file system:
1. Flask writes commands to commands/ directory
2. Simulation script polls command directory, executes commands, and writes responses to responses/ directory
3. Flask polls response directory for results
"""

import os
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger('askthepeople.simulation_ipc')


class CommandType(str, Enum):
    """Command Type"""
    INTERVIEW = "interview"           # Single Agent Interview
    BATCH_INTERVIEW = "batch_interview"  # Batch Interview
    CLOSE_ENV = "close_env"           # Close Environment
    INJECT_POST = "inject_post"
    INJECT_EVENT = "inject_event"
    PAUSE_AFTER_ROUND = "pause_after_round"
    RESUME = "resume"
    STOP = "stop"


class CommandStatus(str, Enum):
    """Command Status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IPCCommand:
    """IPC Command"""
    command_id: str
    command_type: CommandType
    args: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "args": self.args,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCCommand':
        return cls(
            command_id=data["command_id"],
            command_type=CommandType(data["command_type"]),
            args=data.get("args", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )


@dataclass
class IPCResponse:
    """IPC Response"""
    command_id: str
    status: CommandStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCResponse':
        return cls(
            command_id=data["command_id"],
            status=CommandStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )


class SimulationIPCClient:
    """
    Simulation IPC Client (for Flask)
    
    Used to send commands to simulation processes and wait for responses
    """
    
    def __init__(self, simulation_dir: str):
        """
        Initialize IPC client
        
        Args:
            simulation_dir: Simulation data directory
        """
        self.simulation_dir = simulation_dir
        self.commands_dir = os.path.join(simulation_dir, "ipc_commands")
        self.responses_dir = os.path.join(simulation_dir, "ipc_responses")
        
        # Ensure directory exists
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def send_command(
        self,
        command_type: CommandType,
        args: Dict[str, Any],
        timeout: float = 60.0,
        poll_interval: float = 0.5
    ) -> IPCResponse:
        """
        Send command and wait for response
        
        Args:
            command_type: Command Type
            args: Command arguments
            timeout: Timeout (seconds)
            poll_interval: Polling interval (seconds)
            
        Returns:
            IPCResponse
            
        Raises:
            TimeoutError: Timeout waiting for response
        """
        command_id = str(uuid.uuid4())
        command = IPCCommand(
            command_id=command_id,
            command_type=command_type,
            args=args
        )
        
        # Write command file atomically using a temporary file
        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        tmp_command_file = os.path.join(self.commands_dir, f"{command_id}.tmp")
        with open(tmp_command_file, 'w', encoding='utf-8') as f:
            json.dump(command.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp_command_file, command_file)
        
        logger.info(f"Sending IPC Command: {command_type.value}, command_id={command_id}")
        
        # Wait for response
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(response_file):
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    response = IPCResponse.from_dict(response_data)
                    
                    # Clean up command and response files
                    try:
                        os.remove(command_file)
                        os.remove(response_file)
                    except OSError:
                        pass
                    
                    logger.info(f"Received IPC Response: command_id={command_id}, status={response.status.value}")
                    return response
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse response: {e}")
            
            time.sleep(poll_interval)
        
        # Timeout
        logger.error(f"Wait for IPC Response timeout: command_id={command_id}")
        
        # Clean up command file
        try:
            os.remove(command_file)
        except OSError:
            pass
        
        raise TimeoutError(f"Wait for command response timeout ({timeout}s)")
    
    def send_interview(
        self,
        agent_id: int,
        prompt: str,
        platform: str = None,
        timeout: float = 60.0
    ) -> IPCResponse:
        """
        Send single Agent interview command
        
        Args:
            agent_id: Agent ID
            prompt: Interview prompt
            platform: Target platform (optional)
                - "twitter": Only interview Twitter platform
                - "reddit": Only interview Reddit platform  
                - None: Interview both platforms if dual, or specific platform if single
            timeout: Timeout duration
            
        Returns:
            IPCResponse, result field contains interview results
        """
        args = {
            "agent_id": agent_id,
            "prompt": prompt
        }
        if platform:
            args["platform"] = platform
            
        return self.send_command(
            command_type=CommandType.INTERVIEW,
            args=args,
            timeout=timeout
        )
    
    def send_batch_interview(
        self,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> IPCResponse:
        """
        Send Batch Interview command
        
        Args:
            interviews: Interview list, each element contains {"agent_id": int, "prompt": str, "platform": str(optional)}
            platform: Default platform (optional, overridden by platform in each interview item)
                - "twitter": Default only interview Twitter platform
                - "reddit": Default only interview Reddit platform
                - None: Each Agent interviewed on both platforms if dual simulation
            timeout: Timeout duration
            
        Returns:
            IPCResponse, result field contains all interview results
        """
        args = {"interviews": interviews}
        if platform:
            args["platform"] = platform
            
        return self.send_command(
            command_type=CommandType.BATCH_INTERVIEW,
            args=args,
            timeout=timeout
        )
    
    def send_close_env(self, timeout: float = 30.0) -> IPCResponse:
        """
        Send Close Environment command
        
        Args:
            timeout: Timeout duration
            
        Returns:
            IPCResponse
        """
        return self.send_command(
            command_type=CommandType.CLOSE_ENV,
            args={},
            timeout=timeout
        )

    def send_runtime_control(
        self,
        command_type: CommandType,
        args: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> IPCResponse:
        return self.send_command(
            command_type=command_type,
            args=args or {},
            timeout=timeout,
        )

    def send_inject_event(
        self,
        event_text: str,
        platform: str = "parallel",
        agent_id: Optional[int] = None,
        timeout: float = 30.0,
    ) -> IPCResponse:
        """Inject breaking news or scenario event mid-simulation"""
        args = {
            "content": event_text,
            "platform": platform
        }
        if agent_id is not None:
            args["agent_id"] = agent_id
        return self.send_command(
            command_type=CommandType.INJECT_EVENT,
            args=args,
            timeout=timeout
        )

    def check_env_alive(self) -> bool:
        """
        Check if simulation environment is alive
        
        Determined by checking env_status.json file
        """
        status_file = os.path.join(self.simulation_dir, "env_status.json")
        if not os.path.exists(status_file):
            return False
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            return status.get("status") in {"alive", "running", "paused", "pausing_after_round"}
        except (json.JSONDecodeError, OSError):
            return False


class SimulationIPCServer:
    """
    Simulation IPC Server (for simulation scripts)
    
    Poll command directory, execute commands and return responses
    """
    
    def __init__(self, simulation_dir: str):
        """
        Initialize IPC server
        
        Args:
            simulation_dir: Simulation data directory
        """
        self.simulation_dir = simulation_dir
        self.commands_dir = os.path.join(simulation_dir, "ipc_commands")
        self.responses_dir = os.path.join(simulation_dir, "ipc_responses")
        
        # Ensure directory exists
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
        
        # Environment state
        self._running = False
    
    def start(self):
        """Mark server as running state"""
        self._running = True
        self._update_env_status("alive")
    
    def stop(self):
        """Mark server as stopped state"""
        self._running = False
        self._update_env_status("stopped")
    
    def _update_env_status(self, status: str):
        """Update environment state file atomically"""
        status_file = os.path.join(self.simulation_dir, "env_status.json")
        tmp_status_file = os.path.join(self.simulation_dir, "env_status.tmp")
        with open(tmp_status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        os.replace(tmp_status_file, status_file)
    
    def poll_commands(self) -> Optional[IPCCommand]:
        """
        Poll command directory, return first pending command
        
        Returns:
            IPCCommand or None
        """
        if not os.path.exists(self.commands_dir):
            return None
        
        # Sort command files by time
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                try:
                    command_files.append((filepath, os.path.getmtime(filepath)))
                except OSError:
                    continue
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return IPCCommand.from_dict(data)
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning(f"Failed to read command file: {filepath}, {e}")
                continue
        
        return None
    
    def send_response(self, response: IPCResponse):
        """
        Send response atomically
        
        Args:
            response: IPC Response
        """
        response_file = os.path.join(self.responses_dir, f"{response.command_id}.json")
        tmp_response_file = os.path.join(self.responses_dir, f"{response.command_id}.tmp")
        with open(tmp_response_file, 'w', encoding='utf-8') as f:
            json.dump(response.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp_response_file, response_file)
        
        # Delete command file
        command_file = os.path.join(self.commands_dir, f"{response.command_id}.json")
        try:
            if os.path.exists(command_file):
                os.remove(command_file)
        except OSError:
            pass
    
    def send_success(self, command_id: str, result: Dict[str, Any]):
        """Send success response"""
        self.send_response(IPCResponse(
            command_id=command_id,
            status=CommandStatus.COMPLETED,
            result=result
        ))
    
    def send_error(self, command_id: str, error: str):
        """Send error response"""
        self.send_response(IPCResponse(
            command_id=command_id,
            status=CommandStatus.FAILED,
            error=error
        ))
