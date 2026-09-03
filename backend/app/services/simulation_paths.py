"""Simulation filesystem paths — single source of truth for on-disk layout.

This module owns the simulation directory structure. Every path derivation
(workspace root, simulation dir, config file, preflight, profiles, etc.) goes
through this class to ensure consistency and prevent path-traversal bugs.

Layout:
    WORKSPACE_ROOT/
        {project_id}/
            {graph_id}/
                {simulation_id}/
                    state.json
                    simulation_config.json
                    preflight.json
                    decision_lens_runtime.json (optional)
                    agent_profiles.canonical.json
                    entity_type_registry.json
                    agent_relationship_bootstrap.json
                    model_resolution.json
                    run_manifest.json (optional)
                    reddit_profiles.json
                    twitter_profiles.csv
"""

import os
from ..config import Config
from ..utils.safe_path import safe_join


class SimulationPaths:
    """Single source of truth for simulation directory structure."""

    @staticmethod
    def workspace_root() -> str:
        """Return the simulation workspace root directory."""
        return Config.OASIS_SIMULATION_DATA_DIR

    @staticmethod
    def simulation_dir(simulation_id: str) -> str:
        """Return the simulation directory (path-traversal safe).
        
        Raises SafePathError if simulation_id contains traversal attempts.
        """
        return safe_join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

    @staticmethod
    def state_file(simulation_id: str) -> str:
        """Return the path to state.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "state.json"
        )

    @staticmethod
    def config_file(simulation_id: str) -> str:
        """Return the path to simulation_config.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "simulation_config.json"
        )

    @staticmethod
    def preflight_file(simulation_id: str) -> str:
        """Return the path to preflight.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "preflight.json"
        )

    @staticmethod
    def decision_lens_runtime_file(simulation_id: str) -> str:
        """Return the path to decision_lens_runtime.v1.json (optional)."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "decision_lens_runtime.v1.json"
        )

    @staticmethod
    def canonical_profiles_file(simulation_id: str) -> str:
        """Return the path to agent_profiles.canonical.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "agent_profiles.canonical.json"
        )

    @staticmethod
    def entity_type_registry_file(simulation_id: str) -> str:
        """Return the path to entity_type_registry.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "entity_type_registry.json"
        )

    @staticmethod
    def relationship_bootstrap_file(simulation_id: str) -> str:
        """Return the path to agent_relationship_bootstrap.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "agent_relationship_bootstrap.json"
        )

    @staticmethod
    def model_resolution_file(simulation_id: str) -> str:
        """Return the path to model_resolution.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "model_resolution.json"
        )

    @staticmethod
    def run_manifest_file(simulation_id: str) -> str:
        """Run manifest file path"""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "run_manifest.json"
        )
    
    @staticmethod
    def reddit_profiles_file(simulation_id: str) -> str:
        """Legacy reddit profiles file path"""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "reddit_profiles.json"
        )

    @staticmethod
    def reddit_profiles_file(simulation_id: str) -> str:
        """Return the path to reddit_profiles.json."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "reddit_profiles.json"
        )

    @staticmethod
    def twitter_profiles_file(simulation_id: str) -> str:
        """Return the path to twitter_profiles.csv."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "twitter_profiles.csv"
        )

    @staticmethod
    def archetypes_file(simulation_id: str) -> str:
        """Return the path to archetypes.json (optional, when archetype compression is used)."""
        return os.path.join(
            SimulationPaths.simulation_dir(simulation_id),
            "archetypes.json"
        )

    @staticmethod
    def scripts_dir() -> str:
        """Return the backend/scripts directory (execution runtime)."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../scripts')
        )

    @staticmethod
    def run_parallel_script() -> str:
        """Return the path to run_parallel_simulation.py."""
        return os.path.join(
            SimulationPaths.scripts_dir(),
            "run_parallel_simulation.py"
        )
