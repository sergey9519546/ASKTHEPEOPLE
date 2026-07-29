import pytest
from app.services.export_service import ExecutiveExporter

def test_executive_exporter_generates_valid_html_deck():
    exporter = ExecutiveExporter()

    report_data = {
        "title": "Crisis Comms & Sentiment Analysis",
        "summary": "Public sentiment recovered by 34% post counter-statement.",
        "sections": [
            {"title": "1. VIRAL SPREAD", "content": "Initial negative posts reached 5,000 views."},
            {"title": "2. COUNTER MEASURES", "content": "Press release stabilized echo chamber score."}
        ]
    }

    metrics_data = {
        "polarization_index": 0.42,
        "echo_chamber_score": 0.55,
        "engagement_gini": 0.38
    }

    html = exporter.generate_html_deck(report_data, metrics_data=metrics_data)

    assert "<!DOCTYPE html>" in html
    assert "Crisis Comms & Sentiment Analysis" in html
    assert "0.42" in html
    assert "0.55" in html
    assert "VIRAL SPREAD" in html
    assert "COUNTER MEASURES" in html
