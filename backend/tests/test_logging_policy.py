import logging
from types import SimpleNamespace

from app.config import Config
from app.services import report_agent as report_agent_module
from app.services import zep_tools as zep_tools_module
from app.services.oasis_profile_generator import (
    OasisAgentProfile,
    OasisProfileGenerator,
)
from app.services.report_agent import ReportAgent
from app.services.report_agent import ReportLogger
from app.services.zep_tools import ZepToolsService
from app.utils.logger import _ProductionPrivacyFilter, _configured_level


def test_production_log_level_cannot_drop_below_info(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "false")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert _configured_level() == logging.INFO


def test_debug_mode_may_enable_debug_logging(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert _configured_level() == logging.DEBUG


def test_production_logging_suppresses_error_details(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "false")
    record = logging.LogRecord(
        "askthepeople.provider",
        logging.ERROR,
        __file__,
        1,
        "Provider failed: prompt and upstream body sk-privatevalue",
        (),
        None,
    )

    assert _ProductionPrivacyFilter().filter(record) is True
    rendered = record.getMessage()
    assert "prompt and upstream" not in rendered
    assert "sk-privatevalue" not in rendered
    assert "details suppressed" in rendered


def test_production_logging_redacts_credentials_at_info(monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "false")
    record = logging.LogRecord(
        "askthepeople.request",
        logging.INFO,
        __file__,
        1,
        "provider api_key=sk-privatevalue",
        (),
        None,
    )

    _ProductionPrivacyFilter().filter(record)
    assert "sk-privatevalue" not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()


def test_report_trace_omits_prompts_reasoning_and_raw_tool_payloads(
    monkeypatch,
    tmp_path,
):
    private_text = "private-user-source-marker-8fd91b"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    trace = ReportLogger("report_privacy")

    trace.log_start("sim_1", "graph_1", private_text)
    trace.log_planning_context({"records": private_text})
    trace.log_react_thought("Section", 1, 1, private_text)
    trace.log_tool_call("Section", 1, "quick_search", {"query": private_text}, 1)
    trace.log_tool_result("Section", 1, "quick_search", private_text, 1)
    trace.log_llm_response("Section", 1, private_text, 1, False, False)
    trace.log_error(private_text, "generating")

    rendered = trace.log_file_path
    with open(rendered, encoding="utf-8") as handle:
        trace_text = handle.read()
    assert private_text not in trace_text


def test_report_tool_info_log_records_parameter_names_not_values(monkeypatch):
    private_text = "private-tool-query-06d2"
    messages = []

    class _Result:
        def to_text(self):
            return "result"

    class _ZepTools:
        def quick_search(self, **_kwargs):
            return _Result()

    agent = ReportAgent.__new__(ReportAgent)
    agent.graph_id = "graph-1"
    agent.simulation_id = "sim-1"
    agent.simulation_requirement = "scenario"
    agent.zep_tools = _ZepTools()
    agent._generation_lease = None

    monkeypatch.setattr(
        report_agent_module.logger,
        "info",
        lambda message, *args, **_kwargs: messages.append(
            message % args if args else str(message)
        ),
    )

    agent._execute_tool("quick_search", {"query": private_text, "limit": 2})

    rendered = "\n".join(messages)
    assert private_text not in rendered
    assert "query" in rendered
    assert "limit" in rendered


def test_generated_profile_console_does_not_print_private_profile_in_production(
    monkeypatch,
    capsys,
):
    private_text = "private-profile-marker-b899"
    monkeypatch.setattr(Config, "DEBUG", False)
    profile = OasisAgentProfile(
        user_id=1,
        user_name="private_user",
        name=private_text,
        bio=private_text,
        persona=private_text,
    )

    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)
    generator._print_generated_profile(private_text, "Person", profile)

    assert private_text not in capsys.readouterr().out


def test_zep_context_info_log_records_length_not_requirement(monkeypatch):
    private_text = "private-simulation-requirement-814f"
    messages = []
    service = ZepToolsService.__new__(ZepToolsService)
    service.search_graph = lambda **_kwargs: SimpleNamespace(facts=[])
    service.get_graph_statistics = lambda _graph_id: {}
    service.get_all_nodes = lambda _graph_id: []

    monkeypatch.setattr(
        zep_tools_module.logger,
        "info",
        lambda message, *args, **_kwargs: messages.append(
            message % args if args else str(message)
        ),
    )

    service.get_simulation_context("graph-1", private_text)

    rendered = "\n".join(messages)
    assert private_text not in rendered
    assert str(len(private_text)) in rendered
