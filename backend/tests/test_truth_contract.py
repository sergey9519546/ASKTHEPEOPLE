"""
Truth Contract Validation Tests
Ensures Gate 1 requirements are met: Truth Rail visibility and API metadata enforcement

Note: These tests validate the truth contract implementation structure.
Full API integration tests require Flask test client setup.
"""

import ast
import sys
import os
import json
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from flask import Flask

# Add backend directory to path for direct module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestTruthMetadataStructure:
    """Test that truth metadata helper has correct structure"""
    
    def test_truth_metadata_file_exists(self):
        """Verify response.py utility file exists"""
        response_path = os.path.join(
            os.path.dirname(__file__),
            "../app/utils/response.py"
        )
        assert os.path.exists(response_path), \
            "response.py utility file does not exist"
    
    def test_truth_metadata_function_defined(self):
        """Verify truth_metadata function is defined in response.py"""
        response_path = os.path.join(
            os.path.dirname(__file__),
            "../app/utils/response.py"
        )
        
        with open(response_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "def truth_metadata()" in content, \
            "truth_metadata() function not found"
        assert "def truth_response(" in content, \
            "truth_response() function not found"
    
    def test_truth_metadata_returns_required_fields(self):
        """Verify truth_metadata returns all required fields"""
        response_path = os.path.join(
            os.path.dirname(__file__),
            "../app/utils/response.py"
        )
        
        with open(response_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check required fields are in the return statement
        required_fields = [
            '"human_respondent_count"',
            '"output_origin"',
            '"is_forecast"',
            '"generated_at"'
        ]
        
        for field in required_fields:
            assert field in content, \
                f"Required field {field} not found in truth_metadata"


class TestAPIMetadataIntegration:
    """Test that API files import and use truth metadata"""
    
    def test_report_api_imports_truth_metadata(self):
        """Verify report.py imports truth_metadata"""
        api_path = os.path.join(
            os.path.dirname(__file__),
            "../app/api/report.py"
        )
        
        with open(api_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports_truth_metadata = any(
            isinstance(node, ast.ImportFrom)
            and node.level == 2
            and node.module == "utils.response"
            and any(alias.name == "truth_metadata" for alias in node.names)
            for node in ast.walk(tree)
        )

        assert imports_truth_metadata, "report.py does not import truth_metadata"
        assert "**truth_metadata()" in content, \
            "report.py does not use truth_metadata in responses"
    
    def test_simulation_api_entity_routes_return_truth_metadata(self):
        """The entity endpoints must attach truth metadata to their responses.

        Asserted against the live handlers rather than a source grep of one
        file. The previous version grepped app/api/simulation.py, which kept
        undecorated copies of these handlers alongside the registered ones in
        app/api/routes/. The copies carried `**truth_metadata()` and the
        registered handlers did not, so the contract was reported as met by
        code that never answered a request.
        """
        from app.api.routes import entity_routes

        called = {}

        def fake_truth_metadata():
            called["hit"] = called.get("hit", 0) + 1
            return {"truth_metadata": "present"}

        class FakeReader:
            def filter_defined_entities(self, **_kwargs):
                return SimpleNamespace(entities=[])

            def get_entity_with_context(self, *_args):
                return {"uuid": "e1"}

            def get_entities_by_type(self, *_args):
                return []

        app = Flask(__name__)
        with mock.patch.object(entity_routes, "truth_metadata", fake_truth_metadata), \
                mock.patch.object(entity_routes, "ZepEntityReader", FakeReader), \
                mock.patch.object(
                    entity_routes,
                    "resolve_project_graph",
                    return_value=SimpleNamespace(graph_id="g1"),
                ), \
                mock.patch.object(entity_routes.Config, "ZEP_API_KEY", "test-key"):
            handlers = [
                lambda: entity_routes.get_graph_entities("g1"),
                lambda: entity_routes.get_entity_detail("g1", "e1"),
                lambda: entity_routes.get_entities_by_type("g1", "Person"),
            ]
            for handler in handlers:
                with app.test_request_context("/?project_id=project-1"):
                    payload = handler().get_json()
                assert payload["success"] is True
                assert payload.get("truth_metadata") == "present", (
                    "entity route response is missing truth metadata"
                )

        assert called["hit"] == 3
    
    def test_graph_api_imports_truth_metadata(self):
        """Verify graph.py imports truth_metadata"""
        api_path = os.path.join(
            os.path.dirname(__file__),
            "../app/api/graph.py"
        )
        
        with open(api_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "from ..utils.response import truth_metadata" in content, \
            "graph.py does not import truth_metadata"
        assert "**truth_metadata()" in content, \
            "graph.py does not use truth_metadata in responses"


class TestProhibitedClaims:
    """Test that prohibited claims are not present in code"""
    
    def test_response_metadata_values(self):
        """Ensure response.py has correct hardcoded values"""
        response_path = os.path.join(
            os.path.dirname(__file__),
            "../app/utils/response.py"
        )
        
        with open(response_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check correct values are used
        assert '"human_respondent_count": 0' in content
        assert '"output_origin": "synthetic"' in content
        assert '"is_forecast": False' in content
    
    def test_no_misleading_origin_values(self):
        """Ensure output_origin is never set to misleading values"""
        response_path = os.path.join(
            os.path.dirname(__file__),
            "../app/utils/response.py"
        )
        
        with open(response_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # These values should never appear
        prohibited_origins = ["human", "survey", "real", "observed"]
        for origin in prohibited_origins:
            assert f'"output_origin": "{origin}"' not in content, \
                f"Prohibited origin value '{origin}' found"


class TestClaimRegistry:
    """Test that claim and product truth contract exist and have correct structure (ADR-0001)"""
    
    def test_claim_registry_exists(self):
        """Verify ADR-0001 product truth contract file exists"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md"
        )
        assert os.path.exists(registry_path), \
            "ADR-0001-product-category-and-truth-contract.md does not exist"
    
    def test_claim_registry_has_approved_section(self):
        """Verify ADR-0001 has truth contract section"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md"
        )
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Truth Contract" in content or "truth contract" in content.lower()
        assert "Decision" in content
    
    def test_claim_registry_has_required_disclosures(self):
        """Verify truth contract documents required disclosures"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md"
        )
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "zero human respondents" in content.lower() or "human respondent count equals zero" in content.lower()
        assert "synthetic" in content.lower()
        assert "forecast" in content.lower()


class TestTruthRailComponent:
    """Test frontend TruthRail component exists and has correct content"""
    
    def test_truth_rail_component_exists(self):
        """Verify TruthRail.vue component file exists"""
        component_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/TruthRail.vue"
        )
        assert os.path.exists(component_path), \
            "TruthRail.vue component does not exist"
    
    def test_truth_rail_content(self):
        """Verify TruthRail component contains required disclosure text"""
        component_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/TruthRail.vue"
        )
        
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_truth_statements = (
            "ACTIONS + ANSWERS: GENERATED",
            "HUMAN RESPONDENTS: 0",
            "NOT A FORECAST",
            "SOURCES: STARTING CONDITIONS ONLY",
            "HUMAN VALIDATION: OUTSIDE THIS RUN",
        )

        for statement in required_truth_statements:
            assert statement in content
    
    def test_truth_rail_styling(self):
        """Verify TruthRail has prominent styling (yellow background)"""
        component_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/TruthRail.vue"
        )
        
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for yellow background and sticky positioning
        assert "background:" in content.lower() or "background-color:" in content.lower()
        assert "sticky" in content.lower() or "fixed" in content.lower()


class TestViewIntegration:
    """Test that the truth rail is guaranteed across every workflow surface.

    The rail was historically imported per-view, which let a new view silently
    ship without it. It now lives once in DesktopShell — the OS chrome that
    hosts every route view as a window — so the guarantee is structural: any
    view wired into the shell's app registry inherits the rail.
    """

    FRONTEND = os.path.join(os.path.dirname(__file__), "../../frontend/src")

    def _read(self, relpath):
        with open(os.path.join(self.FRONTEND, relpath), 'r', encoding='utf-8') as f:
            return f.read()

    def test_shell_renders_truth_rail(self):
        """The desktop shell renders the truth rail once, above every window."""
        content = self._read("components/DesktopShell.vue")
        assert 'from "./TruthRail.vue"' in content or \
               "from './TruthRail.vue'" in content
        assert "<TruthRail" in content

    def test_app_hosts_desktop_shell(self):
        """The root App.vue hosts the shell, so the rail is always mounted."""
        content = self._read("App.vue")
        assert 'from "./components/DesktopShell.vue"' in content or \
               "from './components/DesktopShell.vue'" in content
        assert "<DesktopShell" in content

    def test_workflow_views_are_registered_in_shell(self):
        """Every workflow view is wired into the shell's app registry.

        Each route view renders inside a shell window and the shell owns the
        rail, so registration is what guarantees the rail overlays the view.
        A view that exists but is not registered would bypass the shell.
        """
        content = self._read("composables/useDesktop.js")
        for view in (
            "Home.vue",
            "MainView.vue",
            "SimulationView.vue",
            "SimulationRunView.vue",
            "ReportView.vue",
            "InteractionView.vue",
        ):
            assert view in content, \
                f"{view} is not registered in the desktop shell"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
