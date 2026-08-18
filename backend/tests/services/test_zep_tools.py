import pytest
from unittest.mock import MagicMock, patch

from app.services.zep_tools import ZepToolsService, SearchResult

@pytest.fixture
def service():
    with patch("app.services.zep_tools.Zep") as mock_zep:
        svc = ZepToolsService(api_key="test_key")
        svc.client = mock_zep.return_value
        # Disable retry delay to speed up testing of exceptions
        svc.MAX_RETRIES = 1
        svc.RETRY_DELAY = 0.0
        return svc

# Create simple data holder classes to avoid MagicMock __getattr__ dynamic creation
class MockEdgeData:
    pass

class MockNodeData:
    pass

def test_search_graph_success_with_edges_and_nodes(service):
    # Setup mock search result
    mock_search_result = MagicMock()

    mock_edge = MockEdgeData()
    mock_edge.uuid = "edge-123"
    mock_edge.name = "edge-name"
    mock_edge.fact = "Edge Fact 1"
    mock_edge.source_node_uuid = "node-1"
    mock_edge.target_node_uuid = "node-2"

    mock_node = MockNodeData()
    mock_node.uuid = "node-123"
    mock_node.name = "NodeName"
    mock_node.labels = ["Label1"]
    mock_node.summary = "Node Summary 1"

    mock_search_result.edges = [mock_edge]
    mock_search_result.nodes = [mock_node]

    service.client.graph.search.return_value = mock_search_result

    # Call the method
    result = service.search_graph("test_graph", "test query")

    # Assert API call
    service.client.graph.search.assert_called_once_with(
        graph_id="test_graph",
        query="test query",
        limit=10,
        scope="edges",
        reranker="cross_encoder"
    )

    # Assert result mapping
    assert isinstance(result, SearchResult)
    assert result.query == "test query"
    assert result.total_count == 2

    assert result.facts == ["Edge Fact 1", "[NodeName]: Node Summary 1"]

    assert len(result.edges) == 1
    assert result.edges[0]["uuid"] == "edge-123"
    assert result.edges[0]["name"] == "edge-name"
    assert result.edges[0]["fact"] == "Edge Fact 1"
    assert result.edges[0]["source_node_uuid"] == "node-1"
    assert result.edges[0]["target_node_uuid"] == "node-2"

    assert len(result.nodes) == 1
    assert result.nodes[0]["uuid"] == "node-123"
    assert result.nodes[0]["name"] == "NodeName"
    assert result.nodes[0]["labels"] == ["Label1"]
    assert result.nodes[0]["summary"] == "Node Summary 1"

def test_search_graph_fallback_to_local_search_on_exception(service):
    service.client.graph.search.side_effect = Exception("API Error")

    # Mock _local_search
    expected_local_result = SearchResult(facts=["Local Fact"], edges=[], nodes=[], query="test query", total_count=1)
    service._local_search = MagicMock(return_value=expected_local_result)

    # Call the method
    result = service.search_graph("test_graph", "test query", limit=5, scope="nodes")

    # Assert
    service._local_search.assert_called_once_with("test_graph", "test query", 5, "nodes")
    assert result == expected_local_result

def test_search_graph_missing_attributes_handled_gracefully(service):
    # Test cases where edge/node attributes might be missing or None
    mock_search_result = MagicMock()

    mock_edge = MockEdgeData()
    mock_edge.uuid = "edge-uuid"

    mock_node = MockNodeData()
    mock_node.uuid = "node-uuid"

    mock_search_result.edges = [mock_edge]
    mock_search_result.nodes = [mock_node]

    service.client.graph.search.return_value = mock_search_result

    # Call the method
    result = service.search_graph("test_graph", "test query")

    # Assert missing attributes default to empty strings or lists as expected
    assert result.facts == []

    assert len(result.edges) == 1
    assert result.edges[0]["uuid"] == "edge-uuid"
    assert result.edges[0]["name"] == ""
    assert result.edges[0]["fact"] == ""
    assert result.edges[0]["source_node_uuid"] == ""
    assert result.edges[0]["target_node_uuid"] == ""

    assert len(result.nodes) == 1
    assert result.nodes[0]["uuid"] == "node-uuid"
    assert result.nodes[0]["name"] == ""
    assert result.nodes[0]["labels"] == []
    assert result.nodes[0]["summary"] == ""


@pytest.mark.parametrize(
    "provider_outcome",
    [
        pytest.param(ValueError, id="unavailable-exception"),
        pytest.param(RuntimeError, id="provider-exception"),
        pytest.param(None, id="provider-error-response"),
    ],
)
def test_interview_agents_failure_summary_omits_raw_provider_detail(
    service,
    monkeypatch,
    provider_outcome,
):
    from app.services.simulation_runner import SimulationRunner

    raw_canary = "PRIVATE_GENERATED_PROBE_PROVIDER_BODY"
    profile = {
        "realname": "Generated profile",
        "username": "generated_profile",
        "bio": "Fictional test profile",
        "profession": "Tester",
    }
    service._load_agent_profiles = MagicMock(return_value=[profile])
    service._select_agents_for_interview = MagicMock(
        return_value=([profile], [0], "Synthetic test selection")
    )

    def provider_call(**_kwargs):
        if provider_outcome is not None:
            raise provider_outcome(raw_canary)
        return {"success": False, "error": raw_canary}

    monkeypatch.setattr(
        SimulationRunner,
        "interview_agents_batch",
        provider_call,
    )

    result = service.interview_agents(
        simulation_id="simulation-provider-failure",
        interview_requirement="Harmless test prompt",
        custom_questions=["Harmless test question"],
    )

    assert raw_canary not in result.summary
    assert result.summary in {
        "Synthetic perspective probe is unavailable. The simulation "
        "environment may be closed.",
        "Synthetic perspective probe failed. Try again later.",
    }
