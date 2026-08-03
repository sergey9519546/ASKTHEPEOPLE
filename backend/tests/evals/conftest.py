"""Shared fixtures and pytest plugin for evaluation suite."""

import pytest
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for app imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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


# ============================================================================
# Pytest Plugin for Result Collection
# ============================================================================

class EvalResultsPlugin:
    """Plugin to collect and save evaluation results."""
    
    def __init__(self):
        self.results = {}
        self.test_outcomes = {}
    
    def pytest_runtest_logreport(self, report):
        """Collect test outcomes."""
        if report.when == "call":
            self.test_outcomes[report.nodeid] = {
                "outcome": report.outcome,
                "duration": report.duration,
            }
    
    def pytest_sessionfinish(self, session, exitstatus):
        """Save results at the end of the test session."""
        # Only save if we're in the evals directory
        if not any('evals' in str(item.fspath) for item in session.items):
            return
        
        # Determine output path
        evals_dir = Path(__file__).parent
        results_path = evals_dir / "results.json"
        
        # Try to load existing results from tmp_path if available
        try:
            for item in session.items:
                if hasattr(item, 'funcargs') and 'eval_results_path' in item.funcargs:
                    tmp_path = item.funcargs['eval_results_path']
                    if tmp_path.exists():
                        with open(tmp_path, 'r') as f:
                            self.results.update(json.load(f))
                        break
        except Exception:
            pass
        
        # Add test execution metadata
        eval_tests = [
            item for item in session.items
            if 'evals' in str(item.fspath)
        ]
        
        passed = sum(
            1 for nodeid, outcome in self.test_outcomes.items()
            if outcome['outcome'] == 'passed'
        )
        failed = sum(
            1 for nodeid, outcome in self.test_outcomes.items()
            if outcome['outcome'] == 'failed'
        )
        
        self.results['_test_summary'] = {
            'total_tests': len(eval_tests),
            'passed': passed,
            'failed': failed,
            'exit_status': exitstatus,
        }
        
        # Save results
        try:
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n\nEvaluation results saved to: {results_path}")
        except Exception as e:
            print(f"\n\nWarning: Failed to save evaluation results: {e}")


def pytest_configure(config):
    """Register custom markers and plugin."""
    config.addinivalue_line(
        "markers", "eval: mark test as an evaluation suite test"
    )
    
    if config.pluginmanager.hasplugin('eval_results'):
        return
    
    plugin = EvalResultsPlugin()
    config.pluginmanager.register(plugin, 'eval_results')
