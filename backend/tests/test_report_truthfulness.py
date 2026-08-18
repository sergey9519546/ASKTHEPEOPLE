from app.services.report_agent import (
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    PLAN_SYSTEM_PROMPT,
    REACT_OBSERVATION_TEMPLATE,
    SECTION_SYSTEM_PROMPT_TEMPLATE,
    GENERATED_REPORT_DISCLOSURE,
    Report,
    ReportAgent,
    ReportOutline,
    ReportSection,
    ReportStatus,
)
from app.services.claim_boundary import synthetic_output_disclosure
from app.services.report_evidence import _evidence_metadata


def test_report_disclosure_is_explicit_and_non_predictive():
    disclosure = GENERATED_REPORT_DISCLOSURE.lower()
    assert "human respondents: 0" in disclosure
    assert "evidence type: synthetic" in disclosure
    assert "not a survey" in disclosure
    assert "forecast" in disclosure
    assert "prediction" in disclosure
    assert "validate" in disclosure

    markdown = ReportOutline(
        title="Scenario",
        summary="Possible paths",
        sections=[ReportSection(title="Path A", content="Generated activity")],
    ).to_markdown()
    assert GENERATED_REPORT_DISCLOSURE in markdown


def test_report_serializers_keep_structured_truth_when_content_is_detached():
    section = ReportSection(title="Path A", content="Generated activity")
    outline = ReportOutline(
        title="Scenario",
        summary="Possible paths",
        sections=[section],
    )
    report = Report(
        report_id="report_123",
        simulation_id="sim_123",
        graph_id="graph_123",
        simulation_requirement="Explore paths",
        status=ReportStatus.COMPLETED,
        outline=outline,
        markdown_content="Generated report content.",
    )

    assert section.to_dict()["truth_status"] == synthetic_output_disclosure()
    assert outline.to_dict()["truth_status"] == synthetic_output_disclosure()
    assert report.to_dict()["truth_status"] == synthetic_output_disclosure()


def test_report_prompts_enforce_synthetic_claim_boundary():
    combined = "\n".join(
        [
            PLAN_SYSTEM_PROMPT,
            SECTION_SYSTEM_PROMPT_TEMPLATE,
            CHAT_SYSTEM_PROMPT_TEMPLATE,
        ]
    ).lower()
    assert combined.count("human respondents: 0") >= 3
    assert "not a survey" in combined
    assert "not a forecast" in combined
    assert "synthetic observation" in combined
    assert "source facts" in combined
    assert "validate with real people" in combined
    assert "preview of the future" not in combined
    assert "predictions of future human behavior" not in combined

    observation_instruction = " ".join(
        REACT_OBSERVATION_TEMPLATE.lower().split()
    )
    assert "label synthetic excerpts as generated" in observation_instruction
    assert "graph text as origin-unverified" in observation_instruction
    assert "never present either as a" in observation_instruction
    assert "supplied-source citation" in observation_instruction
    assert "must cite original text above" not in observation_instruction


def test_required_outline_is_fixed_to_truth_preserving_sections():
    agent = object.__new__(ReportAgent)
    outline = ReportOutline(
        title="Misleading",
        summary="Misleading",
        sections=[
            ReportSection(title="Likely outcome"),
            ReportSection(
                title="Possible Scenario Paths",
                content="Preserve generated content",
            ),
        ],
    )

    normalized = agent._ensure_required_outline_sections(outline)
    assert [section.title for section in normalized.sections] == (
        ReportAgent.REQUIRED_SECTION_TITLES
    )
    assert normalized.sections[1].content == "Preserve generated content"


def test_evidence_metadata_has_no_calibrated_confidence():
    observation = _evidence_metadata("post")
    assumption = _evidence_metadata("scheduled_event")

    assert observation["evidence_class"] == "synthetic_observation"
    assert assumption["evidence_class"] == "configuration_assumption"
    for item in (observation, assumption):
        assert item["human_respondents"] == 0
        assert item["external_validation"] is False
        assert item["calibration"] == "not_calibrated"
        assert "confidence" not in item
