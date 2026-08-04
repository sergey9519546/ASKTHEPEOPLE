import pytest
from unittest.mock import MagicMock, patch
from app.services.zep_tools import (
    ZepToolsService,
    InsightForgeResult,
    SearchResult,
    NodeInfo,
)
from app.utils.llm_client import LLMClient


@pytest.fixture
def mock_zep_client():
    with patch("app.services.zep_tools.Zep") as mock_zep:
        yield mock_zep


@pytest.fixture
def mock_llm_client():
    mock_llm = MagicMock(spec=LLMClient)
    # mock the chat_json for sub_queries
    mock_llm.chat_json.return_value = {"sub_queries": ["query1", "query2"]}
    return mock_llm


@pytest.fixture
def zep_service(mock_zep_client, mock_llm_client):
    with patch("app.services.zep_tools.Config") as mock_config:
        mock_config.ZEP_API_KEY = "test_key"
        service = ZepToolsService(api_key="test_key", llm_client=mock_llm_client)
        return service


def test_insight_forge_success(zep_service, mock_llm_client):
    """Test successful insight_forge execution with valid inputs and results."""
    # Mock specific methods
    zep_service._generate_sub_queries = MagicMock(return_value=["subq1"])

    # Mock search_graph
    # Sub query search result
    search_res1 = SearchResult(
        facts=["fact1"],
        edges=[
            {"source_node_uuid": "uuid1", "target_node_uuid": "uuid2", "name": "rel1"}
        ],
        nodes=[],
        query="subq1",
        total_count=1,
    )
    # Main query search result
    search_res2 = SearchResult(
        facts=["fact2"],
        edges=[
            {"source_node_uuid": "uuid1", "target_node_uuid": "uuid3", "name": "rel2"}
        ],
        nodes=[],
        query="main_query",
        total_count=1,
    )
    zep_service.search_graph = MagicMock(side_effect=[search_res1, search_res2])

    # Mock get_node_detail
    node1 = NodeInfo(
        uuid="uuid1", name="Node1", labels=["Entity"], summary="summary1", attributes={}
    )
    node2 = NodeInfo(
        uuid="uuid2", name="Node2", labels=["Entity"], summary="summary2", attributes={}
    )

    def get_node_side_effect(uuid):
        if uuid == "uuid1":
            return node1
        if uuid == "uuid2":
            return node2
        return None

    zep_service.get_node_detail = MagicMock(side_effect=get_node_side_effect)

    # Execute
    result = zep_service.insight_forge(
        graph_id="g1", query="main_query", simulation_requirement="sim_req"
    )

    # Assert
    assert isinstance(result, InsightForgeResult)
    assert result.query == "main_query"
    assert result.simulation_requirement == "sim_req"
    assert "subq1" in result.sub_queries
    assert "fact1" in result.semantic_facts
    assert "fact2" in result.semantic_facts

    assert result.total_facts == 2
    assert result.total_entities == 2
    assert result.total_relationships == 1

    # Edges from main_query search are not currently included in all_edges in the implementation
    assert result.relationship_chains == ["Node1 --[rel1]--> Node2"]

    assert zep_service._generate_sub_queries.call_count == 1
    assert zep_service.search_graph.call_count == 2
    assert zep_service.get_node_detail.call_count == 2


def test_insight_forge_node_detail_failure(zep_service, mock_llm_client):
    """Test when get_node_detail fails for one or more entities."""
    zep_service._generate_sub_queries = MagicMock(return_value=["subq1"])

    search_res1 = SearchResult(
        facts=["fact1"],
        edges=[
            {"source_node_uuid": "uuid1", "target_node_uuid": "uuid2", "name": "rel1"}
        ],
        nodes=[],
        query="subq1",
        total_count=1,
    )
    search_res2 = SearchResult(
        facts=[], edges=[], nodes=[], query="main", total_count=0
    )
    zep_service.search_graph = MagicMock(side_effect=[search_res1, search_res2])

    # Fail for uuid2
    node1 = NodeInfo(
        uuid="uuid1", name="Node1", labels=["Entity"], summary="summary1", attributes={}
    )

    def get_node_side_effect(uuid):
        if uuid == "uuid1":
            return node1
        if uuid == "uuid2":
            raise Exception("Database error")
        return None

    zep_service.get_node_detail = MagicMock(side_effect=get_node_side_effect)

    result = zep_service.insight_forge(
        graph_id="g1", query="main_query", simulation_requirement="sim_req"
    )

    # Should gracefully handle the exception and skip the node
    assert result.total_entities == 1
    assert result.entity_insights[0]["uuid"] == "uuid1"


