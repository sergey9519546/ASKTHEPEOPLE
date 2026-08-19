"""
Baseline Models Library

Simple models that establish performance floor.
LLM simulation must beat these to be useful.

Authority: "Reality is the final evaluator"
"""

from typing import Dict, List, Optional
import numpy as np
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer

from app.optimization.multi_objective_loss import SimulationOutput, RealWorldData


class BaselineModel:
    """Base class for baseline models."""
    
    def predict(self, query: Dict, historical_data: List[RealWorldData]) -> SimulationOutput:
        """
        Generate prediction.
        
        Args:
            query: Forecast query
            historical_data: Past observations for training
            
        Returns:
            Prediction as SimulationOutput
        """
        raise NotImplementedError


class NaiveBaseline(BaselineModel):
    """
    Naive baseline: always predict most common class.
    
    This is the MINIMUM bar. Any model worse than this is useless.
    """
    
    def predict(self, query: Dict, historical_data: List[RealWorldData]) -> SimulationOutput:
        """Predict most frequent outcome from historical data."""
        
        if not historical_data:
            # Default uniform
            outcome_probs = {"support": 0.33, "neutral": 0.33, "oppose": 0.34}
        else:
            # Aggregate historical frequencies
            total_counts = Counter()
            for data in historical_data:
                for outcome, freq in data.outcome_frequencies.items():
                    total_counts[outcome] += freq * data.num_observations
            
            total = sum(total_counts.values())
            outcome_probs = {k: v / total for k, v in total_counts.items()}
        
        # Use historical mean distributions
        response_dist = self._aggregate_distribution([d.response_distribution for d in historical_data])
        engagement_dist = self._aggregate_distribution([d.engagement_distribution for d in historical_data])
        timing_dist = self._aggregate_distribution([d.timing_distribution for d in historical_data])
        
        # Use historical mean social dynamics
        cascade_sizes = self._aggregate_list([d.cascade_sizes for d in historical_data])
        reply_depths = self._aggregate_list([d.reply_depths for d in historical_data])
        branching_factors = self._aggregate_list([d.branching_factors for d in historical_data])
        toxicity_scores = self._aggregate_list([d.toxicity_scores for d in historical_data])
        
        return SimulationOutput(
            outcome_probabilities=outcome_probs,
            response_distribution=response_dist,
            engagement_distribution=engagement_dist,
            timing_distribution=timing_dist,
            cascade_sizes=cascade_sizes,
            reply_depths=reply_depths,
            branching_factors=branching_factors,
            toxicity_scores=toxicity_scores,
            num_agents=100,
            num_interactions=sum(d.num_observations for d in historical_data) // len(historical_data),
            simulation_time_hours=historical_data[0].time_window_hours if historical_data else 168.0,
        )
    
    def _aggregate_distribution(self, distributions: List[np.ndarray]) -> np.ndarray:
        """Average distributions."""
        if not distributions:
            return np.ones(10) / 10
        return np.mean(distributions, axis=0)
    
    def _aggregate_list(self, lists: List[List]) -> List:
        """Aggregate lists (take mean)."""
        if not lists or not any(lists):
            return [1.0]
        flat = [item for sublist in lists for item in sublist]
        return flat[:10] if len(flat) >= 10 else flat


class PersistenceBaseline(BaselineModel):
    """
    Persistence baseline: predict last observed state.
    
    "Tomorrow will look like today."
    """
    
    def predict(self, query: Dict, historical_data: List[RealWorldData]) -> SimulationOutput:
        """Predict last observation carries forward."""
        
        if not historical_data:
            # Fallback to naive
            return NaiveBaseline().predict(query, historical_data)
        
        # Use most recent observation
        last_obs = historical_data[-1]
        
        return SimulationOutput(
            outcome_probabilities=last_obs.outcome_frequencies,
            response_distribution=last_obs.response_distribution,
            engagement_distribution=last_obs.engagement_distribution,
            timing_distribution=last_obs.timing_distribution,
            cascade_sizes=last_obs.cascade_sizes,
            reply_depths=last_obs.reply_depths,
            branching_factors=last_obs.branching_factors,
            toxicity_scores=last_obs.toxicity_scores,
            num_agents=100,
            num_interactions=last_obs.num_observations,
            simulation_time_hours=last_obs.time_window_hours,
        )


