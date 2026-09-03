"""
OASIS Simulation Manager
Manages parallel Twitter and Reddit simulations
Uses preset scripts + LLM to intelligently generate configuration parameters
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import Config
from ..domain.decision_lens import InputReferenceV1
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
from .decision_lens_generator import DecisionLensGenerator
from .decision_lens_repository import DecisionLensRepository
from .oasis_profile_generator import OasisProfileGenerator
from .simulation_artifacts import (
    build_canonical_agents_from_profiles,
    canonical_agents_path,
    read_json,
    relationship_bootstrap_path,
    save_prepare_artifacts,
    write_exports_from_canonical,
    write_json,
)
from .simulation_config_generator import SimulationConfigGenerator
from .simulation_preflight import run_preflight
from .zep_entity_reader import ZepEntityReader

logger = get_logger('askthepeople.simulation')


class SimulationStatus(str, Enum):
    """Simulation Status"""
    CREATED = "created"
    PREPARING = "preparing"
    NEEDS_REVIEW = "needs_review"
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


class DecisionLensPreparationError(ValueError):
    """Stable preparation-boundary error for API and task translation."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


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
    decision_lenses_count: int = 0
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
            "decision_lenses_count": self.decision_lenses_count,
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
            "decision_lenses_count": self.decision_lenses_count,
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
        """Get simulation data directory (delegates to SimulationPaths)."""
        from .simulation_paths import SimulationPaths
        sim_dir = SimulationPaths.simulation_dir(simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """Save simulation state to the filesystem lifecycle store.

        The legacy filesystem lifecycle is the current store for simulation
        run-state. Canonical ``dw_runs`` rows are owned exclusively by
        ``RunRepository`` (which writes UUIDv7 physical ids and independent
        ``run_...`` aliases); this method must not mirror rows into it, or the
        two writers would populate the canonical table with incompatible
        identities (``uuid5``/``run_{simulation_id}``/fabricated tenants) that
        fail the domain's UUIDv7 invariant when read back.
        """
        sim_dir = self._get_simulation_dir(state.simulation_id)
        from .simulation_paths import SimulationPaths
        state_file = SimulationPaths.state_file(state.simulation_id)

        state.updated_at = datetime.now().isoformat()

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Load simulation status from file"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        from .simulation_paths import SimulationPaths
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = SimulationPaths.state_file(simulation_id)
        
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
            decision_lenses_count=data.get("decision_lenses_count", 0),
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
        if not Config.DECISION_LENS_V1_ENABLED:
            raise DecisionLensPreparationError(
                "decision_lens_preparation_unavailable"
            )
        if use_archetypes:
            raise DecisionLensPreparationError(
                "deprecated_control_not_supported"
            )
        return self._prepare_decision_lens_review(
            state=state,
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            defined_entity_types=defined_entity_types,
            progress_callback=progress_callback,
        )

        # Legacy persona preparation remains readable for existing artifacts,
        # but it is not executable for new runs under the v1 transition.
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
            from .simulation_paths import SimulationPaths
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = SimulationPaths.reddit_profiles_file(simulation_id)
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = SimulationPaths.twitter_profiles_file(simulation_id)
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
                write_json(SimulationPaths.archetypes_file(simulation_id), [a.to_dict() for a in archetypes])

                state.profiles_count = len(profiles)
                canonical_agents = build_canonical_agents_from_profiles(profiles)
                write_json(SimulationPaths.canonical_profiles_file(simulation_id), canonical_agents)
                write_json(SimulationPaths.relationship_bootstrap_file(simulation_id), [])
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
            config_path = SimulationPaths.config_file(simulation_id)
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

    def _prepare_decision_lens_review(
        self,
        *,
        state: SimulationState,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]],
        progress_callback: Optional[callable],
    ) -> SimulationState:
        requirement = simulation_requirement.strip()
        if not requirement:
            raise DecisionLensPreparationError(
                "decision_lens_requirement_required"
            )

        try:
            state.status = SimulationStatus.PREPARING
            state.error = None
            self._save_simulation_state(state)
            sim_dir = self._get_simulation_dir(state.simulation_id)

            if progress_callback:
                progress_callback("reading", 0, "Reading graph records...")
            filtered = ZepEntityReader().filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True,
            )
            if filtered.filtered_count > PREPARE_ENTITY_MAX:
                raise ValueError(
                    "Selected graph contains "
                    f"{filtered.filtered_count} records; the maximum is "
                    f"{PREPARE_ENTITY_MAX}."
                )
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            if filtered.filtered_count == 0:
                raise DecisionLensPreparationError(
                    "decision_lens_source_records_required"
                )
            if progress_callback:
                progress_callback(
                    "reading",
                    100,
                    f"Read {filtered.filtered_count} graph records",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count,
                )

            references, context_records = self._decision_lens_inputs(
                requirement=requirement,
                document_text=document_text,
                entities=filtered.entities,
            )
            repository = DecisionLensRepository(sim_dir)
            current = repository.get_current_artifact()
            revision = 1 if current is None else current.revision + 1

            if progress_callback:
                progress_callback(
                    "generating_decision_lenses",
                    0,
                    "Generating functional decision lenses...",
                )
            artifact = DecisionLensGenerator().generate(
                simulation_id=state.simulation_id,
                revision=revision,
                simulation_requirement=requirement,
                input_references=references,
                allowed_reference_ids={ref.ref_id for ref in references},
                context_records=context_records,
            )
            persisted = repository.save_artifact(artifact)

            state.profiles_count = 0
            state.decision_lenses_count = len(persisted.lenses)
            state.config_generated = False
            state.config_reasoning = ""
            state.status = SimulationStatus.NEEDS_REVIEW
            self._save_simulation_state(state)
            if progress_callback:
                progress_callback(
                    "generating_decision_lenses",
                    100,
                    "Decision lenses are ready for human review",
                    current=len(persisted.lenses),
                    total=len(persisted.lenses),
                )
            logger.info(
                "Simulation preparation paused for decision-lens review: %s, "
                "records=%s, lenses=%s",
                state.simulation_id,
                state.entities_count,
                state.decision_lenses_count,
            )
            return state
        except Exception as exc:
            logger.error(
                "Decision-lens preparation failed: %s, error=%s",
                state.simulation_id,
                str(exc),
            )
            state.status = SimulationStatus.FAILED
            state.error = str(exc)
            self._save_simulation_state(state)
            raise

    @staticmethod
    def _decision_lens_inputs(
        *,
        requirement: str,
        document_text: str,
        entities: List[Any],
    ) -> tuple[tuple[InputReferenceV1, ...], list[Dict[str, Any]]]:
        references: list[InputReferenceV1] = []
        records: list[Dict[str, Any]] = []

        requirement_ref = InputReferenceV1(
            ref_id="starting_condition_requirement",
            role="starting_condition",
            origin="USER_STATED",
        )
        references.append(requirement_ref)
        records.append(
            {
                **requirement_ref.model_dump(mode="json"),
                "record_type": "declared_simulation_requirement",
                "content": requirement,
            }
        )

        source_text = document_text.strip()
        if source_text:
            source_ref = InputReferenceV1(
                ref_id="source_document_excerpt",
                role="source_segment",
                origin="SOURCE_EXTRACTED",
            )
            references.append(source_ref)
            records.append(
                {
                    **source_ref.model_dump(mode="json"),
                    "record_type": "unverified_source_excerpt",
                    "content": source_text[:12000],
                }
            )

        for index, entity in enumerate(entities, start=1):
            stable_key = str(getattr(entity, "uuid", "") or index)
            suffix = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:24]
            reference = InputReferenceV1(
                ref_id=f"graph_record_{suffix}",
                role="graph_record",
                origin="GENERATED_GENERATED",
            )
            references.append(reference)
            records.append(
                {
                    **reference.model_dump(mode="json"),
                    "record_type": "unverified_graph_extraction",
                    "entity_type": entity.get_entity_type(),
                    "labels": list(getattr(entity, "labels", [])),
                    "summary": str(getattr(entity, "summary", ""))[:2000],
                    "attributes": dict(getattr(entity, "attributes", {}) or {}),
                    "external_validation": False,
                    "causal_evidence": False,
                }
            )
        return tuple(references), records
    
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
        from .simulation_paths import SimulationPaths
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        if platform == "twitter":
            profile_path = SimulationPaths.twitter_profiles_file(simulation_id)
            if not os.path.exists(profile_path):
                return []
            import csv
            with open(profile_path, 'r', encoding='utf-8', newline='') as f:
                return list(csv.DictReader(f))

        profile_path = SimulationPaths.reddit_profiles_file(simulation_id)
        if not os.path.exists(profile_path):
            return []
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation configuration"""
        from .simulation_paths import SimulationPaths
        config_path = SimulationPaths.config_file(simulation_id)
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_preflight(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        from .simulation_paths import SimulationPaths
        return read_json(SimulationPaths.preflight_file(simulation_id))

    def get_diagnostics(self, simulation_id: str) -> Dict[str, Any]:
        from .simulation_paths import SimulationPaths
        return {
            "canonical_agents": read_json(SimulationPaths.canonical_profiles_file(simulation_id), default=[]),
            "entity_type_registry": read_json(SimulationPaths.entity_type_registry_file(simulation_id), default=[]),
            "relationship_bootstrap": read_json(SimulationPaths.relationship_bootstrap_file(simulation_id), default=[]),
            "model_resolution": read_json(SimulationPaths.model_resolution_file(simulation_id), default={}),
            "preflight": read_json(SimulationPaths.preflight_file(simulation_id), default=None),
            "run_manifest": read_json(SimulationPaths.run_manifest_file(simulation_id), default=None),
        }
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Get running instructions"""
        from .simulation_paths import SimulationPaths
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = SimulationPaths.config_file(simulation_id)
        scripts_dir = SimulationPaths.scripts_dir()
        parallel_script = SimulationPaths.run_parallel_script()
        parallel_command = (
            f'python "{parallel_script}" --config "{config_path}"'
        )
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"{parallel_command} --twitter-only",
                "reddit": f"{parallel_command} --reddit-only",
                "parallel": parallel_command,
            },
            "instructions": (
                f"1. Activate conda env: conda activate askthepeople\n"
                f"2. Run simulation (script located at {scripts_dir}):\n"
                f"   - Run Twitter separately: {parallel_command} --twitter-only\n"
                f"   - Run Reddit separately: {parallel_command} --reddit-only\n"
                f"   - Run both platforms in parallel: {parallel_command}"
            )
        }

    def is_runnable(self, simulation_id: str) -> tuple[bool, dict]:
        """Check if a simulation is prepared and can be started.
        
        This is the authoritative readiness check, used by execution routes to
        determine whether /start should accept the simulation. It validates:
        
        1. Status is in the prepared set (uses SimulationStatus enum)
        2. Config file exists (config_generated=True)
        3. Preflight passed (preflight.json status="passed")
        4. Decision-lens admission check passed (if decision_lens_runtime.json exists)
        
        Returns:
            (is_runnable: bool, info: dict) — info contains reason/diagnostics
        """
        import os
        import json
        from .simulation_paths import SimulationPaths
        from .decision_lens_repository import DecisionLensAdmissionError
        from .simulation_preflight import assert_decision_lens_execution_admission
        
        simulation_dir = self._get_simulation_dir(simulation_id)
        
        if not os.path.exists(simulation_dir):
            return False, {"reason": "Simulation directory does not exist"}
        
        # Load state
        state = self._load_simulation_state(simulation_id)
        if not state:
            return False, {"reason": "Could not load simulation state"}
        
        # Check status using enum
        try:
            status_enum = SimulationStatus(state.status)
        except ValueError:
            return False, {
                "reason": f"Invalid status: {state.status}",
                "status": state.status,
            }
        
        # The prepared set: "ready", "preparing" (with config_generated=True),
        # "running", "completed", "stopped", "interrupted".
        # "failed" is excluded — a failed run does NOT prove preparation succeeded.
        # "preparing" qualifies only with config_generated=True (covers the race
        # where prepare task finishes but status hasn't flipped yet).
        prepared_statuses = {
            SimulationStatus.READY,
            SimulationStatus.PREPARING,
            SimulationStatus.RUNNING,
            SimulationStatus.COMPLETED,
            SimulationStatus.STOPPED,
            SimulationStatus.INTERRUPTED,
        }
        
        if status_enum not in prepared_statuses:
            return False, {
                "reason": f"Status not prepared: {state.status}",
                "status": state.status,
            }
        
        # Check config exists
        # Honor state.config_generated flag, not just file existence
        # (the test suite may seed files but flag config_generated=False)
        config_generated = getattr(state, 'config_generated', False)
        if not config_generated:
            return False, {
                "reason": "Config not generated",
                "status": state.status,
                "config_generated": False,
            }
        
        # Also verify file exists
        config_path = SimulationPaths.config_file(simulation_id)
        if not os.path.exists(config_path):
            return False, {
                "reason": "Config file missing",
                "status": state.status,
                "config_generated": config_generated,
            }
        
        # Check preflight
        preflight_path = SimulationPaths.preflight_file(simulation_id)
        preflight_passed = False
        if os.path.exists(preflight_path):
            with open(preflight_path, 'r', encoding='utf-8') as pf:
                preflight_data = json.load(pf)
            preflight_passed = preflight_data.get("status") == "passed"
        
        if not preflight_passed:
            return False, {
                "reason": "Preflight not passed",
                "status": state.status,
                "config_generated": config_generated,
                "preflight_passed": False,
            }
        
        # Decision-lens admission check
        decision_lens_runtime = SimulationPaths.decision_lens_runtime_file(simulation_id)
        uses_decision_lens_boundary = os.path.exists(decision_lens_runtime)
        admission_error = None
        
        if uses_decision_lens_boundary:
            try:
                assert_decision_lens_execution_admission(simulation_dir)
            except DecisionLensAdmissionError as exc:
                admission_error = {
                    "code": exc.code,
                    "remediation": exc.remediation,
                }
        
        if admission_error is not None:
            return False, {
                "reason": "Decision-lens admission check failed",
                "admission_error": admission_error,
            }
        
        # Compute profiles_count based on execution boundary
        profiles_count = 0
        if uses_decision_lens_boundary:
            with open(decision_lens_runtime, 'r', encoding='utf-8') as f:
                runtime_data = json.load(f)
            adapters = runtime_data.get("adapters", []) if isinstance(runtime_data, dict) else []
            profiles_count = len(adapters) if isinstance(adapters, list) else 0
        else:
            # Legacy: count from reddit_profiles.json
            reddit_profiles = SimulationPaths.reddit_profiles_file(simulation_id)
            if os.path.exists(reddit_profiles):
                with open(reddit_profiles, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0
        
        # All checks passed
        return True, {
            "status": state.status.value if isinstance(state.status, SimulationStatus) else state.status,
            "entities_count": state.entities_count,
            "profiles_count": profiles_count,
            "entity_types": state.entity_types,
            "config_generated": config_generated,
            "preflight_passed": preflight_passed,
            "execution_boundary": (
                "decision_lens_reviewed"
                if uses_decision_lens_boundary
                else "legacy_profile_artifact_non_executable"
            ),
        }
