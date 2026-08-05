from types import SimpleNamespace

import pytest

from app import create_app
from app.api import graph as graph_api
from app.api import report as report_api
from app.api import simulation as simulation_api
from app.api.routes import export_routes, prep_routes, read_routes
from app.config import Config
from app.services.claim_boundary import (
    model_proposed_schema_disclosure,
    synthetic_output_disclosure,
)
from app.services.simulation_config_generator import SimulationParameters
from app.services.zep_entity_reader import EntityNode


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "APP_TOKEN", "test-app-token-32-characters-long")
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)
    return app.test_client()


def assert_synthetic_disclosure(payload):
    assert payload["disclosure"] == synthetic_output_disclosure()
    assert payload["disclosure"]["human_respondents"] == 0
    assert payload["disclosure"]["forecast_status"] == "not a forecast"
    assert payload["disclosure"]["public_opinion_status"] == "not public opinion"
    assert payload["disclosure"]["causal_status"] == "not a causal estimate"
    assert payload["disclosure"]["calibration"] == "not_calibrated"
    assert payload["disclosure"]["testimony_status"] == "not testimony"
    assert payload["disclosure"]["human_interview_status"] == (
        "not a human interview"
    )


def test_generated_profile_follow_up_uses_truthful_alias_and_disclosure(
    client,
    monkeypatch,
):
    captured = {}
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "check_env_alive",
        lambda _simulation_id: True,
    )

    def generated_response(**kwargs):
        captured.update(kwargs)
        return {"success": True, "response": "A fictional answer."}

    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "interview_agent",
        generated_response,
    )

    response = client.post(
        "/api/simulation/generated-response",
        json={
            "simulation_id": "sim_123",
            "agent_id": 7,
            "prompt": "What concern would this profile raise?",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_synthetic_disclosure(payload)
    assert captured["prompt"].startswith(
        "You are a fictional generated profile inside one synthetic scenario."
    )


def test_generated_interactions_alias_discloses_zero_humans(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    (tmp_path / "sim_123").mkdir()

    response = client.get(
        "/api/simulation/sim_123/generated-interactions"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["opinions"] == []
    assert_synthetic_disclosure(payload)


def test_graph_data_marks_each_edge_provenance_unverified(client, monkeypatch):
    monkeypatch.setattr(Config, "ZEP_API_KEY", "test-zep-key")

    class FakeBuilder:
        def __init__(self, api_key):
            assert api_key == "test-zep-key"

        def get_graph_data(self, _graph_id):
            return {
                "nodes": [],
                "edges": [{"fact": "A model-extracted relationship."}],
            }

    monkeypatch.setattr(graph_api, "GraphBuilderService", FakeBuilder)

    response = client.get("/api/graph/data/graph_123")

    assert response.status_code == 200
    payload = response.get_json()
    edge = payload["data"]["edges"][0]
    assert edge["record_text"] == edge["fact"]
    assert edge["record_origin"] == "graph_record_origin_unverified"
    assert edge["external_validation"] is False
    assert "not independently verified" in edge["interpretation"]
    assert_synthetic_disclosure(payload)


def test_project_ontology_is_labeled_as_a_model_proposed_schema(
    client,
    monkeypatch,
):
    project = SimpleNamespace(
        to_dict=lambda: {
            "project_id": "project_123",
            "files": [{"filename": "source.txt"}],
            "ontology": {
                "entity_types": [{"name": "Rider"}],
                "edge_types": [{"name": "MAY_AFFECT"}],
            },
            "analysis_summary": "A model-generated organizing summary.",
        }
    )
    monkeypatch.setattr(
        graph_api.ProjectManager,
        "get_project",
        lambda _project_id: project,
    )

    response = client.get("/api/graph/project/project_123")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["files"] == [{"filename": "source.txt"}]
    assert payload["data"]["ontology_status"] == (
        model_proposed_schema_disclosure()
    )
    assert payload["data"]["ontology_status"]["causal_evidence"] is False
    assert "not a supplied-source fact" in payload["data"][
        "ontology_status"
    ]["interpretation"]


def test_ontology_task_result_carries_schema_status(client, monkeypatch):
    task = SimpleNamespace(
        to_public_dict=lambda: {
            "task_id": "task_123",
            "status": "completed",
            "result": {
                "ontology": {"entity_types": [], "edge_types": []},
                "analysis_summary": "A model-generated organizing summary.",
            },
        }
    )

    class FakeTaskManager:
        def get_task(self, _task_id):
            return task

    monkeypatch.setattr(graph_api, "TaskManager", FakeTaskManager)

    response = client.get("/api/graph/task/task_123")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["result"]["ontology_status"] == (
        model_proposed_schema_disclosure()
    )


def test_related_report_records_are_not_exposed_as_citations(client, monkeypatch):
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_report",
        lambda _report_id: SimpleNamespace(report_id="report_123"),
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "_get_report_folder",
        lambda _report_id: "unused",
    )
    monkeypatch.setattr(report_api, "load_report_evidence", lambda _path: [])

    response = client.get("/api/report/report_123/related-records")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["relationship"] == "related_example_not_citation"
    assert_synthetic_disclosure(payload)


def test_entity_payload_marks_related_graph_records_unverified():
    entity = EntityNode(
        uuid="entity-1",
        name="Service constraint",
        labels=["Entity", "Constraint"],
        summary="A model-generated summary.",
        attributes={},
        related_edges=[{"fact": "A model-extracted relationship."}],
    )

    edge = entity.to_dict()["related_edges"][0]

    assert edge["record_text"] == edge["fact"]
    assert edge["record_origin"] == "graph_record_origin_unverified"
    assert edge["external_validation"] is False
    assert "not independently verified" in edge["interpretation"]


def test_debug_search_keeps_legacy_facts_but_adds_canonical_records(
    client,
    monkeypatch,
):
    result = SimpleNamespace(
        to_dict=lambda: {
            "facts": ["A model-extracted relationship."],
            "edges": [{"fact": "An edge record."}],
            "nodes": [],
            "total_count": 1,
        }
    )
    monkeypatch.setattr(
        report_api,
        "ZepToolsService",
        lambda: SimpleNamespace(search_graph=lambda **_kwargs: result),
    )

    response = client.post(
        "/api/report/tools/search",
        json={"graph_id": "graph_123", "query": "service", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["facts_deprecated"] is True
    assert payload["data"]["records"][0]["record_text"] == (
        payload["data"]["facts"][0]
    )
    assert payload["data"]["edges"][0]["record_origin"] == (
        "graph_record_origin_unverified"
    )
    assert_synthetic_disclosure(payload)


def test_profile_api_marks_every_profile_fictional(client, monkeypatch):
    monkeypatch.setattr(
        read_routes,
        "SimulationManager",
        lambda: SimpleNamespace(
            get_profiles=lambda _simulation_id, platform: [
                {
                    "realname": "Human-looking name",
                    "age": 30,
                    "gender": "other",
                    "persona": "A generated persona.",
                }
            ]
        ),
    )

    response = client.get("/api/simulation/sim_123/profiles")

    assert response.status_code == 200
    payload = response.get_json()
    profile = payload["data"]["profiles"][0]
    assert profile["profile_origin"] == "fictional_model_generated"
    assert profile["human_respondents"] == 0
    assert profile["is_biography"] is False
    assert profile["is_representative"] is False
    assert profile["is_forecast"] is False
    assert_synthetic_disclosure(payload)


def test_realtime_and_standalone_profile_apis_keep_fictional_metadata(
    client,
    monkeypatch,
    tmp_path,
):
    simulation_dir = tmp_path / "sim_123"
    simulation_dir.mkdir()
    (simulation_dir / "reddit_profiles.json").write_text(
        '[{"realname":"Profile A","persona":"Generated persona"}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))

    realtime = client.get(
        "/api/simulation/sim_123/profiles/realtime?platform=reddit"
    )
    assert realtime.status_code == 200
    realtime_payload = realtime.get_json()
    assert realtime_payload["data"]["profiles"][0]["profile_origin"] == (
        "fictional_model_generated"
    )
    assert_synthetic_disclosure(realtime_payload)

    filtered = SimpleNamespace(
        filtered_count=1,
        entities=[SimpleNamespace()],
        entity_types={"Community"},
    )
    monkeypatch.setattr(
        prep_routes,
        "ZepEntityReader",
        lambda: SimpleNamespace(
            filter_defined_entities=lambda **_kwargs: filtered
        ),
    )
    generated_profile = SimpleNamespace(
        to_reddit_format=lambda: {
            "realname": "Profile B",
            "persona": "Generated persona",
        }
    )
    monkeypatch.setattr(
        prep_routes,
        "OasisProfileGenerator",
        lambda: SimpleNamespace(
            generate_profiles_from_entities=lambda **_kwargs: [
                generated_profile
            ]
        ),
    )

    standalone = client.post(
        "/api/simulation/generate-profiles",
        json={"graph_id": "graph_123", "platform": "reddit"},
    )
    assert standalone.status_code == 200
    standalone_payload = standalone.get_json()
    assert standalone_payload["data"]["profiles"][0]["profile_origin"] == (
        "fictional_model_generated"
    )
    assert_synthetic_disclosure(standalone_payload)


@pytest.mark.parametrize(
    "path",
    [
        "/api/simulation/sim_123/run-status/detail",
        "/api/simulation/sim_123/actions",
        "/api/simulation/sim_123/timeline",
        "/api/simulation/sim_123/agent-stats",
        "/api/simulation/sim_123/posts",
        "/api/simulation/sim_123/comments",
    ],
)
def test_generated_activity_api_surfaces_disclose_even_when_empty(
    client,
    monkeypatch,
    path,
):
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_run_state",
        lambda _simulation_id: None,
    )
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_all_actions",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_timeline",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "get_agent_stats",
        lambda _simulation_id: [],
    )

    response = client.get(path)

    assert response.status_code == 200
    assert_synthetic_disclosure(response.get_json())


def test_observation_search_discloses_records_and_top_level(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        read_routes,
        "_safe_sim_dir",
        lambda _simulation_id: str(tmp_path),
    )
    monkeypatch.setattr(
        read_routes,
        "search_observations",
        lambda **_kwargs: {
            "query": "service",
            "count": 1,
            "results": [{"action_type": "CREATE_POST"}],
        },
    )

    response = client.get(
        "/api/simulation/sim_123/observations/search?q=service"
    )

    assert response.status_code == 200
    payload = response.get_json()
    record = payload["data"]["results"][0]
    assert record["record_origin"] == "synthetic_simulation"
    assert record["human_respondents"] == 0
    assert record["observed_human_behavior"] is False
    assert record["causal_evidence"] is False
    assert_synthetic_disclosure(payload)


def test_config_api_embeds_control_truth_and_top_level_disclosure(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        read_routes,
        "SimulationManager",
        lambda: SimpleNamespace(
            get_simulation_config=lambda _simulation_id: {
                "agent_configs": [{"stance": "neutral"}]
            }
        ),
    )

    response = client.get("/api/simulation/sim_123/config")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["truth_status"] == synthetic_output_disclosure()
    assert payload["data"]["control_metadata"]["assumption_basis"] == (
        "fictional_scenario_controls"
    )
    assert payload["data"]["control_metadata"]["measured_human_behavior"] is False
    assert payload["data"]["control_metadata"]["causal_evidence"] is False
    assert_synthetic_disclosure(payload)


def test_new_config_serialization_embeds_truth_contract():
    payload = SimulationParameters(
        simulation_id="sim_123",
        project_id="project_123",
        graph_id="graph_123",
        simulation_requirement="Explore possible paths.",
    ).to_dict()

    assert payload["truth_status"] == synthetic_output_disclosure()
    assert payload["control_metadata"]["assumption_basis"] == (
        "fictional_scenario_controls"
    )
    assert payload["control_metadata"]["measured_human_behavior"] is False
    assert payload["control_metadata"]["causal_evidence"] is False


def test_realtime_and_downloaded_configs_embed_truth_status(
    client,
    monkeypatch,
    tmp_path,
):
    simulation_dir = tmp_path / "sim_123"
    simulation_dir.mkdir()
    (simulation_dir / "simulation_config.json").write_text(
        '{"agent_configs":[{"stance":"neutral"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(Config, "OASIS_SIMULATION_DATA_DIR", str(tmp_path))
    fake_manager = lambda: SimpleNamespace(
        _get_simulation_dir=lambda _simulation_id: str(simulation_dir)
    )
    # /config/realtime and /config/download both moved out of the simulation.py
    # controller: realtime lives in read_routes, download in export_routes.
    # Each resolves SimulationManager from its own module globals, so both
    # need patching.
    monkeypatch.setattr(read_routes, "SimulationManager", fake_manager)
    monkeypatch.setattr(export_routes, "SimulationManager", fake_manager)

    realtime = client.get("/api/simulation/sim_123/config/realtime")
    assert realtime.status_code == 200
    realtime_payload = realtime.get_json()
    assert realtime_payload["data"]["config"]["truth_status"] == (
        synthetic_output_disclosure()
    )
    assert_synthetic_disclosure(realtime_payload)

    downloaded = client.get("/api/simulation/sim_123/config/download")
    assert downloaded.status_code == 200
    downloaded_payload = downloaded.get_json()
    assert downloaded_payload["truth_status"] == synthetic_output_disclosure()
    assert downloaded_payload["control_metadata"]["causal_evidence"] is False


def test_report_objects_and_standalone_sections_disclose_synthetic_origin(
    client,
    monkeypatch,
    tmp_path,
):
    report = SimpleNamespace(
        report_id="report_123",
        status=report_api.ReportStatus.COMPLETED,
        to_dict=lambda: {
            "report_id": "report_123",
            "markdown_content": "Generated claim text.",
        },
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_report",
        lambda _report_id: report,
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_report_by_simulation",
        lambda _simulation_id: report,
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "list_reports",
        lambda **_kwargs: [report],
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_generated_sections",
        lambda _report_id: [
            {"section_index": 1, "content": "Generated section claim."}
        ],
    )
    section_path = tmp_path / "section_01.md"
    section_path.write_text("Generated section claim.", encoding="utf-8")
    monkeypatch.setattr(
        report_api.ReportManager,
        "_get_section_path",
        lambda _report_id, _section_index: str(section_path),
    )

    for path in (
        "/api/report/report_123",
        "/api/report/by-simulation/sim_123",
        "/api/report/list",
        "/api/report/report_123/sections",
        "/api/report/report_123/section/1",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert_synthetic_disclosure(response.get_json())


def test_report_log_surfaces_keep_the_synthetic_disclosure(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_agent_log",
        lambda _report_id, from_line=0: {
            "logs": [{"action": "llm_response", "content": "Generated text."}],
            "from_line": from_line,
        },
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_agent_log_stream",
        lambda _report_id: [{"action": "llm_response"}],
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_console_log",
        lambda _report_id, from_line=0: {
            "logs": ["Generated report activity."],
            "from_line": from_line,
        },
    )
    monkeypatch.setattr(
        report_api.ReportManager,
        "get_console_log_stream",
        lambda _report_id: ["Generated report activity."],
    )

    for path in (
        "/api/report/report_123/agent-log",
        "/api/report/report_123/agent-log/stream",
        "/api/report/report_123/console-log",
        "/api/report/report_123/console-log/stream",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert_synthetic_disclosure(response.get_json())


def test_stop_run_state_keeps_the_synthetic_disclosure(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        simulation_api.SimulationRunner,
        "stop_simulation",
        lambda _simulation_id: SimpleNamespace(
            to_dict=lambda: {
                "simulation_id": "sim_123",
                "runner_status": "stopped",
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(
        simulation_api,
        "SimulationManager",
        lambda: SimpleNamespace(get_simulation=lambda _simulation_id: None),
    )

    response = client.post(
        "/api/simulation/stop",
        json={"simulation_id": "sim_123"},
    )

    assert response.status_code == 200
    assert_synthetic_disclosure(response.get_json())