class LinearTrendBaseline(BaselineModel):
    """
    Linear trend baseline: extrapolate recent trend.
    
    "The trend will continue."
    """
    
    def predict(self, query: Dict, historical_data: List[RealWorldData]) -> SimulationOutput:
        """Fit linear trend and extrapolate."""
        
        if len(historical_data) < 2:
            # Need at least 2 points for trend
            return PersistenceBaseline().predict(query, historical_data)
        
        # Fit linear trend to outcome frequencies
        support_trend = [d.outcome_frequencies.get("support", 0.33) for d in historical_data]
        neutral_trend = [d.outcome_frequencies.get("neutral", 0.33) for d in historical_data]
        oppose_trend = [d.outcome_frequencies.get("oppose", 0.34) for d in historical_data]
        
        # Simple linear extrapolation (last 2 points)
        support_pred = 2 * support_trend[-1] - support_trend[-2]
        neutral_pred = 2 * neutral_trend[-1] - neutral_trend[-2]
        oppose_pred = 2 * oppose_trend[-1] - oppose_trend[-2]
        
        # Clip to [0, 1] and renormalize
        support_pred = max(0, min(1, support_pred))
        neutral_pred = max(0, min(1, neutral_pred))
        oppose_pred = max(0, min(1, oppose_pred))
        
        total = support_pred + neutral_pred + oppose_pred
        outcome_probs = {
            "support": support_pred / total,
            "neutral": neutral_pred / total,
            "oppose": oppose_pred / total,
        }
        
        # Use last observation for distributions
        last_obs = historical_data[-1]
        
        return SimulationOutput(
            outcome_probabilities=outcome_probs,
            response_distribution=last_obs.response_distribution,
            engagement_distribution=last_obs.engagement_distribution,
            timing_distribution=last_obs.timing_distribution,
            cascade_sizes=last_obs.cascade_sizes,
            reply_depths=last_obs.reply_depths,
            branching_factors=last_obs.branching_factors,
            toxicity_scores=last_obs.toxicity_scores,
            num_agents=100,
            num_interactions=last_obs.num_observations,
            simulation_time_hours=last_obs.time_window_hours,
        )


class SimpleClassifierBaseline(BaselineModel):
    """
    Simple text classifier baseline: logistic regression on TF-IDF features.
    
    This often outperforms LLM agents on simple classification tasks.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
        self.classifier = LogisticRegression(max_iter=1000)
        self.is_trained = False
    
    def train(self, texts: List[str], labels: List[str]):
        """
        Train classifier on historical data.
        
        Args:
            texts: Comment texts
            labels: Outcome labels ("support", "neutral", "oppose")
        """
        if len(texts) == 0:
            return
        
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self.is_trained = True
    
    def predict(self, query: Dict, historical_data: List[RealWorldData]) -> SimulationOutput:
        """
        Predict using trained classifier.
        
        NOTE: This requires storing comment texts in historical_data,
        which we don't currently do. For now, fallback to naive.
        """
        if not self.is_trained:
            # Fallback
            return NaiveBaseline().predict(query, historical_data)
        
        # TODO: Extract texts from query context and classify
        # For now, use historical average
        return NaiveBaseline().predict(query, historical_data)


class BaselineEvaluator:
    """
    Evaluate all baselines and return performance.
    
    This establishes the performance floor that LLM simulation must beat.
    """
    
    def __init__(self):
        self.baselines = {
            "naive": NaiveBaseline(),
            "persistence": PersistenceBaseline(),
            "linear_trend": LinearTrendBaseline(),
            "simple_classifier": SimpleClassifierBaseline(),
        }
    
    def evaluate(
        self,
        query: Dict,
        historical_data: List[RealWorldData],
        ground_truth: RealWorldData,
        loss_function,
    ) -> Dict[str, float]:
        """
        Evaluate all baselines on a single forecast.
        
        Args:
            query: Forecast query
            historical_data: Past observations (training data)
            ground_truth: Real outcome
            loss_function: MultiObjectiveLoss instance
            
        Returns:
            Dict mapping baseline name to loss
        """
        results = {}
        
        for name, baseline in self.baselines.items():
            try:
                prediction = baseline.predict(query, historical_data)
                loss = loss_function(prediction, ground_truth)
                results[name] = loss
            except Exception as e:
                print(f"Baseline {name} failed: {e}")
                results[name] = float('inf')
        
        return results
    
    def get_best_baseline(
        self,
        query: Dict,
        historical_data: List[RealWorldData],
        ground_truth: RealWorldData,
        loss_function,
    ) -> tuple:
        """
        Get best-performing baseline.
        
        Returns:
            (name, loss) tuple
        """
        results = self.evaluate(query, historical_data, ground_truth, loss_function)
        best_name = min(results, key=results.get)
        return best_name, results[best_name]


def compare_to_baselines(
    simulation_loss: float,
    baseline_results: Dict[str, float],
) -> Dict:
    """
    Compare LLM simulation to baselines.
    
    Args:
        simulation_loss: Loss from LLM simulation
        baseline_results: Dict of baseline name -> loss
        
    Returns:
        Comparison report
    """
    best_baseline_name = min(baseline_results, key=baseline_results.get)
    best_baseline_loss = baseline_results[best_baseline_name]
    
    improvement = (best_baseline_loss - simulation_loss) / best_baseline_loss
    
    beats_all = all(simulation_loss < loss for loss in baseline_results.values())
    beats_best = simulation_loss < best_baseline_loss
    
    return {
        "simulation_loss": simulation_loss,
        "best_baseline_name": best_baseline_name,
        "best_baseline_loss": best_baseline_loss,
        "improvement_over_best": improvement,
        "beats_all_baselines": beats_all,
        "beats_best_baseline": beats_best,
        "all_baseline_results": baseline_results,
        "verdict": "PASS" if beats_best else "FAIL",
    }
