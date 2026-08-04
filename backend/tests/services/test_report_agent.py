import pytest
import json
from unittest.mock import MagicMock
from app.services.report_agent import ReportAgent

@pytest.fixture
def agent():
    """Create a mock ReportAgent instance for testing"""
    # Create the agent with mock dependencies to avoid actual external calls
    return ReportAgent(
        graph_id="test_graph",
        simulation_id="test_sim",
        simulation_requirement="test req",
        llm_client=MagicMock(),
        zep_tools=MagicMock()
    )

def test_parse_tool_calls_xml_format(agent):
    """Test parsing XML format tool calls"""
    response = '''Some reasoning text...
<tool_call>
{"name": "insight_forge", "parameters": {"query": "test query"}}
</tool_call>
More text...
<tool_call>{"name": "quick_search", "parameters": {"topic": "test"}}</tool_call>
'''
    result = agent._parse_tool_calls(response)
    assert len(result) == 2
    assert result[0] == {"name": "insight_forge", "parameters": {"query": "test query"}}
    assert result[1] == {"name": "quick_search", "parameters": {"topic": "test"}}

def test_parse_tool_calls_bare_json_format(agent):
    """Test parsing bare JSON format (entire response is JSON)"""
    response = '{"name": "quick_search", "parameters": {"topic": "test"}}'
    result = agent._parse_tool_calls(response)
    assert len(result) == 1
    assert result[0] == {"name": "quick_search", "parameters": {"topic": "test"}}

def test_parse_tool_calls_json_with_tool_key(agent):
    """Test parsing JSON that uses 'tool' instead of 'name' and 'params' instead of 'parameters'"""
    response = '{"tool": "quick_search", "params": {"topic": "test"}}'
    result = agent._parse_tool_calls(response)
    assert len(result) == 1
    # The agent normalizes these keys internally
    assert result[0] == {"name": "quick_search", "parameters": {"topic": "test"}}

def test_parse_tool_calls_json_at_end(agent):
    """Test parsing JSON appended at the end of the response"""
    response = '''Let me search for that.
{"name": "insight_forge", "parameters": {"query": "test query"}}'''
    result = agent._parse_tool_calls(response)
    assert len(result) == 1
    assert result[0] == {"name": "insight_forge", "parameters": {"query": "test query"}}

def test_parse_tool_calls_invalid_json_xml(agent):
    """Test handling of invalid JSON inside XML tags"""
    response = '<tool_call>{"name": "test", broken json}</tool_call>'
    result = agent._parse_tool_calls(response)
    assert len(result) == 0

def test_parse_tool_calls_invalid_tool_name(agent):
    """Test handling of bare JSON with invalid tool name"""
    # VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}
    response = '{"name": "unknown_tool", "parameters": {}}'
    result = agent._parse_tool_calls(response)
    assert len(result) == 0

def test_parse_tool_calls_no_tool_call(agent):
    """Test response with no tool calls"""
    response = 'Just a regular response with no tool calls.'
    result = agent._parse_tool_calls(response)
    assert len(result) == 0
