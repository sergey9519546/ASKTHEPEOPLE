"""
Zep Graph Memory Update Service
Dynamically updates Agent activities from the simulation into the Zep graph
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from ..utils.opinion_scorer import get_opinion_scorer

logger = get_logger('askthepeople.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """Agent activity record"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        """
        Convert activity to a text description that can be sent to Zep
        
        Uses a natural language description format so Zep can extract entities and relationships
        Does not add simulation-related prefixes to avoid misleading graph updates
        """
        # Generate different descriptions based on different action types
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
            "INTERVIEW": self._describe_interview,
        }
        
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        
        # Directly return 'agent name: activity description' format, do not add simulation prefix
        return f"{self.agent_name}: {description}"
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"published a post: '{content}'"
        return "published a post"
    
    def _describe_like_post(self) -> str:
        """Like post - contains original post and author info"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"liked {post_author}'s post: '{post_content}'"
        elif post_content:
            return f"liked a post: '{post_content}'"
        elif post_author:
            return f"liked a post by {post_author}"
        return "liked a post"
    
    def _describe_dislike_post(self) -> str:
        """Dislike post - contains original post and author info"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"disliked {post_author}'s post: '{post_content}'"
        elif post_content:
            return f"disliked a post: '{post_content}'"
        elif post_author:
            return f"disliked a post by {post_author}"
        return "disliked a post"
    
    def _describe_repost(self) -> str:
        """Repost - contains original post and author info"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        
        if original_content and original_author:
            return f"reposted {original_author}'s post: '{original_content}'"
        elif original_content:
            return f"reposted a post: '{original_content}'"
        elif original_author:
            return f"reposted a post by {original_author}"
        return "reposted a post"
    
    def _describe_quote_post(self) -> str:
        """Quote post - contains original post, author info, and quote comment"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")
        
        base = ""
        if original_content and original_author:
            base = f"quoted {original_author}'s post '{original_content}'"
        elif original_content:
            base = f"quoted a post '{original_content}'"
        elif original_author:
            base = f"quoted a post by {original_author}"
        else:
            base = "quoted a post"
        
        if quote_content:
            base += f", and commented: '{quote_content}'"
        return base
    
    def _describe_follow(self) -> str:
        """Follow user - contains followed user's name"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"followed user '{target_user_name}'"
        return "followed a user"
    
    def _describe_create_comment(self) -> str:
        """Create comment - contains comment content and commented post info"""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if content:
            if post_content and post_author:
                return f"commented under {post_author}'s post '{post_content}': '{content}'"
            elif post_content:
                return f"commented under post '{post_content}': '{content}'"
            elif post_author:
                return f"commented under {post_author}'s post: '{content}'"
            return f"commented: '{content}'"
        return "created a comment"
    
    def _describe_like_comment(self) -> str:
        """Like comment - contains comment content and author info"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"liked {comment_author}'s comment: '{comment_content}'"
        elif comment_content:
            return f"liked a comment: '{comment_content}'"
        elif comment_author:
            return f"liked a comment by {comment_author}"
        return "liked a comment"
    
    def _describe_dislike_comment(self) -> str:
        """Dislike comment - contains comment content and author info"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"disliked {comment_author}'s comment: '{comment_content}'"
        elif comment_content:
            return f"disliked a comment: '{comment_content}'"
        elif comment_author:
            return f"disliked a comment by {comment_author}"
        return "disliked a comment"
    
    def _describe_search(self) -> str:
        """Search posts - contains search keyword"""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"searched for '{query}'" if query else "performed a search"
    
    def _describe_search_user(self) -> str:
        """Search user - contains search keyword"""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"searched for user '{query}'" if query else "searched for a user"
    
    def _describe_mute(self) -> str:
        """Mute user - contains muted user's name"""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"muted user '{target_user_name}'"
        return "muted a user"
    
    def _describe_interview(self) -> str:
        """Interview or Reflection action"""
        prompt = self.action_args.get("prompt", "")
        is_reflection = self.action_args.get("is_reflection", False)
        
        if is_reflection:
            # For reflection, we want Zep to treat it as internal consolidation
            # The prompt is actually the 'reflection question', the response is the 'reflection content'
            # However, in ManualAction for INTERVIEW, the response is usually handled by OASIS
            # and may be in a different database field.
            return f"reflected on recent events and updated their personal perspective: '{prompt}'"
        
        if prompt:
            return f"responded to an interview question: '{prompt}'"
        return "participated in an interview"
    
    def _describe_generic(self) -> str:
        # Generate generic description for unknown action types
        return f"executed {self.action_type} operation"


