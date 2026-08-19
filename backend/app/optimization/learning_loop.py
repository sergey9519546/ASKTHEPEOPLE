"""
Automatic Learning Loop: Forecast → Score → Update θ → Repeat

This is the closed-loop system that makes the engine improve over time.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md Phase 5 + "Reality is the final evaluator"
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SealedForecast, BacktestResult, CapabilityRegistry
from app.optimization.theta_optimizer import ThetaOptimizer, ThetaParameters
from app.optimization.multi_objective_loss import (
    MultiObjectiveLoss,
    SimulationOutput,
    RealWorldData,
    create_default_loss,
)


class AutomaticLearningLoop:
    """
    Continuous improvement system.
    
    Workflow:
    1. Seal forecast with current θ
    2. Wait for real outcome
    3. Score forecast (compute loss)
    4. Update θ to minimize loss
    5. Repeat
    
    This is how the system learns from production forecasts.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        simulator: Callable[[ThetaParameters, Dict], SimulationOutput],
        outcome_fetcher: Callable[[UUID], RealWorldData],
    ):
        """
        Initialize learning loop.
        
        Args:
            session: Database session
            simulator: Function that runs simulation given θ and query
            outcome_fetcher: Function that fetches real outcomes
        """
        self.session = session
        self.simulator = simulator
        self.outcome_fetcher = outcome_fetcher
    
    async def seal_forecast(
        self,
        capability_id: UUID,
        query: Dict,
        theta: ThetaParameters,
        outcome_due_at: datetime,
        scoring_rule: str = "brier",
    ) -> UUID:
        """
        Seal a prospective forecast before outcome is known.
        
        Args:
            capability_id: Capability being forecasted
            query: Forecast query (e.g., "How will r/politics respond to X?")
            theta: Current best θ for this capability
            outcome_due_at: When real outcome will be available
            scoring_rule: Scoring method
            
        Returns:
            Forecast ID
        """
        # Run simulation with current θ
        simulation = self.simulator(theta, query)
        
        # Seal prediction
        forecast = SealedForecast(
            forecast_id=uuid4(),
            capability_id=capability_id,
            sealed_at=datetime.utcnow(),
            outcome_due_at=outcome_due_at,
            prediction_json={
                "outcome_probabilities": simulation.outcome_probabilities,
                "response_distribution": simulation.response_distribution.tolist(),
                "engagement_distribution": simulation.engagement_distribution.tolist(),
                "timing_distribution": simulation.timing_distribution.tolist(),
                "cascade_sizes": simulation.cascade_sizes,
                "reply_depths": simulation.reply_depths,
                "branching_factors": simulation.branching_factors,
                "toxicity_scores": simulation.toxicity_scores,
                "num_agents": simulation.num_agents,
                "num_interactions": simulation.num_interactions,
                "simulation_time_hours": simulation.simulation_time_hours,
            },
            scoring_rule=scoring_rule,
            model_version=theta.llm_model,
            code_sha="HEAD",  # TODO: Get actual git SHA
            data_cutoff=datetime.utcnow(),
            status="sealed",
        )
        
        self.session.add(forecast)
        await self.session.commit()
        
        return forecast.forecast_id
    
    async def score_forecast(
        self,
        forecast_id: UUID,
    ) -> float:
        """
        Score a completed forecast against real outcome.
        
        Args:
            forecast_id: Sealed forecast to score
            
        Returns:
            Loss value (lower is better)
        """
        # Fetch forecast
        stmt = select(SealedForecast).where(SealedForecast.forecast_id == forecast_id)
        result = await self.session.execute(stmt)
        forecast = result.scalar_one_or_none()
        
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")
        
        if forecast.status != "sealed":
            raise ValueError(f"Forecast {forecast_id} already scored or failed")
        
        # Fetch real outcome
        reality = self.outcome_fetcher(forecast_id)
        
        # Reconstruct simulation output
        pred = forecast.prediction_json
        simulation = SimulationOutput(
            outcome_probabilities=pred["outcome_probabilities"],
            response_distribution=pred["response_distribution"],
            engagement_distribution=pred["engagement_distribution"],
            timing_distribution=pred["timing_distribution"],
            cascade_sizes=pred["cascade_sizes"],
            reply_depths=pred["reply_depths"],
            branching_factors=pred["branching_factors"],
            toxicity_scores=pred["toxicity_scores"],
            num_agents=pred["num_agents"],
            num_interactions=pred["num_interactions"],
            simulation_time_hours=pred["simulation_time_hours"],
        )
        
        # Get capability type for appropriate loss weights
        stmt = select(CapabilityRegistry).where(
            CapabilityRegistry.capability_id == forecast.capability_id
        )
        result = await self.session.execute(stmt)
        capability = result.scalar_one_or_none()
        
        # Infer capability type from outcome
        capability_type = "forecasting"  # Default
        if "distribution" in capability.outcome.lower():
            capability_type = "population"
        elif "discourse" in capability.outcome.lower() or "conversation" in capability.outcome.lower():
            capability_type = "discourse"
        
        loss_fn = create_default_loss(capability_type)
        
        # Compute loss
        loss = loss_fn(simulation, reality)
        metrics = loss_fn.get_last_metrics()
        
        # Update forecast
        forecast.outcome_json = {
            "outcome_frequencies": reality.outcome_frequencies,
            "response_distribution": reality.response_distribution.tolist(),
            "engagement_distribution": reality.engagement_distribution.tolist(),
            "timing_distribution": reality.timing_distribution.tolist(),
            "cascade_sizes": reality.cascade_sizes,
            "reply_depths": reality.reply_depths,
            "branching_factors": reality.branching_factors,
            "toxicity_scores": reality.toxicity_scores,
            "num_observations": reality.num_observations,
            "time_window_hours": reality.time_window_hours,
        }
        forecast.score = loss
        forecast.scored_at = datetime.utcnow()
        forecast.status = "scored"
        
        await self.session.commit()
        
        return loss
    
    async def update_theta(
        self,
        capability_id: UUID,
        n_recent_forecasts: int = 10,
    ) -> ThetaParameters:
        """
        Update θ based on recent forecast performance.
        
        This is the core learning step: adjust parameters to minimize
        average loss on recent forecasts.
        
        Args:
            capability_id: Capability to optimize
            n_recent_forecasts: How many recent forecasts to optimize over
            
        Returns:
            New optimized θ*
        """
        # Fetch recent scored forecasts
        stmt = (
            select(SealedForecast)
            .where(
                SealedForecast.capability_id == capability_id,
                SealedForecast.status == "scored",
            )
            .order_by(SealedForecast.scored_at.desc())
            .limit(n_recent_forecasts)
        )
        result = await self.session.execute(stmt)
        forecasts = result.scalars().all()
        
        if len(forecasts) == 0:
            raise ValueError(f"No scored forecasts for capability {capability_id}")
        
        # Get current θ (from most recent forecast)
        # TODO: Store θ snapshot in forecast or capability registry
        current_theta = ThetaParameters()  # Placeholder
        
        # Define loss function that averages over recent forecasts
        def aggregate_loss(theta: ThetaParameters) -> float:
            losses = []
            for forecast in forecasts:
                # Reconstruct simulation and reality
                pred = forecast.prediction_json
                simulation = SimulationOutput(
                    outcome_probabilities=pred["outcome_probabilities"],
                    response_distribution=pred["response_distribution"],
                    engagement_distribution=pred["engagement_distribution"],
                    timing_distribution=pred["timing_distribution"],
                    cascade_sizes=pred["cascade_sizes"],
                    reply_depths=pred["reply_depths"],
                    branching_factors=pred["branching_factors"],
                    toxicity_scores=pred["toxicity_scores"],
                    num_agents=pred["num_agents"],
                    num_interactions=pred["num_interactions"],
                    simulation_time_hours=pred["simulation_time_hours"],
                )
                
                obs = forecast.outcome_json
                reality = RealWorldData(
                    outcome_frequencies=obs["outcome_frequencies"],
                    response_distribution=obs["response_distribution"],
                    engagement_distribution=obs["engagement_distribution"],
                    timing_distribution=obs["timing_distribution"],
                    cascade_sizes=obs["cascade_sizes"],
                    reply_depths=obs["reply_depths"],
                    branching_factors=obs["branching_factors"],
                    toxicity_scores=obs["toxicity_scores"],
                    num_observations=obs["num_observations"],
                    time_window_hours=obs["time_window_hours"],
                )
                
                # Re-simulate with new θ and score
                # NOTE: This is expensive - each loss evaluation runs a simulation
                # In practice, we'd cache simulations or use surrogate models
                new_simulation = self.simulator(theta, forecast.prediction_json)
                
                loss_fn = create_default_loss("forecasting")
                loss = loss_fn(new_simulation, reality)
                losses.append(loss)
            
            return sum(losses) / len(losses)
        
        # Optimize θ to minimize aggregate loss
        optimizer = ThetaOptimizer(
            loss_function=aggregate_loss,
            method="bayesian",  # Sample-efficient (simulations are expensive)
            n_iter=30,
        )
        
        theta_star = optimizer.optimize(
            initial_theta=current_theta,
            capability_key={"capability_id": str(capability_id)},
        )
        
        # Store optimization history
        # TODO: Save to backtest_results table
        
        return theta_star
    
    async def run_continuous_loop(
        self,
        capability_id: UUID,
        check_interval_hours: float = 1.0,
    ):
        """
        Run continuous learning loop.
        
        Periodically checks for due forecasts, scores them, and updates θ.
        
        Args:
            capability_id: Capability to monitor
            check_interval_hours: How often to check for due forecasts
        """
        while True:
            # Check for forecasts that are due
            now = datetime.utcnow()
            stmt = (
                select(SealedForecast)
                .where(
                    SealedForecast.capability_id == capability_id,
                    SealedForecast.status == "sealed",
                    SealedForecast.outcome_due_at <= now,
                )
            )
            result = await self.session.execute(stmt)
            due_forecasts = result.scalars().all()
            
            # Score each due forecast
            for forecast in due_forecasts:
                try:
                    loss = await self.score_forecast(forecast.forecast_id)
                    print(f"Scored forecast {forecast.forecast_id}: loss={loss:.4f}")
                except Exception as e:
                    print(f"Failed to score forecast {forecast.forecast_id}: {e}")
                    forecast.status = "failed"
                    await self.session.commit()
            
            # If we scored any forecasts, update θ
            if len(due_forecasts) > 0:
                try:
                    theta_star = await self.update_theta(capability_id)
                    print(f"Updated θ for capability {capability_id}")
                    # TODO: Store theta_star in capability registry
                except Exception as e:
                    print(f"Failed to update θ for capability {capability_id}: {e}")
            
            # Wait before next check
            await asyncio.sleep(check_interval_hours * 3600)


