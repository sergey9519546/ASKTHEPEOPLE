"""
Multi-Objective Loss Function D(P_simulation, P_real_world)

Composes multiple fidelity metrics into a single optimization target.
This is the evaluator that determines whether θ is good or bad.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md + "Reality is the final evaluator"
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance, ks_2samp


@dataclass
class SimulationOutput:
    """Simulation predictions to be scored against reality."""
    
    # Probabilistic predictions
    outcome_probabilities: Dict[str, float]  # e.g., {"support": 0.62, "oppose": 0.38}
    
    # Distribution predictions
    response_distribution: np.ndarray  # Histogram of responses
    engagement_distribution: np.ndarray  # Histogram of engagement levels
    timing_distribution: np.ndarray  # Response time distribution
    
    # Social dynamics
    cascade_sizes: List[int]  # Reply chain lengths
    reply_depths: List[int]  # Max depth per thread
    branching_factors: List[float]  # Replies per comment
    toxicity_scores: List[float]  # Per-comment toxicity
    
    # Metadata
    num_agents: int
    num_interactions: int
    simulation_time_hours: float


@dataclass
class RealWorldData:
    """Ground truth observations from Reddit/Twitter/etc."""
    
    # Actual outcomes
    outcome_frequencies: Dict[str, float]  # Observed frequencies
    
    # Observed distributions
    response_distribution: np.ndarray
    engagement_distribution: np.ndarray
    timing_distribution: np.ndarray
    
    # Observed social dynamics
    cascade_sizes: List[int]
    reply_depths: List[int]
    branching_factors: List[float]
    toxicity_scores: List[float]
    
    # Metadata
    num_observations: int
    time_window_hours: float


@dataclass
class LossWeights:
    """
    Weights for multi-objective loss composition.
    
    These determine what we optimize for. Different capability keys
    may have different weights (e.g., stance prediction cares more about
    Brier score, while discourse simulation cares more about cascade fidelity).
    """
    
    # Tier A: Predictive validity (primary for forecasting)
    w_brier: float = 1.0  # Brier score (probability calibration)
    w_log_loss: float = 0.5  # Log loss (sharpness + calibration)
    w_calibration: float = 1.0  # Calibration error (over/under confidence)
    w_sharpness: float = 0.3  # Sharpness (confidence when correct)
    
    # Tier B: Distribution fidelity (primary for population modeling)
    w_tvd: float = 0.7  # Total variation distance
    w_jsd: float = 0.7  # Jensen-Shannon divergence
    w_wasserstein: float = 0.5  # Wasserstein (earth mover's) distance
    
    # Tier C: Social dynamics fidelity (primary for discourse simulation)
    w_cascade_ks: float = 0.4  # Cascade size distribution (KS test)
    w_depth_mae: float = 0.3  # Reply depth error
    w_branching_mae: float = 0.3  # Branching factor error
    w_toxicity_tvd: float = 0.2  # Toxicity distribution
    
    # Penalty terms
    w_complexity: float = 0.05  # Penalize unnecessary complexity (Occam's razor)
    w_cost: float = 0.01  # Penalize expensive models (economic constraint)


class MultiObjectiveLoss:
    """
    D(P_simulation, P_real_world): Multi-objective fidelity function.
    
    Composes metrics into a single scalar loss. Lower is better.
    """
    
    def __init__(self, weights: Optional[LossWeights] = None):
        """
        Initialize loss function.
        
        Args:
            weights: Relative weights for each metric (or use defaults)
        """
        self.weights = weights or LossWeights()
        
        # Track individual metric values for analysis
        self.last_metrics: Optional[Dict[str, float]] = None
    
    def __call__(
        self,
        simulation: SimulationOutput,
        reality: RealWorldData,
    ) -> float:
        """
        Compute total loss D(P_sim, P_real).
        
        Args:
            simulation: Simulation predictions
            reality: Ground truth observations
            
        Returns:
            Scalar loss (lower is better)
        """
        metrics = {}
        
        # Tier A: Predictive validity
        metrics["brier"] = self._brier_score(simulation.outcome_probabilities, reality.outcome_frequencies)
        metrics["log_loss"] = self._log_loss(simulation.outcome_probabilities, reality.outcome_frequencies)
        metrics["calibration_error"] = self._calibration_error(simulation.outcome_probabilities, reality.outcome_frequencies)
        metrics["sharpness"] = self._sharpness(simulation.outcome_probabilities)
        
        # Tier B: Distribution fidelity
        metrics["tvd_response"] = self._total_variation_distance(simulation.response_distribution, reality.response_distribution)
        metrics["jsd_response"] = self._jensen_shannon_divergence(simulation.response_distribution, reality.response_distribution)
        metrics["wasserstein_engagement"] = self._wasserstein_distance(simulation.engagement_distribution, reality.engagement_distribution)
        
        # Tier C: Social dynamics fidelity
        metrics["cascade_ks"] = self._cascade_ks_stat(simulation.cascade_sizes, reality.cascade_sizes)
        metrics["depth_mae"] = self._mean_absolute_error(simulation.reply_depths, reality.reply_depths)
        metrics["branching_mae"] = self._mean_absolute_error(simulation.branching_factors, reality.branching_factors)
        metrics["toxicity_tvd"] = self._total_variation_distance(
            self._to_histogram(simulation.toxicity_scores),
            self._to_histogram(reality.toxicity_scores)
        )
        
        # Penalty terms
        metrics["complexity_penalty"] = self._complexity_penalty(simulation.num_agents, simulation.num_interactions)
        metrics["cost_penalty"] = self._cost_penalty(simulation.simulation_time_hours)
        
        # Compose into single loss
        total_loss = (
            self.weights.w_brier * metrics["brier"] +
            self.weights.w_log_loss * metrics["log_loss"] +
            self.weights.w_calibration * metrics["calibration_error"] +
            self.weights.w_sharpness * (1.0 - metrics["sharpness"]) +  # Maximize sharpness = minimize (1 - sharpness)
            self.weights.w_tvd * metrics["tvd_response"] +
            self.weights.w_jsd * metrics["jsd_response"] +
            self.weights.w_wasserstein * metrics["wasserstein_engagement"] +
            self.weights.w_cascade_ks * metrics["cascade_ks"] +
            self.weights.w_depth_mae * metrics["depth_mae"] +
            self.weights.w_branching_mae * metrics["branching_mae"] +
            self.weights.w_toxicity_tvd * metrics["toxicity_tvd"] +
            self.weights.w_complexity * metrics["complexity_penalty"] +
            self.weights.w_cost * metrics["cost_penalty"]
        )
        
        # Store for inspection
        self.last_metrics = metrics
        self.last_metrics["total_loss"] = total_loss
        
        return total_loss
    
    # ========== Tier A: Predictive Validity ==========
    
    def _brier_score(self, predicted: Dict[str, float], observed: Dict[str, float]) -> float:
        """
        Brier score: mean squared error of probabilities.
        
        Range: [0, 1], lower is better.
        Perfect calibration = 0.
        """
        score = 0.0
        for outcome, p_pred in predicted.items():
            p_obs = observed.get(outcome, 0.0)
            score += (p_pred - p_obs) ** 2
        return score / len(predicted)
    
    def _log_loss(self, predicted: Dict[str, float], observed: Dict[str, float]) -> float:
        """
        Log loss (cross-entropy): penalizes confident wrong predictions.
        
        Range: [0, ∞], lower is better.
        """
        epsilon = 1e-15  # Avoid log(0)
        loss = 0.0
        for outcome, p_obs in observed.items():
            p_pred = predicted.get(outcome, epsilon)
            p_pred = np.clip(p_pred, epsilon, 1 - epsilon)
            if p_obs > 0:
                loss -= p_obs * np.log(p_pred)
        return loss
    
    def _calibration_error(self, predicted: Dict[str, float], observed: Dict[str, float]) -> float:
        """
        Expected Calibration Error (ECE): average gap between confidence and accuracy.
        
        Simplified version for outcome probabilities.
        Range: [0, 1], lower is better.
        """
        errors = []
        for outcome, p_pred in predicted.items():
            p_obs = observed.get(outcome, 0.0)
            errors.append(abs(p_pred - p_obs))
        return np.mean(errors) if errors else 0.0
    
    def _sharpness(self, predicted: Dict[str, float]) -> float:
        """
        Sharpness: how confident are predictions?
        
        High sharpness = confident (probabilities near 0 or 1).
        Low sharpness = uncertain (probabilities near 0.5).
        
        Range: [0, 1], higher is better (but only when also calibrated).
        """
        probs = list(predicted.values())
        # Measure distance from uniform distribution
        uniform = 1.0 / len(probs)
        sharpness = np.mean([(p - uniform) ** 2 for p in probs])
        return sharpness
    
    # ========== Tier B: Distribution Fidelity ==========
    
    def _total_variation_distance(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        Total Variation Distance: 0.5 * sum(|p_i - q_i|)
        
        Range: [0, 1], lower is better.
        TVD = 0 means identical distributions.
        """
        p = self._normalize(p)
        q = self._normalize(q)
        return 0.5 * np.sum(np.abs(p - q))
    
    def _jensen_shannon_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        Jensen-Shannon Divergence: symmetric KL divergence.
        
        Range: [0, 1], lower is better.
        JSD = 0 means identical distributions.
        """
        p = self._normalize(p)
        q = self._normalize(q)
        return jensenshannon(p, q) ** 2  # Square to get actual divergence
    
    def _wasserstein_distance(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        Wasserstein (Earth Mover's) Distance: minimum cost to transform p into q.
        
        Range: [0, ∞], lower is better.
        Sensitive to distance between bins (unlike TVD/JSD).
        """
        p = self._normalize(p)
        q = self._normalize(q)
        return wasserstein_distance(p, q)
    
    # ========== Tier C: Social Dynamics Fidelity ==========
    
    def _cascade_ks_stat(self, sim_cascades: List[int], real_cascades: List[int]) -> float:
        """
        Kolmogorov-Smirnov statistic: test if cascade distributions match.
        
        Range: [0, 1], lower is better.
        KS = 0 means identical distributions.
        """
        if len(sim_cascades) == 0 or len(real_cascades) == 0:
            return 1.0  # Maximum distance if one is empty
        
        ks_stat, _ = ks_2samp(sim_cascades, real_cascades)
        return ks_stat
    
    def _mean_absolute_error(self, sim_values: List[float], real_values: List[float]) -> float:
        """
        MAE: average absolute difference.
        
        Range: [0, ∞], lower is better.
        """
        if len(sim_values) == 0 or len(real_values) == 0:
            return float('inf')
        
        sim_mean = np.mean(sim_values)
        real_mean = np.mean(real_values)
        return abs(sim_mean - real_mean)
    
    # ========== Penalty Terms ==========
    
    def _complexity_penalty(self, num_agents: int, num_interactions: int) -> float:
        """
        Penalize unnecessary complexity (Occam's razor).
        
        Simpler models (fewer agents, fewer interactions) preferred if equal accuracy.
        """
        return np.log(1 + num_agents) + np.log(1 + num_interactions) / 1000.0
    
    def _cost_penalty(self, simulation_time_hours: float) -> float:
        """
        Penalize expensive simulations (economic constraint).
        
        Faster models preferred if equal accuracy.
        """
        return simulation_time_hours
    
    # ========== Utilities ==========
    
    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        """Normalize array to sum to 1."""
        arr = np.asarray(arr).astype(float)
        total = np.sum(arr)
        if total == 0:
            return np.ones_like(arr) / len(arr)
        return arr / total
    
    def _to_histogram(self, values: List[float], bins: int = 10) -> np.ndarray:
        """Convert values to histogram."""
        if len(values) == 0:
            return np.zeros(bins)
        hist, _ = np.histogram(values, bins=bins, density=True)
        return hist
    
    def get_last_metrics(self) -> Optional[Dict[str, float]]:
        """Return individual metric values from last call."""
        return self.last_metrics


