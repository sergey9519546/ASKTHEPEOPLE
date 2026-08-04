import pytest
import os
from unittest.mock import MagicMock, patch

from app.services.zep_tools import ZepToolsService, SearchResult, NodeInfo, EdgeInfo

@pytest.fixture
def mock_zep_tools_service(monkeypatch):
    """创建一个模拟的 ZepToolsService 实例。"""
    # 绕过 __init__ 中抛出 ValueError 的情况
    with patch('app.services.zep_tools.Config.ZEP_API_KEY', 'fake_api_key'), \
         patch('app.services.zep_tools.Zep') as mock_zep, \
         patch('app.services.zep_tools.LLMClient') as mock_llm:
        service = ZepToolsService(api_key="fake_api_key")
        yield service

def test_local_search_with_edges(mock_zep_tools_service):
    """测试基于边的本地搜索。"""
    graph_id = "test_graph"
    query = "test query"

    # 模拟边数据
    mock_edges = [
        EdgeInfo(uuid="1", name="relates_to", fact="This is a test fact containing the query keyword.", source_node_uuid="A", target_node_uuid="B"),
        EdgeInfo(uuid="2", name="depends_on", fact="This is another fact with no match.", source_node_uuid="C", target_node_uuid="D"),
        EdgeInfo(uuid="3", name="test_relation", fact="A relation that matches partially.", source_node_uuid="E", target_node_uuid="F"),
    ]

    mock_zep_tools_service.get_all_edges = MagicMock(return_value=mock_edges)

    result = mock_zep_tools_service._local_search(graph_id, query, limit=5, scope="edges")

    assert isinstance(result, SearchResult)
    assert result.query == query
    assert len(result.facts) == 2 # 包含 "test" 的边有2个 (第一个fact, 和第三个name)
    assert result.total_count == 2

    # 验证 get_all_edges 被调用
    mock_zep_tools_service.get_all_edges.assert_called_once_with(graph_id)

def test_local_search_with_nodes(mock_zep_tools_service):
    """测试基于节点的本地搜索。"""
    graph_id = "test_graph"
    query = "specific topic"

    # 模拟节点数据
    mock_nodes = [
        NodeInfo(uuid="A", name="Node A", labels=["Entity"], summary="This node discusses a specific topic in detail.", attributes={}),
        NodeInfo(uuid="B", name="Topic Node", labels=["Concept"], summary="General discussion.", attributes={}),
        NodeInfo(uuid="C", name="Unrelated", labels=["Person"], summary="Nothing to see here.", attributes={}),
    ]

    mock_zep_tools_service.get_all_nodes = MagicMock(return_value=mock_nodes)

    result = mock_zep_tools_service._local_search(graph_id, query, limit=5, scope="nodes")

    assert isinstance(result, SearchResult)
    assert result.query == query
    assert len(result.facts) == 2 # 包含 "topic" 的有 Node A (summary) 和 Node B (name)
    assert result.total_count == 2

    mock_zep_tools_service.get_all_nodes.assert_called_once_with(graph_id)

def test_local_search_both(mock_zep_tools_service):
    """测试同时包含边和节点的本地搜索。"""
    graph_id = "test_graph"
    query = "combined search"

    # 模拟边数据
    mock_edges = [
        EdgeInfo(uuid="1", name="relates", fact="A fact about a combined approach.", source_node_uuid="A", target_node_uuid="B"),
    ]

    # 模拟节点数据
    mock_nodes = [
        NodeInfo(uuid="A", name="Combined Node", labels=["Entity"], summary="A node about search.", attributes={}),
    ]

    mock_zep_tools_service.get_all_edges = MagicMock(return_value=mock_edges)
    mock_zep_tools_service.get_all_nodes = MagicMock(return_value=mock_nodes)

    result = mock_zep_tools_service._local_search(graph_id, query, limit=5, scope="both")

    assert isinstance(result, SearchResult)
    assert len(result.facts) == 2 # 1 edge fact + 1 node summary
    assert len(result.edges) == 1
    assert len(result.nodes) == 1

    mock_zep_tools_service.get_all_edges.assert_called_once_with(graph_id)
    mock_zep_tools_service.get_all_nodes.assert_called_once_with(graph_id)

def test_local_search_limit(mock_zep_tools_service):
    """测试返回结果数量限制。"""
    graph_id = "test_graph"
    query = "test"

    mock_edges = [
        EdgeInfo(uuid=str(i), name="relates", fact=f"test fact {i}", source_node_uuid="A", target_node_uuid="B")
        for i in range(10)
    ]

    mock_zep_tools_service.get_all_edges = MagicMock(return_value=mock_edges)

    result = mock_zep_tools_service._local_search(graph_id, query, limit=3, scope="edges")

    assert len(result.facts) == 3
    assert len(result.edges) == 3

def test_local_search_empty_query_or_no_matches(mock_zep_tools_service):
    """测试空查询或无匹配情况。"""
    graph_id = "test_graph"

    mock_zep_tools_service.get_all_edges = MagicMock(return_value=[])

    # 空查询处理：可能不会抛出异常，但返回0结果
    result = mock_zep_tools_service._local_search(graph_id, "", scope="edges")
    assert len(result.facts) == 0

    # 无匹配情况
    mock_zep_tools_service.get_all_edges = MagicMock(return_value=[
        EdgeInfo(uuid="1", name="rel", fact="unrelated", source_node_uuid="A", target_node_uuid="B")
    ])
    result = mock_zep_tools_service._local_search(graph_id, "nomatchkeyword", scope="edges")
    assert len(result.facts) == 0

def test_local_search_exception_handling(mock_zep_tools_service):
    """测试内部异常处理。"""
    graph_id = "test_graph"

    mock_zep_tools_service.get_all_edges = MagicMock(side_effect=Exception("Database error"))

    result = mock_zep_tools_service._local_search(graph_id, "test", scope="edges")

    # 根据代码，异常会被捕获并记录日志，返回空结果
    assert isinstance(result, SearchResult)
    assert len(result.facts) == 0
    assert len(result.edges) == 0
