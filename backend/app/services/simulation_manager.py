"""
OASIS Simulation Manager
Manages parallel Twitter and Reddit simulations
Uses preset scripts + LLM to intelligently generate configuration parameters
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.input_policy import (
    ARCHETYPE_COUNT_MAX,
    ARCHETYPE_EXPANSION_MAX,
    ENTITY_TYPE_FILTER_MAX,
    PARALLEL_PROFILE_WORKERS_MAX,
    PREPARE_ENTITY_MAX,
    PREPARED_PROFILE_MAX,
    bounded_integer,
    validate_item_count,
)
from ..utils.logger import get_logger
from .zep_entity_reader import ZepEntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters
from .simulation_artifacts import (
    read_json, save_prepare_artifacts, write_exports_from_canonical,
    write_json, canonical_agents_path, relationship_bootstrap_path,
    build_canonical_agents_from_profiles,
)
from .simulation_preflight import run_preflight

logger = get_logger('askthepeople.simulation')


class SimulationStatus(str, Enum):
    """Simulation Status"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # Simulation manually stopped
    COMPLETED = "completed"  # Simulation completed naturally
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class PlatformType(str, Enum):
    """Platform Type"""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """Simulation Status"""
    simulation_id: str
    project_id: str
    graph_id: str
    
    # Platform enable status
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # Status
    status: SimulationStatus = SimulationStatus.CREATED
    
    # Preparation stage data
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # Configuration generation info
    config_generated: bool = False
    config_reasoning: str = ""
    
    # Runtime data
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Error information
    error: Optional[str] = None

    # Counterfactual branching lineage. Set only on simulations produced by
    # POST /api/simulation/<id>/fork; None on originals. Without these a fork
    # is indistinguishable from an unrelated simulation, so no branch tree can
    # be assembled from the stored data.
    forked_from: Optional[str] = None
    forked_at_turn: Optional[int] = None
    forked_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Full status dictionary (for internal use)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "forked_from": self.forked_from,
            "forked_at_turn": self.forked_at_turn,
            "forked_at": self.forked_at,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """Simplified status dictionary (for API return)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
            # Carried in the list payload so a client can build the branch tree
            # from one request instead of fetching each simulation.
            "forked_from": self.forked_from,
            "forked_at_turn": self.forked_at_turn,
            "forked_at": self.forked_at,
        }


class SimulationManager:
    """
    Simulation Manager
    
    Core features:
    1. Read and filter entities from Zep graph
    2. Generate OASIS Agent Profile
    3. Intelligent generation of simulation config via LLM
    4. Prepare all files needed for preset scripts
    """
    
    @staticmethod
    def _base_dir() -> str:
        """Configured root for simulation run-state. Single source of truth."""
        from ..config import Config
        return Config.OASIS_SIMULATION_DATA_DIR

    def __init__(self):
        # Ensure the *configured* directory exists. Creating a hardcoded
        # repo-relative path here instead would defeat OASIS_SIMULATION_DATA_DIR
        # and raise OSError on a read-only image, which is exactly the
        # deployment the setting exists for.
        os.makedirs(self._base_dir(), exist_ok=True)

        # In-memory Simulation Status cache
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        """Get simulation data directory"""
        from ..utils.safe_path import safe_join
        sim_dir = safe_join(self._base_dir(), simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """Save simulation state to file"""
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        state.updated_at = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Load simulation status from file"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
            forked_from=data.get("forked_from"),
            forked_at_turn=data.get("forked_at_turn"),
            forked_at=data.get("forked_at"),
        )
        
        self._simulations[simulation_id] = state
        return state
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """
        Create new simulation
        
        Args:
            project_id: Project ID
            graph_id: Zep Graph ID
            enable_twitter: Whether to enable Twitter simulation
            enable_reddit: Whether to enable Reddit simulation
            
        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"Created simulation: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        use_archetypes: bool = False,
        archetype_count: Optional[int] = None,
        expansion_factor: Optional[int] = None,
    ) -> SimulationState:
        """
        Prepare simulation environment (fully automated)
        
        Steps:
        1. Read and filter entities from Zep graph
        2. Generate OASIS Agent Profile for each entity (optional LLM enhancement, supports parallel)
        3. Intelligent generation of simulation config via LLM (time, activity, speaking frequency, etc.)
        4. Save config files and Profile files
        5. Copy preset scripts to simulation directory
        
        Args:
            simulation_id: Simulation ID
            simulation_requirement: Simulation requirement description (for LLM)
            document_text: Original document content (for LLM context)
            defined_entity_types: Predefined entity types (optional)
            use_llm_for_profiles: Whether to use LLM for detailed persona
            progress_callback: Progress callback function (stage, progress, message)
            parallel_profile_count: Number of parallel persona generations, default 3
            
        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        parallel_profile_count = bounded_integer(
            parallel_profile_count,
            field="parallel_profile_count",
            minimum=1,
            maximum=PARALLEL_PROFILE_WORKERS_MAX,
        )
        if defined_entity_types is not None:
            defined_entity_types = validate_item_count(
                defined_entity_types,
                field="defined_entity_types",
                maximum=ENTITY_TYPE_FILTER_MAX,
            )
        if use_archetypes:
            archetype_count = bounded_integer(
                archetype_count or Config.ARCHETYPE_DEFAULT_COUNT,
                field="archetype_count",
                minimum=1,
                maximum=ARCHETYPE_COUNT_MAX,
            )
            expansion_factor = bounded_integer(
                expansion_factor or Config.ARCHETYPE_DEFAULT_EXPANSION_FACTOR,
                field="expansion_factor",
                minimum=1,
                maximum=ARCHETYPE_EXPANSION_MAX,
            )
            if archetype_count * expansion_factor > PREPARED_PROFILE_MAX:
                raise ValueError(
                    "Requested archetype expansion exceeds the prepared "
                    f"profile limit of {PREPARED_PROFILE_MAX}."
                )
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== Phase 1: Read and filter entities ==========
            if progress_callback:
                progress_callback("reading", 0, "Connecting to Zep graph...")
            
            reader = ZepEntityReader()
            
            if progress_callback:
                progress_callback("reading", 30, "Reading node data...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )
            if filtered.filtered_count > PREPARE_ENTITY_MAX:
                raise ValueError(
                    "Selected graph contains "
                    f"{filtered.filtered_count} profile entities; the maximum "
                    f"is {PREPARE_ENTITY_MAX}."
                )
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"Completed, total {filtered.filtered_count} entities",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "No matching entities found, please check if graph was built correctly"
                self._save_simulation_state(state)
                return state
            
            # ========== Phase 2: Generate Agent Profile ==========
            total_entities = len(filtered.entities)
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    "Starting generation...",
                    current=0,
                    total=total_entities
                )
            
            # Pass graph_id to enable Zep retrieval for richer context
            generator = OasisProfileGenerator(graph_id=state.graph_id)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )
            
            # Set real-time save paths (prefer Reddit JSON format)
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            if use_archetypes:
                # ========== Archetype compression path ==========
                # generate_archetype_profiles internally calls generate_profiles_from_entities,
                # so we do NOT call it separately here to avoid double LLM generation.
                from ..config import Config as _Config
                n_arch = archetype_count or _Config.ARCHETYPE_DEFAULT_COUNT
                expand = expansion_factor or _Config.ARCHETYPE_DEFAULT_EXPANSION_FACTOR

                profiles, archetypes = generator.generate_archetype_profiles(
                    entities=filtered.entities,
                    n_archetypes=n_arch,
                    expansion_factor=expand,
                    use_llm=use_llm_for_profiles,
                    progress_callback=profile_progress,
                    graph_id=state.graph_id,
                )
                if len(profiles) > PREPARED_PROFILE_MAX:
                    raise ValueError(
                        "Archetype generation produced "
                        f"{len(profiles)} profiles; the maximum is "
                        f"{PREPARED_PROFILE_MAX}."
                    )
                write_json(os.path.join(sim_dir, "archetypes.json"), [a.to_dict() for a in archetypes])

                state.profiles_count = len(profiles)
                canonical_agents = build_canonical_agents_from_profiles(profiles)
                write_json(canonical_agents_path(sim_dir), canonical_agents)
                write_json(relationship_bootstrap_path(sim_dir), [])
                write_exports_from_canonical(sim_dir, canonical_agents)
            else:
                # ========== Normal entity-zip path ==========
                profiles = generator.generate_profiles_from_entities(
                    entities=filtered.entities,
                    use_llm=use_llm_for_profiles,
                    progress_callback=profile_progress,
                    graph_id=state.graph_id,
                    parallel_count=parallel_profile_count,
                    realtime_output_path=realtime_output_path,
                    output_platform=realtime_platform,
                )
                if len(profiles) > PREPARED_PROFILE_MAX:
                    raise ValueError(
                        "Profile generation produced "
                        f"{len(profiles)} profiles; the maximum is "
                        f"{PREPARED_PROFILE_MAX}."
                    )
                state.profiles_count = len(profiles)

                artifacts = save_prepare_artifacts(
                    simulation_dir=sim_dir,
                    entities=filtered.entities,
                    profiles=profiles,
                )
                canonical_agents = artifacts["canonical_agents"]

                if progress_callback:
                    progress_callback(
                        "generating_profiles", 95,
                        "Saving Profile files...",
                        current=total_entities,
                        total=total_entities
                    )

                write_exports_from_canonical(
                    simulation_dir=sim_dir,
                    canonical_agents=canonical_agents,
                )

            if progress_callback:
                progress_callback(
                    "generating_profiles", 100,
                    f"Completed, total {len(profiles)} Profiles",
                    current=len(profiles),
                    total=len(profiles)
                )
            
            # ========== Phase 3: LLM intelligent config generation ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "Analyzing simulation requirements...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "Calling LLM to generate config...",
                    current=1,
                    total=3
                )
            
            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                canonical_agents=canonical_agents,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit
            )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "Saving configuration file...",
                    current=2,
                    total=3
                )
            
            # Save configuration file
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())

            preflight = run_preflight(sim_dir)
            if preflight.get("status") != "passed":
                raise ValueError(f"Simulation preflight failed: {preflight.get('failed_checks', [])}")
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "Configuration generation completed",
                    current=3,
                    total=3
                )
            
            # Note: scripts are kept in backend/scripts/ and not copied to simulation dir
            # simulation_runner runs from scripts/ directory on start
            
            # Update status
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"Simulation preparation completed: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"Simulation preparation failed: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """Get simulation status"""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """List all simulations"""
        simulations = []
        
        from ..utils.safe_path import safe_join, SafePathError
        base_dir = self._base_dir()
        if os.path.exists(base_dir):
            for sim_id in os.listdir(base_dir):
                # Skip hidden files (e.g. .DS_Store) and non-directory files
                if sim_id.startswith('.'):
                    continue
                try:
                    sim_path = safe_join(base_dir, sim_id)
                except SafePathError:
                    continue
                if not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Get simulation Agent Profile"""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        sim_dir = self._get_simulation_dir(simulation_id)
        if platform == "twitter":
            profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
            if not os.path.exists(profile_path):
                return []
            import csv
            with open(profile_path, 'r', encoding='utf-8', newline='') as f:
                return list(csv.DictReader(f))

        profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if not os.path.exists(profile_path):
            return []
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation configuration"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_preflight(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        return read_json(os.path.join(sim_dir, "preflight.json"))

    def get_diagnostics(self, simulation_id: str) -> Dict[str, Any]:
        sim_dir = self._get_simulation_dir(simulation_id)
        return {
            "canonical_agents": read_json(os.path.join(sim_dir, "agent_profiles.canonical.json"), default=[]),
            "entity_type_registry": read_json(os.path.join(sim_dir, "entity_type_registry.json"), default=[]),
            "relationship_bootstrap": read_json(os.path.join(sim_dir, "agent_relationship_bootstrap.json"), default=[]),
            "model_resolution": read_json(os.path.join(sim_dir, "model_resolution.json"), default={}),
            "preflight": read_json(os.path.join(sim_dir, "preflight.json"), default=None),
            "run_manifest": read_json(os.path.join(sim_dir, "run_manifest.json"), default=None),
        }
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Get running instructions"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Activate conda env: conda activate askthepeople\n"
                f"2. Run simulation (script located at {scripts_dir}):\n"
                f"   - Run Twitter separately: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Run Reddit separately: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - Run both platforms in parallel: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
