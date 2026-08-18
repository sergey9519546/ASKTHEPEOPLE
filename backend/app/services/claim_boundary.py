"""Shared disclosure contract for every synthetic-output surface."""

from typing import Any

GRAPH_RECORD_ORIGIN = "graph_record_origin_unverified"
GRAPH_RECORD_INTERPRETATION = (
    "Model-generated extraction from submitted or pre-existing graph material; "
    "not independently verified and not evidence of causality."
)
GENERATED_OUTPUT_DISCLOSURE_TEXT = (
    "SYNTHETIC SCENARIOS · 0 HUMAN RESPONDENTS · NO POPULATION REPRESENTED · "
    "NOT PUBLIC OPINION · NOT A CAUSAL ESTIMATE · NOT CALIBRATED · "
    "NOT A FORECAST"
)


def synthetic_output_disclosure() -> dict[str, Any]:
    """Return a fresh, serialization-safe copy of the product truth boundary."""
    return {
        "evidence_type": "synthetic",
        "human_respondents": 0,
        "population_represented": "none established",
        "forecast_status": "not a forecast",
        "public_opinion_status": "not public opinion",
        "causal_status": "not a causal estimate",
        "calibration": "not_calibrated",
        "testimony_status": "not testimony",
        "human_interview_status": "not a human interview",
        "external_validation": "none documented",
    }


def fictional_profile_disclosure() -> dict[str, Any]:
    """Return record-level truth metadata for a generated scenario profile."""
    return {
        "profile_origin": "fictional_model_generated",
        "human_respondents": 0,
        "is_biography": False,
        "is_representative": False,
        "is_forecast": False,
    }


def synthetic_activity_disclosure() -> dict[str, Any]:
    """Return record-level truth metadata for generated run activity."""
    return {
        "record_origin": "synthetic_simulation",
        "human_respondents": 0,
        "observed_human_behavior": False,
        "external_validation": False,
        "causal_evidence": False,
    }


def synthetic_config_disclosure() -> dict[str, Any]:
    """Return truth metadata for fictional run-control configuration."""
    return {
        "assumption_basis": "fictional_scenario_controls",
        "measured_human_behavior": False,
        "human_respondents": 0,
        "external_validation": False,
        "causal_evidence": False,
        "calibration": "not_calibrated",
    }


def model_proposed_schema_disclosure() -> dict[str, Any]:
    """Return truth metadata for a model-proposed organizing schema."""
    return {
        "record_origin": "model_proposed_schema",
        "external_validation": False,
        "causal_evidence": False,
        "interpretation": (
            "Model-proposed organizing schema; not a supplied-source fact, "
            "verified relationship, causal model, population description, "
            "or forecast."
        ),
    }


def graph_record_disclosure(record_text: str | None = None) -> dict[str, Any]:
    """Return record-level metadata without promoting graph text to evidence."""
    disclosure: dict[str, Any] = {
        "record_origin": GRAPH_RECORD_ORIGIN,
        "external_validation": False,
        "causal_evidence": False,
        "interpretation": GRAPH_RECORD_INTERPRETATION,
    }
    if record_text is not None:
        disclosure["record_text"] = record_text
    return disclosure