class ZepGraphMemoryUpdater:
    """
    Zep Graph Memory Updater
    
    Monitors simulation actions log file, updates new agent activities to Zep graph in real-time.
    Groups by platform, accumulates BATCH_SIZE activities before batch sending to Zep.
    
    All meaningful behaviors are updated to Zep, action_args contains full context information:
    - Liked/disliked original post
    - Reposted/quoted original post
    - Followed/muted username
    - Liked/disliked original comment
    """
    
    # Batch send size (accumulation threshold per platform)
    BATCH_SIZE = 5
    
    # Platform name mapping (for console display)
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'World 1',
        'reddit': 'World 2',
    }
    
    # Send interval (seconds) to prevent rate limiting
    SEND_INTERVAL = 0.5
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, graph_id: str, simulation_id: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize updater
        
        Args:
            graph_id: Zep Graph ID
            simulation_id: Simulation ID (optional, for saving opinion data)
            api_key: Zep API Key (optional, defauts to config)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.api_key = api_key or Config.ZEP_API_KEY
        
        if not self.api_key:
            raise ValueError("ZEP_API_KEY not configured")
        
        self.client = Zep(api_key=self.api_key)
        
        # Opinion Scorer
        self.scorer = get_opinion_scorer() # Default context
        
        # Activity queue
        self._activity_queue: Queue = Queue()
        
        # Platform-grouped activity buffer (accumulates up to BATCH_SIZE per platform)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()
        
        # Control flags
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Statistics
        self._total_activities = 0  # Total activities added to queue
        self._total_sent = 0        # Batches successfully sent to Zep
        self._total_items_sent = 0  # Activities successfully sent to Zep
        self._failed_count = 0      # Failed batches count
        self._skipped_count = 0     # Skipped activities count (DO_NOTHING)
        
        logger.info(f"ZepGraphMemoryUpdater initialized: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")
    
    def _get_platform_display_name(self, platform: str) -> str:
        """Get platform display name"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        """Start background worker thread"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"ZepMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"ZepGraphMemoryUpdater started: graph_id={self.graph_id}")
    
    def stop(self):
        """Stop background worker thread"""
        self._running = False
        
        # Send remaining activities
        self._flush_remaining()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        
        logger.info(f"ZepGraphMemoryUpdater stopped: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")
    
    def add_activity(self, activity: AgentActivity):
        """
        Add an agent activity to the queue
        
        All meaningful behaviors added to the queue, including:
        - CREATE_POST
        - CREATE_COMMENT
        - QUOTE_POST
        - SEARCH_POSTS
        - SEARCH_USER
        - LIKE_POST/DISLIKE_POST
        - REPOST
        - FOLLOW
        - MUTE
        - LIKE_COMMENT/DISLIKE_COMMENT
        
        action_args will contain full context info (e.g., original post, username).
        
        Args:
            activity: Agent activity record
        """
        # Skip DO_NOTHING type activities
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(f"Added activity to Zep queue: {activity.agent_name} - {activity.action_type}")
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        Add activity from dictionary data
        
        Args:
            data: Parsed dict data from actions.jsonl
            platform: Platform name (twitter/reddit)
        """
        # Skip event type entries
        if "event_type" in data:
            return
        
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        self.add_activity(activity)
    
    def _worker_loop(self):
        """Background worker loop - batch send activities to Zep by platform"""
        while self._running or not self._activity_queue.empty():
            try:
                # Try to get activity from queue (timeout 1 second)
                try:
                    activity = self._activity_queue.get(timeout=1)
                    
                    # Add activity to corresponding platform buffer
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        # Check if platform reached batch size
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # Release lock before sending
                            self._send_batch_activities(batch, platform)
                            # Send interval to avoid rate limiting
                            time.sleep(self.SEND_INTERVAL)
                    
                except Empty:
                    pass
                    
            except Exception as e:
                logger.error(f"Worker loop exception: {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        Batch send activities to Zep graph (merged as single text)
        
        Args:
            activities: Agent activity list
            platform: Platform name
        """
        if not activities:
            return
        
        # Merge multiple activities into one text, separated by newline
        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)
        
        # Send with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text
                )
                
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"Successfully batch sent {len(activities)} {display_name}activities to graph {self.graph_id}")
                logger.debug(f"Batch content preview: {combined_text[:200]}...")
                
                # After successful batch send, score opinions in background
                # (We do it here to ensure we only score actions that were successfully processed)
                for activity in activities:
                    self._save_opinion(activity)
                    
                return
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Batch send to Zep failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Batch send to Zep failed, retried{self.MAX_RETRIES}times: {e}")
                    self._failed_count += 1

    def _save_opinion(self, activity: AgentActivity):
        """Score activity and save to opinions.jsonl if simulation_id is present"""
        if not self.simulation_id:
            return
            
        content = activity.action_args.get("content") or activity.action_args.get("prompt")
        if not content:
            return
            
        try:
            x, y, z, reason = self.scorer.score_text(content)
            
            # Save to opinions.jsonl
            simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, self.simulation_id)
            if not os.path.exists(simulation_dir):
                os.makedirs(simulation_dir, exist_ok=True)
                
            opinion_file = os.path.join(simulation_dir, "opinions.jsonl")
            opinion_data = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": activity.agent_id,
                "agent_name": activity.agent_name,
                "platform": activity.platform,
                "round": activity.round_num,
                "x": x,
                "y": y,
                "z": z,
                "reason": reason,
                "text_snippet": content[:100]
            }
            
            with open(opinion_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(opinion_data, ensure_ascii=False) + "\n")
                
            logger.debug(f"Saved opinion coord for {activity.agent_name}: ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Failed to save opinion: {e}")
    
    def _flush_remaining(self):
        """Send remaining activities in queue and buffers"""
        # Process remaining activities in queue, add to buffer first
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        # Then send remaining activities in platform buffers (even if under BATCH_SIZE)
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"Sending {display_name} platform's remaining {len(buffer)} activities")
                    self._send_batch_activities(buffer, platform)
            # Clear all buffers
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics info"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # Total activities added to queue
            "batches_sent": self._total_sent,            # Batches successfully sent
            "items_sent": self._total_items_sent,        # Activities successfully sent
            "failed_count": self._failed_count,          # Failed batches count
            "skipped_count": self._skipped_count,        # Skipped activities count (DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # Buffer sizes by platform
            "running": self._running,
        }


class ZepGraphMemoryManager:
    """
    Manage Zep Graph Memory Updaters for multiple simulations
    
    Each simulation can have its own updater instance
    """
    
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        """
        Create graph memory updater for simulation
        
        Args:
            simulation_id: Simulation ID
            graph_id: Zep Graph ID
            
        Returns:
            ZepGraphMemoryUpdater instance
        """
        with cls._lock:
            # If exists, stop the old one first
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            
            updater = ZepGraphMemoryUpdater(graph_id, simulation_id=simulation_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            
            logger.info(f"Created graph memory updater: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        """Get updater for simulation"""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        """Stop and remove updater for simulation"""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"Stopped graph memory updater: simulation_id={simulation_id}")
    
    # Flag to prevent repeated stop_all calls
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        """Stop all updaters"""
        # Prevent repeated calls
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"Failed to stop updater: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("Stopped all graph memory updaters")
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get all updaters statistics info"""
        return {
            sim_id: updater.get_stats() 
            for sim_id, updater in cls._updaters.items()
        }