def create_default_loss(capability_type: str) -> MultiObjectiveLoss:
    """
    Create loss function with default weights for capability type.
    
    Args:
        capability_type: "forecasting", "population", or "discourse"
        
    Returns:
        Loss function with appropriate weights
    """
    if capability_type == "forecasting":
        # Predictive validity is primary
        weights = LossWeights(
            w_brier=2.0,
            w_log_loss=1.5,
            w_calibration=2.0,
            w_sharpness=0.5,
            w_tvd=0.3,
            w_jsd=0.3,
            w_wasserstein=0.2,
            w_cascade_ks=0.1,
            w_depth_mae=0.1,
            w_branching_mae=0.1,
            w_toxicity_tvd=0.05,
        )
    elif capability_type == "population":
        # Distribution fidelity is primary
        weights = LossWeights(
            w_brier=0.5,
            w_log_loss=0.3,
            w_calibration=0.5,
            w_sharpness=0.2,
            w_tvd=2.0,
            w_jsd=2.0,
            w_wasserstein=1.5,
            w_cascade_ks=0.3,
            w_depth_mae=0.2,
            w_branching_mae=0.2,
            w_toxicity_tvd=0.3,
        )
    elif capability_type == "discourse":
        # Social dynamics fidelity is primary
        weights = LossWeights(
            w_brier=0.3,
            w_log_loss=0.2,
            w_calibration=0.3,
            w_sharpness=0.1,
            w_tvd=0.5,
            w_jsd=0.5,
            w_wasserstein=0.3,
            w_cascade_ks=2.0,
            w_depth_mae=1.5,
            w_branching_mae=1.5,
            w_toxicity_tvd=1.0,
        )
    else:
        # Balanced (default)
        weights = LossWeights()
    
    return MultiObjectiveLoss(weights)
