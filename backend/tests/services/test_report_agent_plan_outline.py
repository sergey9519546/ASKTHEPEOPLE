"""Tests for ReportAgent.plan_outline.

Salvaged from origin/test-report-agent-plan-outline-5579421567871858887. The
branch's assertions described an older plan_outline: Chinese progress strings
and an outline whose sections came from the LLM. Both changed. The section
expectations are now written against REQUIRED_SECTION_TITLES, because that is
the actual contract -- _ensure_required_outline_sections runs on the success
path too, so the LLM cannot add, drop, or rename a section.
"""

from unittest.mock import MagicMock

from app.services.report_agent import ReportAgent, ReportOutline


def _agent(mock_llm, mock_zep_tools, requirement="Test requirement"):
    return ReportAgent(
        graph_id="test_graph",
        simulation_id="test_sim",
        simulation_requirement=requirement,
        llm_client=mock_llm,
        zep_tools=mock_zep_tools,
    )


def test_plan_outline_success():
    mock_llm = MagicMock()
    mock_llm.chat_json.return_value = {
        "title": "Mock Report Title",
        "summary": "Mock Report Summary",
        "sections": [
            {"title": "Section 1", "content": ""},
            {"title": "Section 2", "content": ""},
        ],
    }

    mock_zep_tools = MagicMock()
    mock_zep_tools.get_simulation_context.return_value = {
        "graph_statistics": {
            "total_nodes": 100,
            "total_edges": 200,
            "entity_types": {"Person": 50, "Organization": 50},
        },
        "total_entities": 100,
        "related_facts": [{"fact": "Fact 1"}, {"fact": "Fact 2"}],
    }

    agent = _agent(mock_llm, mock_zep_tools)
    progress_callback = MagicMock()

    outline = agent.plan_outline(progress_callback=progress_callback)

    mock_zep_tools.get_simulation_context.assert_called_once_with(
        graph_id="test_graph",
        simulation_requirement="Test requirement",
    )

    assert mock_llm.chat_json.call_count == 1
    call_kwargs = mock_llm.chat_json.call_args[1]
    assert len(call_kwargs["messages"]) == 2
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][1]["role"] == "user"
    user_prompt = call_kwargs["messages"][1]["content"]
    assert "Test requirement" in user_prompt
    assert "100" in user_prompt  # total_nodes / total_entities
    assert "200" in user_prompt  # total_edges

    assert isinstance(outline, ReportOutline)
    assert outline.title == "Mock Report Title"
    assert outline.summary == "Mock Report Summary"

    # The LLM proposed "Section 1"/"Section 2"; neither survives. Every report
    # carries the same five sections so that the uncertainty and
    # validate-with-people sections cannot be dropped by a model response.
    assert [s.title for s in outline.sections] == ReportAgent.REQUIRED_SECTION_TITLES

    assert progress_callback.call_count == 4
    progress_callback.assert_any_call(
        "planning", 0, "Analyzing Simulation requirement..."
    )
    progress_callback.assert_any_call("planning", 30, "Generating Report outline...")
    progress_callback.assert_any_call("planning", 80, "Parsing outline structure...")
    progress_callback.assert_any_call("planning", 100, "Outline planning complete")


def test_plan_outline_falls_back_without_raising():
    mock_llm = MagicMock()
    mock_llm.chat_json.side_effect = Exception("LLM Error")

    mock_zep_tools = MagicMock()
    mock_zep_tools.get_simulation_context.return_value = {}

    agent = _agent(mock_llm, mock_zep_tools)
    progress_callback = MagicMock()

    outline = agent.plan_outline(progress_callback=progress_callback)

    assert isinstance(outline, ReportOutline)
    assert outline.title == "Synthetic Scenario Exploration Report"
    # The fallback summary is load-bearing: a failed outline still must not
    # read as a forecast over real respondents.
    assert "0 human respondents" in outline.summary
    assert "not a forecast" in outline.summary
    assert [s.title for s in outline.sections] == ReportAgent.REQUIRED_SECTION_TITLES

    # Only the two callbacks before the LLM call fire.
    assert progress_callback.call_count == 2
    progress_callback.assert_any_call(
        "planning", 0, "Analyzing Simulation requirement..."
    )
    progress_callback.assert_any_call("planning", 30, "Generating Report outline...")


def test_plan_outline_no_progress_callback():
    mock_llm = MagicMock()
    mock_llm.chat_json.return_value = {
        "title": "Title",
        "summary": "Summary",
        "sections": [{"title": "Sec", "content": ""}],
    }

    mock_zep_tools = MagicMock()
    mock_zep_tools.get_simulation_context.return_value = {}

    outline = _agent(mock_llm, mock_zep_tools, requirement="Test req").plan_outline()

    assert outline.title == "Title"
