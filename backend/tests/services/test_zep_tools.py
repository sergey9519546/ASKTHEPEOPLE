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
