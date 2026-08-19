"""
Capability Registry API

Endpoints for evidence-gated forecasting capability system.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md Phase 6
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.capability import (
    CapabilityCreate,
    CapabilityUpdate,
    CapabilityResponse,
    CapabilityClaimRequest,
    PermittedClaim,
    EvidenceLevel,
)
from app.services.capability_registry import CapabilityRegistryService

router = APIRouter(prefix="/api/capability", tags=["capability"])


@router.post("/register", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def register_capability(
    capability: CapabilityCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new capability with initial evidence level E0.
    
    Success on one capability key does not unlock claims for other keys.
    Each platform/population/outcome/horizon combination requires separate validation.
    """
    service = CapabilityRegistryService(db)
    
    # Check if capability already exists
    existing = await service.get_capability(
        platform=capability.platform,
        target_population=capability.target_population,
        outcome=capability.outcome,
        forecast_horizon=capability.forecast_horizon,
        model_release=capability.model_release,
        language=capability.language,
        geography=capability.geography,
        intervention_class=capability.intervention_class,
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Capability already registered: {existing.capability_id}",
        )
    
    return await service.register_capability(capability)


@router.get("/check", response_model=CapabilityResponse)
async def check_capability(
    platform: str,
    target_population: str,
    outcome: str,
    forecast_horizon: str,
    model_release: str,
    language: str = "en",
    geography: Optional[str] = None,
    intervention_class: str = "none",
    db: AsyncSession = Depends(get_db),
):
    """
    Check evidence level for a specific capability key.
    
    Returns 404 if capability not registered (defaults to E0 implicit).
    """
    service = CapabilityRegistryService(db)
    
    capability = await service.get_capability(
        platform=platform,
        target_population=target_population,
        outcome=outcome,
        forecast_horizon=forecast_horizon,
        model_release=model_release,
        language=language,
        geography=geography,
        intervention_class=intervention_class,
    )
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not registered",
        )
    
    return capability


@router.post("/claims/permitted", response_model=PermittedClaim)
async def get_permitted_claim(
    request: CapabilityClaimRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Get permitted external claim for a capability.
    
    This is the core truth boundary enforcement: claims are automatically
    derived from evidence level. No manual overrides allowed.
    
    **E0-E1:** "Synthetic simulation" (not a forecast)
    **E2:** "Historically benchmarked experimental simulation" (not a forecast)
    **E3:** "Out-of-sample experimental forecast" (experimental only)
    **E4:** "Prospectively validated forecast" (forecast claim permitted)
    **E5:** "Independently validated forecast" (externally replicated)
    **E6:** "Production forecast (monitored)" (continuously validated)
    
    If drift detected: "Forecast capability suspended pending revalidation"
    """
    service = CapabilityRegistryService(db)
    
    capability = await service.get_capability(
        platform=request.platform,
        target_population=request.target_population,
        outcome=request.outcome,
        forecast_horizon=request.forecast_horizon,
        model_release=request.model_release,
        language=request.language,
        geography=request.geography,
        intervention_class=request.intervention_class,
    )
    
    if not capability:
        # Not registered = E0 implicit
        return PermittedClaim(
            claim_text="Synthetic simulation (experimental)",
            scope=f"{request.platform} → {request.target_population} → {request.outcome}",
            restrictions=[
                "Not registered in capability registry",
                "No fidelity evidence",
                "Not a forecast",
            ],
            evidence_level="E0",
            is_forecast=False,
        )
    
    return service.get_permitted_claim(capability)


@router.patch("/{capability_id}/evidence", response_model=CapabilityResponse)
async def update_evidence_level(
    capability_id: UUID,
    evidence_level: EvidenceLevel,
    performance_metrics: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Update capability evidence level after validation.
    
    **Evidence progression:** Cannot skip levels without intermediate validation.
    E0 → E1 → E2 → E3 → E4 → E5 → E6
    
    Each level requires specific validation evidence:
    - E1: Engineering tests (reproducibility, schema)
    - E2: Historical backtests (skill vs baselines)
    - E3: Temporal holdouts (frozen cutoffs)
    - E4: Prospective forecasts (sealed predictions)
    - E5: External replication (independent evaluation)
    - E6: Production monitoring (ongoing drift checks)
    """
    service = CapabilityRegistryService(db)
    
    try:
        return await service.update_evidence_level(
            capability_id=capability_id,
            new_level=evidence_level,
            performance_metrics=performance_metrics,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{capability_id}/drift", response_model=CapabilityResponse)
async def update_drift_status(
    capability_id: UUID,
    drift_status: str,
    calibration_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Update drift and calibration status (production monitoring).
    
    **Drift statuses:**
    - `within_limits`: Performance stable
    - `degrading`: Performance declining but within tolerance
    - `out_of_limits`: Performance below threshold → capability suspended
    
    **Calibration statuses:**
    - `calibrated`: Within calibration error threshold
    - `miscalibrated`: Overconfident or underconfident
    - `uncalibrated`: No calibration evidence
    """
    service = CapabilityRegistryService(db)
    
    try:
        return await service.update_drift_status(
            capability_id=capability_id,
            drift_status=drift_status,
            calibration_status=calibration_status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/list", response_model=List[CapabilityResponse])
async def list_capabilities(
    platform: Optional[str] = None,
    evidence_level: Optional[EvidenceLevel] = None,
    min_evidence: Optional[EvidenceLevel] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List registered capabilities with optional filters.
    
    **Filters:**
    - `platform`: Filter by platform (reddit, twitter, etc.)
    - `evidence_level`: Exact evidence level (E0-E6)
    - `min_evidence`: Minimum evidence level (E3+ includes E3, E4, E5, E6)
    """
    service = CapabilityRegistryService(db)
    
    return await service.list_capabilities(
        platform=platform,
        evidence_level=evidence_level,
        min_evidence=min_evidence,
    )