class DriftMonitor:
    """
    Monitors forecast performance over time and detects drift.
    
    If performance degrades, suspends capability and triggers revalidation.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        drift_threshold: float = 0.15,  # 15% increase in loss
        window_size: int = 20,  # Rolling window of forecasts
    ):
        """
        Initialize drift monitor.
        
        Args:
            session: Database session
            drift_threshold: Relative increase in loss to trigger suspension
            window_size: Number of recent forecasts to compare
        """
        self.session = session
        self.drift_threshold = drift_threshold
        self.window_size = window_size
    
    async def check_drift(self, capability_id: UUID) -> Dict[str, any]:
        """
        Check if capability performance has drifted.
        
        Args:
            capability_id: Capability to check
            
        Returns:
            Drift report with status and statistics
        """
        # Fetch recent scored forecasts
        stmt = (
            select(SealedForecast)
            .where(
                SealedForecast.capability_id == capability_id,
                SealedForecast.status == "scored",
            )
            .order_by(SealedForecast.scored_at.desc())
            .limit(self.window_size * 2)  # Get 2x window for comparison
        )
        result = await self.session.execute(stmt)
        forecasts = result.scalars().all()
        
        if len(forecasts) < self.window_size:
            return {
                "status": "insufficient_data",
                "n_forecasts": len(forecasts),
                "min_required": self.window_size,
            }
        
        # Split into recent and baseline windows
        recent_window = forecasts[:self.window_size]
        baseline_window = forecasts[self.window_size:self.window_size * 2]
        
        # Compute average loss in each window
        recent_loss = sum(f.score for f in recent_window) / len(recent_window)
        baseline_loss = sum(f.score for f in baseline_window) / len(baseline_window)
        
        # Compute relative change
        relative_change = (recent_loss - baseline_loss) / baseline_loss
        
        # Determine drift status
        if relative_change > self.drift_threshold:
            drift_status = "out_of_limits"
        elif relative_change > self.drift_threshold / 2:
            drift_status = "degrading"
        else:
            drift_status = "within_limits"
        
        return {
            "status": drift_status,
            "recent_loss": recent_loss,
            "baseline_loss": baseline_loss,
            "relative_change": relative_change,
            "threshold": self.drift_threshold,
            "n_recent": len(recent_window),
            "n_baseline": len(baseline_window),
        }
    
    async def suspend_if_drifted(self, capability_id: UUID) -> bool:
        """
        Check drift and suspend capability if out of limits.
        
        Args:
            capability_id: Capability to check
            
        Returns:
            True if suspended, False otherwise
        """
        drift_report = await self.check_drift(capability_id)
        
        if drift_report["status"] == "out_of_limits":
            # Update capability registry
            stmt = select(CapabilityRegistry).where(
                CapabilityRegistry.capability_id == capability_id
            )
            result = await self.session.execute(stmt)
            capability = result.scalar_one_or_none()
            
            if capability:
                capability.drift_status = "out_of_limits"
                capability.updated_at = datetime.utcnow()
                await self.session.commit()
                
                print(f"SUSPENDED capability {capability_id}: drift detected")
                print(f"  Recent loss: {drift_report['recent_loss']:.4f}")
                print(f"  Baseline loss: {drift_report['baseline_loss']:.4f}")
                print(f"  Relative change: {drift_report['relative_change']:.2%}")
                
                return True
        
        return False
