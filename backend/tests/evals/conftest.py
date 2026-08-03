"""Shared fixtures for evaluation suite."""

import pytest
import json
import os
from pathlib import Path
from app import create_app
from app.services.oasis_profile_generator import (
    OasisProfileGenerator,
    OasisAgentProfile,
)
from app.services.zep_entity_reader import EntityNode


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def profile_generator():
    """Create profile generator instance."""
    return OasisProfileGenerator()


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    return EntityNode(
        uuid="test-uuid-001",
        name="Alex Chen",
        labels=["Person", "Student"],
        summary="A computer science student interested in AI and ethics",
        attributes={
            "occupation": "Student",
            "institution": "Test University"
        },
        related_edges=[
            {
                "fact": "Alex Chen studies at Test University",
                "edge_name": "studies_at",
                "direction": "outgoing"
            }
        ],
        related_nodes=[
            {
                "name": "Test University",
                "labels": ["University"],
                "summary": "A research university"
            }
        ]
    )


@pytest.fixture
def sample_decision_prompt():
    """Sample decision prompt for profile generation."""
    return "Should universities implement stricter AI ethics guidelines for student research projects?"


@pytest.fixture
def eval_results_path(tmp_path):
    """Path for saving evaluation results."""
    results_path = tmp_path / "results.json"
    yield results_path
    
    # Copy to actual results location if test passes
    if results_path.exists():
        actual_path = Path(__file__).parent / "results.json"
        import shutil
        shutil.copy(results_path, actual_path)


def save_eval_results(results: dict, results_path: Path):
    """Save evaluation results to JSON file."""
    # Load existing results if available
    existing = {}
    if results_path.exists():
        try:
            with open(results_path, 'r') as f:
                existing = json.load(f)
        except:
            pass
    
    # Merge results
    existing.update(results)
    
    # Save
    with open(results_path, 'w') as f:
        json.dump(existing, f, indent=2)
