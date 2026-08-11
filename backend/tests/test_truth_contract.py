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
    """Test that claim registry exists and has correct structure"""
    
    def test_claim_registry_exists(self):
        """Verify CLAIM_REGISTRY.md file exists"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/product/CLAIM_REGISTRY.md"
        )
        assert os.path.exists(registry_path), \
            "CLAIM_REGISTRY.md does not exist"
    
    def test_claim_registry_has_approved_section(self):
        """Verify claim registry has approved claims section"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/product/CLAIM_REGISTRY.md"
        )
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "## ✅ Approved Claims" in content or "Approved Claims" in content
        assert "## ❌ Prohibited Claims" in content or "Prohibited Claims" in content
    
    def test_claim_registry_has_required_disclosures(self):
        """Verify claim registry documents required disclosures"""
        registry_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/product/CLAIM_REGISTRY.md"
        )
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "0 human respondents" in content
        assert "synthetic" in content.lower()
        assert "non-representative" in content.lower()


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
            "ACTIONS + ANSWERS: SYNTHETIC",
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
    """Test that TruthRail is integrated into all workflow views"""
    
    def test_home_view_has_truth_rail(self):
        """Verify Home.vue imports and uses TruthRail"""
        view_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/views/Home.vue"
        )
        
        with open(view_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'from "../components/TruthRail.vue"' in content or \
               'from \'../components/TruthRail.vue\'' in content
        assert "<TruthRail" in content
    
    def test_process_view_has_truth_rail(self):
        """Verify MainView.vue (formerly Process.vue) imports and uses TruthRail"""
        view_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/views/MainView.vue"
        )
        
        with open(view_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'TruthRail' in content
        assert "<TruthRail" in content
    
    def test_main_view_has_truth_rail(self):
        """Verify MainView.vue imports and uses TruthRail"""
        view_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/views/MainView.vue"
        )
        
        with open(view_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'TruthRail' in content
        assert "<TruthRail" in content
    
    def test_interaction_view_has_truth_rail(self):
        """Verify InteractionView.vue imports and uses TruthRail"""
        view_path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/views/InteractionView.vue"
        )
        
        with open(view_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'TruthRail' in content
        assert "<TruthRail" in content


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
