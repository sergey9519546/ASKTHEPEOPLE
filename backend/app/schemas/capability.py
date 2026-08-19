"""
Capability Registry Schemas

Pydantic models for evidence-gated forecasting capability system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceLevel(str, Enum):
    """Evidence levels for capability validation."""
    E0 = "E0"  # Untested
    E1 = "E1"  # Engineering validated
    E2 = "E2"  # Retrospectively benchmarked
    E3 = "E3"  # Temporally validated
    E4 = "E4"  # Prospectively validated
    E5 = "E5"  # Externally replicated
    E6 = "E6"  # Production monitored


class RunMode(str, Enum):
    """Run modes with different truth boundaries."""
    SCENARIO_EXPLORATION = "SCENARIO_EXPLORATION"
    RETROSPECTIVE_EVALUATION = "RETROSPECTIVE_EVALUATION"
    PROSPECTIVE_SHADOW_FORECAST = "PROSPECTIVE_SHADOW_FORECAST"
    VALIDATED_FORECAST = "VALIDATED_FORECAST"
    CAUSAL_COUNTERFACTUAL = "CAUSAL_COUNTERFACTUAL"


class CapabilityKey(BaseModel):
    """Narrow capability key (success on one key does not unlock others)."""
    platform: str = Field(..., description="Platform: reddit, twitter, linkedin, etc.")
    target_population: str = Field(..., description="Target population/community")
    outcome: str = Field(..., description="Outcome to predict")
    forecast_horizon: str = Field(..., description="Forecast horizon (e.g., '14_days')")
    language: str = Field(default="en", description="Language code")
    geography: Optional[str] = Field(None, description="Geographic scope")
    intervention_class: str = Field(default="none", description="Intervention type")
    model_release: str = Field(..., description="Model version")


class CapabilityCreate(CapabilityKey):
    """Create new capability registration."""
    pass


class CapabilityUpdate(BaseModel):
    """Update capability evidence or status."""
    evidence_level: Optional[EvidenceLevel] = None
    calibration_status: Optional[str] = None
    drift_status: Optional[str] = None
    performance_metrics: Optional[Dict] = None


class CapabilityResponse(CapabilityKey):
    """Capability with evidence level and status."""
    capability_id: UUID
    evidence_level: str
    calibration_status: str
    drift_status: str
    performance_metrics: Dict
    last_validated: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermittedClaim(BaseModel):
    """Permitted external claim based on evidence level."""
    claim_text: str = Field(..., description="Permitted claim text")
    scope: str = Field(..., description="Registered scope")
    restrictions: List[str] = Field(..., description="What cannot be claimed")
    evidence_level: str = Field(..., description="Evidence level (E0-E6)")
    is_forecast: bool = Field(..., description="Whether 'forecast' language permitted")


class CapabilityClaimRequest(BaseModel):
    """Request permitted claim for capability."""
    platform: str
    target_population: str
    outcome: str
    forecast_horizon: str
    model_release: str
    language: str = "en"
    geography: Optional[str] = None
    intervention_class: str = "none"