def test_insight_forge_no_edges(zep_service, mock_llm_client):
    """Test when search returns no edges."""
    zep_service._generate_sub_queries = MagicMock(return_value=["subq1"])

    search_res1 = SearchResult(
        facts=["fact1"], edges=[], nodes=[], query="subq1", total_count=1
    )
    search_res2 = SearchResult(
        facts=["fact2"], edges=[], nodes=[], query="main", total_count=1
    )
    zep_service.search_graph = MagicMock(side_effect=[search_res1, search_res2])
    zep_service.get_node_detail = MagicMock()

    result = zep_service.insight_forge(
        graph_id="g1", query="main_query", simulation_requirement="sim_req"
    )

    assert result.total_facts == 2
    assert result.total_entities == 0
    assert result.total_relationships == 0
    assert zep_service.get_node_detail.call_count == 0


def test_generate_sub_queries(zep_service, mock_llm_client):
    """Test the _generate_sub_queries method functionality directly."""
    result = zep_service._generate_sub_queries(
        query="test query", simulation_requirement="sim_req", max_queries=2
    )
    assert result == ["query1", "query2"]
    assert mock_llm_client.chat_json.call_count == 1

    # Test fallback on exception
    mock_llm_client.chat_json.side_effect = Exception("API Error")
    result = zep_service._generate_sub_queries(
        query="test query", simulation_requirement="sim_req", max_queries=2
    )
    # Fallback variants of the main query. The wording is deliberate: the
    # truth contract forbids calling source actors "participants", so this
    # asserts the exact template rather than just the shape.
    assert len(result) == 2
    assert result[0] == "test query"
    assert result[1] == (
        "Source actors or fictional profile labels associated with test query"
    )


def test_insight_forge_edge_case_empty_sub_queries(zep_service, mock_llm_client):
    """Test behavior when _generate_sub_queries returns empty list."""
    zep_service._generate_sub_queries = MagicMock(return_value=[])

    # Mock main search
    search_res = SearchResult(
        facts=["fact_main"],
        edges=[
            {
                "source_node_uuid": "uuid1",
                "target_node_uuid": "uuid2",
                "name": "rel_main",
            }
        ],
        nodes=[],
        query="main",
        total_count=1,
    )
    zep_service.search_graph = MagicMock(return_value=search_res)

    # Mock node details
    node1 = NodeInfo(
        uuid="uuid1", name="Node1", labels=["Entity"], summary="sum1", attributes={}
    )
    node2 = NodeInfo(
        uuid="uuid2", name="Node2", labels=["Entity"], summary="sum2", attributes={}
    )

    def get_node_side_effect(uuid):
        if uuid == "uuid1":
            return node1
        if uuid == "uuid2":
            return node2
        return None

    zep_service.get_node_detail = MagicMock(side_effect=get_node_side_effect)

    result = zep_service.insight_forge(
        graph_id="g1", query="main", simulation_requirement="sim"
    )

    # It should still process the main query
    assert len(result.sub_queries) == 0
    assert result.total_facts == 1
    assert result.semantic_facts == ["fact_main"]
    assert (
        result.total_entities == 0
    )  # because main search edges are not added to all_edges in the current implementation


def test_insight_forge_duplicate_facts_handling(zep_service, mock_llm_client):
    """Test behavior when multiple searches return the same facts."""
    zep_service._generate_sub_queries = MagicMock(return_value=["subq1"])

    search_res1 = SearchResult(
        facts=["shared_fact", "fact1"], edges=[], nodes=[], query="subq1", total_count=2
    )
    search_res2 = SearchResult(
        facts=["shared_fact", "fact2"], edges=[], nodes=[], query="main", total_count=2
    )
    zep_service.search_graph = MagicMock(side_effect=[search_res1, search_res2])
    zep_service.get_node_detail = MagicMock()

    result = zep_service.insight_forge(
        graph_id="g1", query="main", simulation_requirement="sim"
    )

    # shared_fact should only appear once
    assert result.total_facts == 3
    assert set(result.semantic_facts) == {"shared_fact", "fact1", "fact2"}
