import csv
import io
from types import SimpleNamespace

from app import create_app
from app.api import simulation as simulation_api
from app.config import Config
from app.services.export_service import CSVExporter, ExecutiveExporter

def test_executive_exporter_generates_valid_html_deck():
    exporter = ExecutiveExporter()

    report_data = {
        "title": "Service-change scenario exploration",
        "summary": "The synthetic run surfaced three paths to validate with people.",
        "sections": [
            {"title": "1. SYNTHETIC PATHS", "content": "Generated observations diverged after the second round."},
            {"title": "2. VALIDATION PLAN", "content": "Interview affected riders before making a decision."}
        ]
    }

    metrics_data = {
        "polarization_index": 0.42,
        "echo_chamber_score": 0.55,
        "engagement_gini": 0.38
    }

    html = exporter.generate_html_deck(report_data, metrics_data=metrics_data)

    assert "<!DOCTYPE html>" in html
    assert "Service-change scenario exploration" in html
    assert "0.42" in html
    assert "0.55" in html
    assert "SYNTHETIC PATHS" in html
    assert "VALIDATION PLAN" in html
    assert "0 HUMAN RESPONDENTS" in html
    assert "NO POPULATION REPRESENTED" in html
    assert "NOT PUBLIC OPINION" in html
    assert "NOT A CAUSAL ESTIMATE" in html
    assert "NOT CALIBRATED" in html
    assert "NOT A FORECAST" in html


def test_executive_exporter_escapes_model_generated_html():
    exporter = ExecutiveExporter()
    html = exporter.generate_html_deck({
        "title": '<img src=x onerror="alert(1)">',
        "summary": "</div><script>alert(2)</script>",
        "sections": [{
            "title": "<svg onload=alert(3)>",
            "content": '<a href="javascript:alert(4)">click</a>',
        }],
    })
    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "<svg onload" not in html
    assert "javascript:alert" in html
    assert "&lt;script&gt;" in html


def test_csv_exporter_neutralizes_spreadsheet_formulas():
    zep = SimpleNamespace(
        get_all_nodes=lambda _graph_id: [
            SimpleNamespace(
                labels=["Entity", "Person"],
                name="@malicious",
                summary="  =HYPERLINK(\"https://example.test\")",
            ),
        ],
        get_all_edges=lambda _graph_id: [
            SimpleNamespace(
                source_node_name="+cmd",
                source_node_uuid="source",
                target_node_name="-2+3",
                target_node_uuid="target",
                name="RELATES_TO",
                fact="safe",
                valid_at="",
                created_at="",
                is_expired=False,
            ),
        ],
    )
    rows = list(csv.DictReader(io.StringIO(CSVExporter(zep).export_graph("graph"))))
    assert rows[0]["Source"].startswith("'")
    assert rows[0]["Target"].startswith("'")
    assert rows[1]["Source"].startswith("'")
    assert rows[1]["Graph_Record"].startswith("'")
    assert all(row["Human_Respondents"] == "0" for row in rows)
    assert all(row["Causal_Evidence"] == "False" for row in rows)
    assert all(row["Calibration"] == "NOT_CALIBRATED" for row in rows)
    assert all(
        row["Record_Origin"] == "GRAPH_RECORD_ORIGIN_UNVERIFIED"
        for row in rows
    )
    assert not any(
        row["Record_Origin"] == "SOURCE_GRAPH_RECORD"
        for row in rows
    )
    assert all(
        "not independently verified" in row["Permitted_Interpretation"]
        for row in rows
    )
    assert all(
        "not evidence of causality" in row["Permitted_Interpretation"]
        for row in rows
    )
    assert all("Fact" not in row for row in rows)
    assert all("Evidence_Origin" not in row for row in rows)


def test_survey_export_marks_answers_as_model_generated():
    exporter = CSVExporter(SimpleNamespace())
    rows = list(csv.DictReader(io.StringIO(exporter.export_survey_results([
        {"agent_name": "Generated profile 7", "profession": "rider", "answer": "I might change routes."}
    ]))))

    assert rows[0]["response_origin"] == "MODEL_GENERATED"
    assert rows[0]["human_respondents"] == "0"
    assert rows[0]["population_represented"] == "none established"
    assert rows[0]["public_opinion_status"] == "not public opinion"
    assert rows[0]["forecast_status"] == "not a forecast"
    assert rows[0]["causal_evidence"] == "False"
    assert rows[0]["calibration"] == "NOT_CALIBRATED"


def test_generated_response_export_uses_truthful_route_and_filename(monkeypatch):
    monkeypatch.setattr(
        simulation_api,
        "ZepToolsService",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        Config,
        "APP_TOKEN",
        "test-app-token-32-characters-long",
    )
    app = create_app()
    app.config.update(TESTING=True, APP_TOKEN=None)

    response = app.test_client().post(
        "/api/simulation/sim_123/export/generated-responses",
        json={
            "results": [
                {
                    "agent_name": "Generated profile 7",
                    "profession": "rider",
                    "answer": "I might change routes.",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert "ATP_GENERATED_RESPONSES_sim_123_" in response.headers[
        "Content-Disposition"
    ]
    assert b"MODEL_GENERATED" in response.data
    assert b"human_respondents" in response.data
