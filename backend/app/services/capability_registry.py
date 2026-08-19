"""
Capability Registry Service

Tracks evidence levels for narrow capability keys and generates permitted claims.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md Phase 1.1 + 6.1
"""

from datetime import datetime
from typing import Dict, Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CapabilityRegistry, BacktestResult, SealedForecast
from app.schemas.capability import (
    CapabilityKey,
    CapabilityCreate,
    CapabilityUpdate,
    CapabilityResponse,
    EvidenceLevel,
    PermittedClaim,
)


class CapabilityRegistryService:
    """Service for managing capability evidence and permitted claims."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_capability(
        self, capability: CapabilityCreate
    ) -> CapabilityResponse:
        """
        Register a new capability with initial evidence level E0.
        
        Args:
            capability: Capability key + metadata
            
        Returns:
            Registered capability with ID
        """
        db_capability = CapabilityRegistry(
            capability_id=uuid4(),
            platform=capability.platform,
            target_population=capability.target_population,
            outcome=capability.outcome,
            forecast_horizon=capability.forecast_horizon,
            language=capability.language or "en",
            geography=capability.geography,
            intervention_class=capability.intervention_class or "none",
            model_release=capability.model_release,
            evidence_level="E0",
            calibration_status="uncalibrated",
            drift_status="unknown",
            performance_metrics={},
            last_validated=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.session.add(db_capability)
        await self.session.commit()
        await self.session.refresh(db_capability)
        
        return CapabilityResponse.from_orm(db_capability)

    async def get_capability(
        self,
        platform: str,
        target_population: str,
        outcome: str,
        forecast_horizon: str,
        model_release: str,
        language: str = "en",
        geography: Optional[str] = None,
        intervention_class: str = "none",
    ) -> Optional[CapabilityResponse]:
        """
        Get capability by key components.
        
        Returns:
            Capability if found, None otherwise
        """
        stmt = select(CapabilityRegistry).where(
            and_(
                CapabilityRegistry.platform == platform,
                CapabilityRegistry.target_population == target_population,
                CapabilityRegistry.outcome == outcome,
                CapabilityRegistry.forecast_horizon == forecast_horizon,
                CapabilityRegistry.model_release == model_release,
                CapabilityRegistry.language == language,
                CapabilityRegistry.geography == geography,
                CapabilityRegistry.intervention_class == intervention_class,
            )
        )
        result = await self.session.execute(stmt)
        capability = result.scalar_one_or_none()
        
        if capability:
            return CapabilityResponse.from_orm(capability)
        return None

    async def update_evidence_level(
        self,
        capability_id: UUID,
        new_level: EvidenceLevel,
        performance_metrics: Optional[Dict] = None,
    ) -> CapabilityResponse:
        """
        Update capability evidence level after validation.
        
        Args:
            capability_id: Capability UUID
            new_level: New evidence level (E0-E6)
            performance_metrics: Optional performance data
            
        Returns:
            Updated capability
        """
        stmt = select(CapabilityRegistry).where(
            CapabilityRegistry.capability_id == capability_id
        )
        result = await self.session.execute(stmt)
        capability = result.scalar_one_or_none()
        
        if not capability:
            raise ValueError(f"Capability {capability_id} not found")
        
        # Validate evidence level progression (cannot skip levels without evidence)
        current = EvidenceLevel(capability.evidence_level)
        if new_level.value > current.value + 1:
            raise ValueError(
                f"Cannot jump from {current} to {new_level} without intermediate validation"
            )
        
        capability.evidence_level = new_level.value
        capability.last_validated = datetime.utcnow()
        capability.updated_at = datetime.utcnow()
        
        if performance_metrics:
            capability.performance_metrics = performance_metrics
        
        await self.session.commit()
        await self.session.refresh(capability)
        
        return CapabilityResponse.from_orm(capability)

    async def update_drift_status(
        self,
        capability_id: UUID,
        drift_status: str,
        calibration_status: Optional[str] = None,
    ) -> CapabilityResponse:
        """
        Update drift and calibration status (production monitoring).
        
        Args:
            capability_id: Capability UUID
            drift_status: "within_limits", "degrading", "out_of_limits"
            calibration_status: Optional calibration status
            
        Returns:
            Updated capability
        """
        stmt = select(CapabilityRegistry).where(
            CapabilityRegistry.capability_id == capability_id
        )
        result = await self.session.execute(stmt)
        capability = result.scalar_one_or_none()
        
        if not capability:
            raise ValueError(f"Capability {capability_id} not found")
        
        capability.drift_status = drift_status
        if calibration_status:
            capability.calibration_status = calibration_status
        capability.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(capability)
        
        return CapabilityResponse.from_orm(capability)

    def get_permitted_claim(self, capability: CapabilityResponse) -> PermittedClaim:
        """
        Generate permitted claim text based on evidence level and status.
        
        This is the core truth boundary enforcement function. External claims
        are automatically derived from evidence level — no manual overrides.
        
        Args:
            capability: Capability with evidence level
            
        Returns:
            Permitted claim with text, scope, and restrictions
        """
        level = EvidenceLevel(capability.evidence_level)
        
        # Check drift status first (production monitoring)
        if capability.drift_status == "out_of_limits":
            return PermittedClaim(
                claim_text="Forecast capability suspended pending revalidation",
                scope="N/A",
                restrictions=[
                    "This capability has detected performance degradation",
                    "No forecast claims permitted until revalidated",
                ],
                evidence_level=level.value,
                is_forecast=False,
            )
        
        # E0: Untested
        if level == EvidenceLevel.E0:
            return PermittedClaim(
                claim_text="Synthetic simulation (experimental)",
                scope=self._format_scope(capability),
                restrictions=[
                    "No fidelity evidence",
                    "Not a forecast",
                    "Not validated against real-world outcomes",
                ],
                evidence_level="E0",
                is_forecast=False,
            )
        
        # E1: Engineering validated
        if level == EvidenceLevel.E1:
            return PermittedClaim(
                claim_text="Synthetic simulation (validated engineering)",
                scope=self._format_scope(capability),
                restrictions=[
                    "Reproducible and schema-valid",
                    "Not a forecast",
                    "No real-world fidelity evidence",
                ],
                evidence_level="E1",
                is_forecast=False,
            )
        
        # E2: Retrospectively benchmarked
        if level == EvidenceLevel.E2:
            return PermittedClaim(
                claim_text="Historically benchmarked experimental simulation",
                scope=self._format_scope(capability),
                restrictions=[
                    "Demonstrates historical skill against baselines",
                    "Not a forecast (retrospective only)",
                    "Temporal leakage and hindsight bias possible",
                ],
                evidence_level="E2",
                is_forecast=False,
            )
        
        # E3: Temporally validated
        if level == EvidenceLevel.E3:
            return PermittedClaim(
                claim_text="Out-of-sample experimental forecast",
                scope=self._format_scope(capability),
                restrictions=[
                    "Passed frozen temporal holdouts",
                    "Not decision-grade",
                    "Prospective validation pending",
                ],
                evidence_level="E3",
                is_forecast=True,
            )
        
        # E4: Prospectively validated
        if level == EvidenceLevel.E4:
            return PermittedClaim(
                claim_text=f"Prospectively validated forecast for {self._format_scope(capability)}",
                scope=self._format_scope(capability),
                restrictions=[
                    "Passed sealed forward-looking forecasts",
                    "Claims valid only within registered scope",
                    "Does not generalize to other domains/populations without separate validation",
                ],
                evidence_level="E4",
                is_forecast=True,
            )
        
        # E5: Externally replicated
        if level == EvidenceLevel.E5:
            return PermittedClaim(
                claim_text=f"Independently validated forecast for {self._format_scope(capability)}",
                scope=self._format_scope(capability),
                restrictions=[
                    "Independent evaluation confirms performance",
                    "Claims valid only within registered scope",
                    "Does not generalize to other domains/populations without separate validation",
                ],
                evidence_level="E5",
                is_forecast=True,
            )
        
        # E6: Production monitored
        if level == EvidenceLevel.E6:
            return PermittedClaim(
                claim_text=f"Production forecast (monitored) for {self._format_scope(capability)}",
                scope=self._format_scope(capability),
                restrictions=[
                    "Current performance within calibration limits",
                    "Continuously monitored for drift",
                    "Claims valid only within registered scope",
                ],
                evidence_level="E6",
                is_forecast=True,
            )
        
        # Fallback (should never reach here)
        return PermittedClaim(
            claim_text="Unknown evidence level",
            scope="N/A",
            restrictions=["Evidence level not recognized"],
            evidence_level="E0",
            is_forecast=False,
        )

    def _format_scope(self, capability: CapabilityResponse) -> str:
        """Format capability scope as human-readable string."""
        parts = [
            capability.platform,
            capability.target_population,
            capability.outcome,
            f"{capability.forecast_horizon} horizon",
        ]
        if capability.geography:
            parts.append(capability.geography)
        return " → ".join(parts)

    async def list_capabilities(
        self,
        platform: Optional[str] = None,
        evidence_level: Optional[EvidenceLevel] = None,
        min_evidence: Optional[EvidenceLevel] = None,
    ) -> List[CapabilityResponse]:
        """
        List registered capabilities with optional filters.
        
        Args:
            platform: Filter by platform
            evidence_level: Filter by exact evidence level
            min_evidence: Filter by minimum evidence level
            
        Returns:
            List of capabilities
        """
        stmt = select(CapabilityRegistry)
        
        if platform:
            stmt = stmt.where(CapabilityRegistry.platform == platform)
        
        if evidence_level:
            stmt = stmt.where(CapabilityRegistry.evidence_level == evidence_level.value)
        elif min_evidence:
            # Filter by minimum evidence level (E3+ includes E3, E4, E5, E6)
            levels = [f"E{i}" for i in range(int(min_evidence.value[1]), 7)]
            stmt = stmt.where(CapabilityRegistry.evidence_level.in_(levels))
        
        result = await self.session.execute(stmt)
        capabilities = result.scalars().all()
        
        return [CapabilityResponse.from_orm(c) for c in capabilities]
