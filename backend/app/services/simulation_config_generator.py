"""
Simulation Configuration Generator.
Uses an LLM to automatically generate detailed simulation parameters from requirements, document text, and graph data.
Fully automated — no manual parameter tuning needed.

Uses a step-by-step generation strategy to avoid failures from overly long outputs:
1. Generate time configuration
2. Generate event configuration
3. Generate agent configurations in batches
4. Generate platform configuration
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from .role_normalizer import normalize_entity_type
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('askthepeople.simulation_config')

@dataclass
class AgentActivityConfig:
    """Activity configuration for a single agent."""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # Activity level (0.0-1.0)
    activity_level: float = 0.5
    
    # Post/comment frequency (expected per hour)
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # Active hours (24h, 0-23)
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # Response delay to trending events (simulated minutes)
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # Sentiment bias (-1.0 negative to 1.0 positive)
    sentiment_bias: float = 0.0
    
    # Stance on the simulation topic
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # Influence weight (probability of post being seen by other agents)
    influence_weight: float = 1.0

    # Expanded behavior contract consumed by runtime logic
    normalized_role: str = "entity"
    reaction_style: str = "measured"
    conflict_tolerance: float = 0.45
    authority_sensitivity: float = 0.4
    novelty_seeking: float = 0.45
    platform_preference: str = "both"


@dataclass  
class TimeSimulationConfig:
    """Time simulation configuration (based on typical daily activity patterns)."""
    # Total simulation duration in simulated hours
    total_simulation_hours: int = 72  # Default: 72 hours (3 days)
    
    # Time represented per round (simulated minutes) — default 60 mins for faster time flow
    minutes_per_round: int = 60
    
    # Range of agents activated per hour
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # Peak hours (19-22h — most active period)
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # Off-peak hours (0-5h — almost no activity)
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05
    
    # Morning hours
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # Work hours
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """Event configuration for the simulation."""
    # Seed posts that trigger the simulation at the start
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Scheduled events triggered at specific times
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Trending topic keywords
    hot_topics: List[str] = field(default_factory=list)
    
    # Narrative direction for opinion flow
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """Platform-specific configuration."""
    platform: str  # twitter or reddit
    
    # Recommendation algorithm weights
    recency_weight: float = 0.4
    popularity_weight: float = 0.3
    relevance_weight: float = 0.3
    
    # Viral spread threshold (interactions needed to trigger diffusion)
    viral_threshold: int = 10
    
    # Echo chamber effect strength (clustering of similar opinions)
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """Complete simulation parameter configuration."""
    # Basic info
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # Time configuration
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agent configuration list
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # Event configuration
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # Platform configurations
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None

    # Execution contract extensions
    context_profile: Dict[str, Any] = field(default_factory=dict)
    network_bootstrap: Dict[str, Any] = field(default_factory=dict)
    event_schedule: List[Dict[str, Any]] = field(default_factory=list)
    bootstrap_posts: List[Dict[str, Any]] = field(default_factory=list)
    platform_profiles: Dict[str, Any] = field(default_factory=dict)
    
    # LLM config
    llm_model: str = ""
    llm_base_url: str = ""
    
    # Generation metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM reasoning explanation
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "context_profile": self.context_profile,
            "network_bootstrap": self.network_bootstrap,
            "event_schedule": self.event_schedule,
            "bootstrap_posts": self.bootstrap_posts,
            "platform_profiles": self.platform_profiles,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    Intelligent Simulation Configuration Generator.
    
    Uses an LLM to analyse simulation requirements, document content, and entity graph data,
    then automatically generates optimal simulation parameters.
    
    Step-by-step generation strategy:
    1. Generate time config and event config (lightweight)
    2. Generate agent configs in batches (10-20 per batch)
    3. Generate platform config
    """
    
    # Maximum context length in characters
    MAX_CONTEXT_LENGTH = 50000
    # Agents generated per batch
    AGENTS_PER_BATCH = 15
    
    # Context truncation limits per step (characters)
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # Time config
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # Event config
    ENTITY_SUMMARY_LENGTH = 300          # Entity summary
    AGENT_SUMMARY_LENGTH = 300           # Entity summary in agent configs
    ENTITIES_PER_TYPE_DISPLAY = 20       # Entities shown per type
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        canonical_agents: Optional[List[Dict[str, Any]]] = None,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        Intelligently generate a complete simulation configuration (step-by-step).
        
        Args:
            simulation_id: Simulation ID
            project_id: Project ID
            graph_id: Graph ID
            simulation_requirement: Simulation requirement description
            document_text: Source document text
            entities: Filtered list of entities
            enable_twitter: Whether to enable Twitter platform
            enable_reddit: Whether to enable Reddit platform
            progress_callback: Progress callback (current_step, total_steps, message)
            
        Returns:
            SimulationParameters: Complete simulation parameters
        """
        logger.info(f"Starting simulation config generation: simulation_id={simulation_id}, entity_count={len(entities)}")
        canonical_agents = canonical_agents or []
        
        # Calculate total steps
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # time config + event config + N agent batches + platform config
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. Build base context
        context_profile = self._infer_context_profile(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities,
        )

        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities,
            context_profile=context_profile,
        )
        
        reasoning_parts = []
        
        # ========== Step 1: Generate time config ==========
        report_progress(1, "Generating time configuration...")
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"TimeConfig: {time_config_result.get('reasoning', 'ok')}")
        
        # ========== Step 2: Generate event config ==========
        report_progress(2, "Generating event configuration and hot topics...")
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"EventConfig: {event_config_result.get('reasoning', 'ok')}")
        
        # ========== Steps 3-N: Generate agent configs in batches ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                f"Generating agent configs ({start_idx + 1}-{end_idx}/{len(entities)})..."
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement,
                canonical_agents=canonical_agents[start_idx:end_idx] if canonical_agents else None,
                context_profile=context_profile,
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(f"AgentConfigs: successfully generated {len(all_agent_configs)}")
        
        # ========== Assign initial post publishers ==========
        logger.info("Assigning suitable publisher agents to initial posts...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(f"InitialPosts: {assigned_count} posts assigned publishers")
        
        # ========== Final step: Generate platform config ==========
        report_progress(total_steps, "Generating platform configuration...")
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        # Build final parameters
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            context_profile=context_profile,
            network_bootstrap=self._build_network_bootstrap(all_agent_configs, enable_twitter, enable_reddit),
            event_schedule=self._build_event_schedule(event_config, context_profile, all_agent_configs),
            bootstrap_posts=list(event_config.initial_posts),
            platform_profiles=self._build_platform_profiles(context_profile, enable_twitter, enable_reddit),
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"Simulation config generation complete: {len(params.agent_configs)} agent configs")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        context_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build LLM context string, truncated to the maximum allowed length."""
        
        # Entity summary block
        entity_summary = self._summarize_entities(entities)
        
        # Assemble context
        context_parts = [
            f"## Simulation Requirement\n{simulation_requirement}",
            f"\n## Entities ({len(entities)} total)\n{entity_summary}",
        ]
        if context_profile:
            context_parts.append(f"\n## Context Profile\n{json.dumps(context_profile, ensure_ascii=False, indent=2)}")
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # 500-char buffer
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(document truncated)"
            context_parts.append(f"\n## Source Document\n{doc_text}")
        
        return "\n".join(context_parts)

    def _infer_context_profile(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
    ) -> Dict[str, Any]:
        source = f"{simulation_requirement}\n{document_text}".lower()
        labels = " ".join((e.get_entity_type() or "").lower() for e in entities)

        language = "en"
        country = "Unknown"
        region = "global"
        timezone = "UTC"
        activity_norm = "global_generic"
        confidence = 0.45
        reasoning = "Fallback global context used because locale signals were weak."

        if any("\u4e00" <= ch <= "\u9fff" for ch in simulation_requirement + document_text):
            language = "zh"
            confidence = 0.72
            reasoning = "Detected CJK characters in source material."
        elif any(keyword in source for keyword in ("espa", "mexico", "madrid", "latam", "argentina")):
            language = "es"
            confidence = 0.65
            reasoning = "Detected Spanish-language regional cues in source material."

        if "china" in source or "beijing" in source or "shanghai" in source:
            country = "China"
            region = "Asia"
            timezone = "Asia/Shanghai"
            activity_norm = "china_urban"
            confidence = max(confidence, 0.8)
            reasoning = "Detected China-specific geographic references."
        elif any(token in source for token in ("united states", "usa", "u.s.", "america", "california", "new york")):
            country = "United States"
            region = "North America"
            timezone = "America/Los_Angeles"
            activity_norm = "us_general"
            confidence = max(confidence, 0.78)
            reasoning = "Detected United States geographic references."
        elif any(token in source for token in ("uk", "united kingdom", "london", "britain")):
            country = "United Kingdom"
            region = "Europe"
            timezone = "Europe/London"
            activity_norm = "uk_general"
            confidence = max(confidence, 0.74)
            reasoning = "Detected UK geographic references."
        elif "reddit" in labels and "twitter" not in labels:
            confidence = max(confidence, 0.55)
            reasoning = "Platform mix suggests discussion-heavy, globally distributed behavior."

        return {
            "language": language,
            "country": country,
            "region": region,
            "timezone": timezone,
            "activity_norm": activity_norm,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
        }

    def _build_network_bootstrap(
        self,
        agent_configs: List[AgentActivityConfig],
        enable_twitter: bool,
        enable_reddit: bool,
    ) -> Dict[str, Any]:
        return {
            "enable_follow_bootstrap": True,
            "follow_density": round(min(0.65, max(0.15, len(agent_configs) / 120)), 2),
            "role_bias_rules": {
                "media": 0.8,
                "official": 0.55,
                "student": 0.72,
                "community": 0.78,
            },
            "relationship_affinity_rules": {
                "supportive": 0.85,
                "neutral": 0.55,
                "conflict": 0.35,
            },
            "platforms": {
                "twitter": enable_twitter,
                "reddit": enable_reddit,
            },
        }

    def _build_event_schedule(
        self,
        event_config: EventConfig,
        context_profile: Dict[str, Any],
        agent_configs: List[AgentActivityConfig],
    ) -> List[Dict[str, Any]]:
        schedule: List[Dict[str, Any]] = []
        if event_config.hot_topics:
            schedule.append(
                {
                    "trigger_round": 2,
                    "platforms": ["twitter", "reddit"],
                    "event_type": "topic_spike",
                    "payload": {"topics": event_config.hot_topics[:5]},
                    "targeting": {"roles": sorted({cfg.normalized_role for cfg in agent_configs})[:4]},
                    "reasoning": f"Derived from hot topics under {context_profile.get('activity_norm', 'global_generic')} context.",
                }
            )
        if event_config.initial_posts:
            first_post = event_config.initial_posts[0]
            schedule.append(
                {
                    "trigger_round": 4,
                    "platforms": ["twitter", "reddit"],
                    "event_type": "seed_post",
                    "payload": {"content": first_post.get("content", "")},
                    "targeting": {"poster_agent_id": first_post.get("poster_agent_id")},
                    "reasoning": "Carry the initial narrative forward with a second-wave reaction trigger.",
                }
            )
        return schedule

    def _build_platform_profiles(
        self,
        context_profile: Dict[str, Any],
        enable_twitter: bool,
        enable_reddit: bool,
    ) -> Dict[str, Any]:
        return {
            "twitter": {
                "enabled": enable_twitter,
                "language": context_profile.get("language", "en"),
                "style": "broadcast",
            },
            "reddit": {
                "enabled": enable_reddit,
                "language": context_profile.get("language", "en"),
                "style": "threaded_discussion",
            },
        }
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """Generate a structured entity summary grouped by type."""
        lines = []
        
        # Group by entity type
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)} total)")
            # 使用配置的显示数量和摘要长度
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... 还有 {len(type_entities) - display_count} 个")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """LLM call with retry logic and JSON repair."""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Lower temperature on each retry
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Check if output was truncated
                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # Attempt JSON parse
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed (attempt {attempt+1}): {str(e)[:80]}")
                    
                    # Attempt JSON repair
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLM call failed")
    
    def _fix_truncated_json(self, content: str) -> str:
        """Attempt to repair JSON truncated by token limits."""
        content = content.strip()
        
        # Count unclosed brackets
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # Close any dangling open string
        if content and content[-1] not in '",}]':
            content += '"'
        
        # Close brackets
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair a malformed config JSON string."""
        import re
        
        # Fix truncation first
        content = self._fix_truncated_json(content)
        
        # Extract JSON block
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # Remove newlines inside string values
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                # Strip all control characters and try again
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Generate time configuration using an LLM."""
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        # Max agents allowed (90% of total)
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""Based on the following simulation requirement, generate a time simulation configuration.

{context_truncated}

## Task
Please generate a time configuration in JSON format.

### General principles (for reference only, please adjust flexibly based on the specific event and participant group):
- User group is people from China, must conform to Beijing time activity habits.
- 0-5h (late night): almost no activity (multiplier 0.05)
- 6-8h (morning): gradually increasing activity (multiplier 0.4)
- 9-18h (work hours): moderate activity (multiplier 0.7)
- 19-22h (evening peak): highest activity (multiplier 1.5)
- 23h+: activity declining (multiplier 0.5)
- General trend: late night low, morning increasing, work hours moderate, evening peak.
- **Important**: The following example values are for reference only. You need to adjust the specific time periods according to the nature of the event and the characteristics of the participant group.
  - Example: student group peak might be 21-23h; media might be active all day; official agencies might only be active during working hours.
  - Example: breaking news events might cause late-night discussions, so off_peak_hours can be appropriately shortened.

### Return JSON format (no markdown)

Example:
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "Explanation for the time configuration for this event"
}}

Field descriptions:
- total_simulation_hours (int): Total simulation duration, 24-168 hours. Short for breaking events, long for sustained topics.
- minutes_per_round (int): Duration per round, 30-120 minutes, 60 minutes recommended.
- agents_per_hour_min (int): Minimum number of Agents activated per hour (value range: 1-{max_agents_allowed})
- agents_per_hour_max (int): Maximum number of Agents activated per hour (value range: 1-{max_agents_allowed})
- peak_hours (int array): Peak hours, adjust according to the event participation group.
- off_peak_hours (int array): Off-peak hours, usually late night and early morning.
- morning_hours (int array): Morning hours.
- work_hours (int array): Work hours.
- reasoning (string): Brief explanation of why it is configured this way."""

        system_prompt = "You are a social media simulation expert. Return in pure JSON format, time configuration should conform to typical activity habits."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Time config LLM generation failed: {e}, using defaults")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """Get default time configuration."""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # 1 hour per round, faster time flow
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "Using default time configuration (1 hour per round)"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """Parse the time configuration result, and ensure agents_per_hour values don't exceed total agents."""
        # Get original values
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        # Verify and clamp: Ensure it does not exceed the total number of agents
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) exceeds total agents ({num_entities}), corrected")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) exceeds total agents ({num_entities}), corrected")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # Ensure min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max, corrected to {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # Default 1 hour per round
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # Late night, almost no one
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """Generate event configuration."""
        
        # Get list of available entity types for LLM reference
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # List representative entities for each type
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # Truncate context based on configuration
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""Based on the following simulation requirement, generate the event configuration.

Simulation Requirement: {simulation_requirement}

{context_truncated}

## Available Entity Types and Examples
{type_info}

## Task
Generate the event configuration JSON:
- Extract trending topic keywords
- Describe public opinion narrative direction
- Design initial posts content, **each post must specify poster_type**

**Important**: poster_type MUST be chosen from the "Available Entity Types" above so the initial posts can be assigned to an appropriate Agent.
For example: Official statements should be posted by Official/University type, news by MediaOutlet, student opinions by Student.

Return JSON format (no markdown):
{{
    "hot_topics": ["keyword1", "keyword2", ...],
    "narrative_direction": "<description of opinion development direction>",
    "initial_posts": [
        {{"content": "Post content", "poster_type": "Entity type (must match available types)"}},
        ...
    ],
    "reasoning": "<brief explanation>"
}}"""

        system_prompt = "You are a public opinion analysis expert. Return pure JSON. Note that poster_type MUST match the available entity types exactly."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Event config LLM generation failed: {e}, using default configs")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Using default configurations"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """Parse event configuration results."""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        Assign appropriate poster Agents for initial posts.
        
        Matches best agent_id based on each post's poster_type.
        """
        if not event_config.initial_posts:
            return event_config
        
        # Index agents by entity type
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # Type aliases mapping (handling LLM output variations)
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # Track used indexes for each type to avoid repeating agents
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # Try matching agent
            matched_agent_id = None
            
            # 1. Exact match
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. Alias match
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. Fallback to highest influence agent if no match
            if matched_agent_id is None:
                logger.warning(f"Could not find matching Agent for poster_type '{poster_type}', fallback to highest influence Agent")
                if agent_configs:
                    # Sort by influence descending
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id,
                "poster_assignment_confidence": 0.9 if matched_agent_id is not None else 0.4,
                "poster_assignment_reason": (
                    f"Matched poster_type '{post.get('poster_type', 'Unknown')}' to agent_id={matched_agent_id}"
                    if matched_agent_id is not None else
                    "Fallback to highest influence agent because no role match was available."
                ),
            })
            
            logger.info(f"Assigned initial post: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str,
        canonical_agents: Optional[List[Dict[str, Any]]] = None,
        context_profile: Optional[Dict[str, Any]] = None,
    ) -> List[AgentActivityConfig]:
        """Generate Agent configurations in batches."""

        # Build entity info (using configured summary length)
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            canonical = canonical_agents[i] if canonical_agents and i < len(canonical_agents) else {}
            role_info = normalize_entity_type(e.get_entity_type())
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "normalized_role": canonical.get("source_entity_type_normalized", role_info["normalized_role"]),
                "summary": e.summary[:summary_len] if e.summary else "",
                "platform_preference": canonical.get("activity_seed", {}).get("platform_preference", "both"),
            })

        context_desc = context_profile or {
            "language": "en",
            "country": "Unknown",
            "timezone": "UTC",
            "activity_norm": "global_generic",
        }
        prompt = f"""Based on the following information, generate social media activity configurations for each entity.

Simulation Requirement: {simulation_requirement}

Context Profile: {json.dumps(context_desc, ensure_ascii=False)}

## Entity List
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## Task
Generate activity configuration for each entity. Note:
- Use the context profile to infer realistic local active hours.
- **Official Agencies** (University/GovernmentAgency): Low activity (0.1-0.3), active during work hours (9-17), slow response (60-240 mins), high influence (2.5-3.0)
- **Media** (MediaOutlet): Medium activity (0.4-0.6), active all day (8-23), fast response (5-30 mins), high influence (2.0-2.5)
- **Individuals** (Student/Person/Alumni): High activity (0.6-0.9), mainly active in evening (18-23), fast response (1-15 mins), low influence (0.8-1.2)
- **Public Figures/Experts**: Medium activity (0.4-0.6), medium-high influence (1.5-2.0)

Return JSON format (no markdown):
{{
    "agent_configs": [
        {{
            "agent_id": <must match input>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <posting frequency>,
            "comments_per_hour": <commenting frequency>,
            "active_hours": [<list of active hours for the inferred locale>],
            "response_delay_min": <minimum response delay in mins>,
            "response_delay_max": <maximum response delay in mins>,
            "sentiment_bias": <-1.0 to 1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <influence weight>,
            "reaction_style": "<measured/reactive/amplifying/cautious>",
            "conflict_tolerance": <0.0-1.0>,
            "authority_sensitivity": <0.0-1.0>,
            "novelty_seeking": <0.0-1.0>,
            "platform_preference": "<twitter/reddit/both>"
        }},
        ...
    ]
}}"""

        system_prompt = "You are a social media behavior analysis expert. Return pure JSON and follow the inferred locale rather than a fixed country default."
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent config batch LLM generation failed: {e}, using rule-based generation")
            llm_configs = {}
        
        # Build AgentActivityConfig objects
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # Use rule generation if LLM failed to generate
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0),
                normalized_role=cfg.get("normalized_role", normalize_entity_type(entity.get_entity_type())["normalized_role"]),
                reaction_style=cfg.get("reaction_style", "measured"),
                conflict_tolerance=cfg.get("conflict_tolerance", 0.45),
                authority_sensitivity=cfg.get("authority_sensitivity", 0.4),
                novelty_seeking=cfg.get("novelty_seeking", 0.45),
                platform_preference=cfg.get("platform_preference", "both"),
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """Generate a single Agent config based on normalized roles."""
        role_info = normalize_entity_type(entity.get_entity_type())
        entity_type = role_info["normalized_role"]
        
        if entity_type in ["institution", "government", "organization", "company"]:
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0,
                "normalized_role": entity_type,
                "reaction_style": "cautious",
                "conflict_tolerance": 0.18,
                "authority_sensitivity": 0.88,
                "novelty_seeking": 0.12,
                "platform_preference": "twitter",
            }
        elif entity_type in ["media", "journalist", "public_figure"]:
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5,
                "normalized_role": entity_type,
                "reaction_style": "amplifying",
                "conflict_tolerance": 0.58,
                "authority_sensitivity": 0.35,
                "novelty_seeking": 0.62,
                "platform_preference": "twitter",
            }
        elif entity_type in ["academic", "expert", "official"]:
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0,
                "normalized_role": entity_type,
                "reaction_style": "measured",
                "conflict_tolerance": 0.34,
                "authority_sensitivity": 0.62,
                "novelty_seeking": 0.32,
                "platform_preference": "both",
            }
        elif entity_type in ["student", "alumni", "activist", "community", "individual"]:
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8,
                "normalized_role": entity_type,
                "reaction_style": "reactive",
                "conflict_tolerance": 0.66,
                "authority_sensitivity": 0.24,
                "novelty_seeking": 0.7,
                "platform_preference": "reddit",
            }
        else:
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0,
                "normalized_role": entity_type,
                "reaction_style": "measured",
                "conflict_tolerance": 0.45,
                "authority_sensitivity": 0.4,
                "novelty_seeking": 0.45,
                "platform_preference": "both",
            }
    

