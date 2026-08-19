"""
Theta Optimizer: Core parameter search engine for predictive simulation.

This is the heart of the system. Everything else (capability registry, evidence badges,
claim gating) tracks OUTCOMES of this optimizer.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md + θ* = argmin_θ D(P_sim, P_real)
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from uuid import UUID, uuid4

import numpy as np
from scipy.optimize import differential_evolution, minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern


@dataclass
class ThetaParameters:
    """
    Complete parameter vector θ for simulation.
    
    This includes EVERYTHING that affects simulation output:
    - Population construction
    - Agent behavior
    - Network dynamics
    - LLM parameters
    - Calibration
    """
    
    # Population
    population_size: int = 100
    persona_temperature: float = 0.8
    persona_diversity_weight: float = 0.5
    importance_weights: Optional[np.ndarray] = None
    
    # Agent behavioral policy (statistical, not LLM)
    action_base_rate: Dict[str, float] = None  # e.g., {"comment": 0.15, "upvote": 0.45}
    engagement_decay: float = 0.92  # Temporal decay of interest
    stance_shift_rate: float = 0.08  # How often agents change opinion
    
    # Network dynamics
    homophily_strength: float = 0.65  # Tendency to interact with similar agents
    network_density: float = 0.12  # Edge probability
    preferential_attachment_alpha: float = 1.5  # Rich-get-richer exponent
    
    # Exposure mechanism (feed algorithm)
    exposure_recency_weight: float = 0.7
    exposure_popularity_weight: float = 0.3
    exposure_personalization_weight: float = 0.4
    
    # LLM parameters (semantic layer only)
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    reasoning_depth: int = 2  # Chain-of-thought steps
    
    # Temporal dynamics
    simulation_steps: int = 100
    time_step_hours: float = 1.0
    
    # Calibration (post-simulation correction)
    calibration_temperature: float = 1.0  # Platt scaling temperature
    calibration_bias: float = 0.0  # Calibration intercept
    
    # Ensemble
    ensemble_size: int = 5  # Monte Carlo runs
    ensemble_aggregation: str = "mean"  # "mean", "median", "mixture"
    
    def to_vector(self) -> np.ndarray:
        """Convert to flat numpy array for optimization."""
        return np.array([
            self.population_size,
            self.persona_temperature,
            self.persona_diversity_weight,
            self.action_base_rate.get("comment", 0.15) if self.action_base_rate else 0.15,
            self.action_base_rate.get("upvote", 0.45) if self.action_base_rate else 0.45,
            self.engagement_decay,
            self.stance_shift_rate,
            self.homophily_strength,
            self.network_density,
            self.preferential_attachment_alpha,
            self.exposure_recency_weight,
            self.exposure_popularity_weight,
            self.exposure_personalization_weight,
            self.llm_temperature,
            self.llm_top_p,
            float(self.reasoning_depth),
            float(self.simulation_steps),
            self.time_step_hours,
            self.calibration_temperature,
            self.calibration_bias,
            float(self.ensemble_size),
        ])
    
    @classmethod
    def from_vector(cls, vec: np.ndarray, base_params: Optional["ThetaParameters"] = None):
        """Construct from flat vector."""
        base = base_params or cls()
        return cls(
            population_size=int(vec[0]),
            persona_temperature=float(vec[1]),
            persona_diversity_weight=float(vec[2]),
            action_base_rate={"comment": float(vec[3]), "upvote": float(vec[4])},
            engagement_decay=float(vec[5]),
            stance_shift_rate=float(vec[6]),
            homophily_strength=float(vec[7]),
            network_density=float(vec[8]),
            preferential_attachment_alpha=float(vec[9]),
            exposure_recency_weight=float(vec[10]),
            exposure_popularity_weight=float(vec[11]),
            exposure_personalization_weight=float(vec[12]),
            llm_temperature=float(vec[13]),
            llm_top_p=float(vec[14]),
            reasoning_depth=int(vec[15]),
            simulation_steps=int(vec[16]),
            time_step_hours=float(vec[17]),
            calibration_temperature=float(vec[18]),
            calibration_bias=float(vec[19]),
            ensemble_size=int(vec[20]),
            llm_model=base.llm_model,
            importance_weights=base.importance_weights,
            ensemble_aggregation=base.ensemble_aggregation,
        )
    
    def get_bounds(self) -> List[tuple]:
        """Get optimization bounds for each parameter."""
        return [
            (10, 1000),      # population_size
            (0.3, 1.5),      # persona_temperature
            (0.0, 1.0),      # persona_diversity_weight
            (0.01, 0.5),     # action_base_rate["comment"]
            (0.1, 0.8),      # action_base_rate["upvote"]
            (0.7, 0.99),     # engagement_decay
            (0.01, 0.3),     # stance_shift_rate
            (0.3, 0.9),      # homophily_strength
            (0.05, 0.3),     # network_density
            (0.5, 3.0),      # preferential_attachment_alpha
            (0.3, 1.0),      # exposure_recency_weight
            (0.0, 0.7),      # exposure_popularity_weight
            (0.0, 0.7),      # exposure_personalization_weight
            (0.3, 1.5),      # llm_temperature
            (0.7, 1.0),      # llm_top_p
            (1, 5),          # reasoning_depth
            (50, 500),       # simulation_steps
            (0.5, 4.0),      # time_step_hours
            (0.5, 2.0),      # calibration_temperature
            (-0.5, 0.5),     # calibration_bias
            (3, 20),         # ensemble_size
        ]


class ThetaOptimizer:
    """
    Searches θ space to minimize D(P_simulation, P_real_world).
    
    Methods:
    - Differential evolution (global search)
    - Bayesian optimization (sample-efficient)
    - Gradient descent (local refinement, when gradients available)
    - Evolutionary strategies (parallelizable)
    """
    
    def __init__(
        self,
        loss_function: Callable[[ThetaParameters], float],
        method: str = "bayesian",
        n_iter: int = 50,
        n_parallel: int = 4,
    ):
        """
        Initialize optimizer.
        
        Args:
            loss_function: D(P_sim, P_real) - lower is better
            method: "differential_evolution", "bayesian", "gradient", "evolutionary"
            n_iter: Number of optimization iterations
            n_parallel: Parallel evaluations (for evolutionary/differential)
        """
        self.loss_function = loss_function
        self.method = method
        self.n_iter = n_iter
        self.n_parallel = n_parallel
        
        # History of evaluations
        self.history: List[Dict] = []
        
        # Bayesian optimization state
        self.gp: Optional[GaussianProcessRegressor] = None
        if method == "bayesian":
            kernel = Matern(nu=2.5)
            self.gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True)
    
    def optimize(
        self,
        initial_theta: ThetaParameters,
        capability_key: Optional[Dict] = None,
    ) -> ThetaParameters:
        """
        Find θ* that minimizes loss.
        
        Args:
            initial_theta: Starting point
            capability_key: Capability being optimized (for logging)
            
        Returns:
            Optimized θ*
        """
        bounds = initial_theta.get_bounds()
        x0 = initial_theta.to_vector()
        
        if self.method == "differential_evolution":
            result = differential_evolution(
                func=self._objective,
                bounds=bounds,
                args=(initial_theta,),
                maxiter=self.n_iter,
                workers=self.n_parallel,
                updating="deferred",
                seed=42,
            )
            theta_star = ThetaParameters.from_vector(result.x, initial_theta)
            
        elif self.method == "bayesian":
            theta_star = self._bayesian_optimize(initial_theta, bounds)
            
        elif self.method == "gradient":
            # Requires differentiable loss (rare for simulation)
            result = minimize(
                fun=self._objective,
                x0=x0,
                args=(initial_theta,),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": self.n_iter},
            )
            theta_star = ThetaParameters.from_vector(result.x, initial_theta)
            
        elif self.method == "evolutionary":
            theta_star = self._evolutionary_optimize(initial_theta, bounds)
            
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        # Log final result
        final_loss = self.loss_function(theta_star)
        self.history.append({
            "iteration": len(self.history),
            "theta": theta_star.to_vector().tolist(),
            "loss": final_loss,
            "is_final": True,
            "capability_key": capability_key,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return theta_star
    
    def _objective(self, x: np.ndarray, base_params: ThetaParameters) -> float:
        """Objective function for scipy optimizers."""
        theta = ThetaParameters.from_vector(x, base_params)
        loss = self.loss_function(theta)
        
        # Log evaluation
        self.history.append({
            "iteration": len(self.history),
            "theta": x.tolist(),
            "loss": loss,
            "is_final": False,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return loss
    
    def _bayesian_optimize(
        self,
        initial_theta: ThetaParameters,
        bounds: List[tuple],
    ) -> ThetaParameters:
        """
        Bayesian optimization using Gaussian process surrogate.
        
        Sample-efficient: good when each simulation is expensive.
        """
        X_observed = []
        y_observed = []
        
        # Initial random samples
        n_initial = min(10, self.n_iter // 5)
        for _ in range(n_initial):
            x = np.array([np.random.uniform(low, high) for low, high in bounds])
            theta = ThetaParameters.from_vector(x, initial_theta)
            loss = self.loss_function(theta)
            X_observed.append(x)
            y_observed.append(loss)
            
            self.history.append({
                "iteration": len(self.history),
                "theta": x.tolist(),
                "loss": loss,
                "acquisition": "random",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Bayesian optimization loop
        for i in range(n_initial, self.n_iter):
            # Fit GP to observed data
            X_arr = np.array(X_observed)
            y_arr = np.array(y_observed).reshape(-1, 1)
            self.gp.fit(X_arr, y_arr)
            
            # Find next point via expected improvement
            x_next = self._acquisition_ei(bounds, X_arr, y_arr)
            
            # Evaluate
            theta = ThetaParameters.from_vector(x_next, initial_theta)
            loss = self.loss_function(theta)
            X_observed.append(x_next)
            y_observed.append(loss)
            
            self.history.append({
                "iteration": len(self.history),
                "theta": x_next.tolist(),
                "loss": loss,
                "acquisition": "expected_improvement",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Return best observed
        best_idx = np.argmin(y_observed)
        return ThetaParameters.from_vector(X_observed[best_idx], initial_theta)
    
    def _acquisition_ei(
        self,
        bounds: List[tuple],
        X_observed: np.ndarray,
        y_observed: np.ndarray,
    ) -> np.ndarray:
        """
        Expected improvement acquisition function.
        
        Balances exploration (uncertainty) and exploitation (mean).
        """
        from scipy.stats import norm
        
        def ei(x):
            x = x.reshape(1, -1)
            mu, sigma = self.gp.predict(x, return_std=True)
            mu = mu[0]
            sigma = sigma[0]
            
            y_best = np.min(y_observed)
            
            if sigma == 0:
                return 0
            
            z = (y_best - mu) / sigma
            ei_value = (y_best - mu) * norm.cdf(z) + sigma * norm.pdf(z)
            return -ei_value  # Negative because we minimize
        
        # Optimize acquisition function
        result = differential_evolution(
            func=ei,
            bounds=bounds,
            maxiter=20,
            seed=42,
        )
        
        return result.x
    
    def _evolutionary_optimize(
        self,
        initial_theta: ThetaParameters,
        bounds: List[tuple],
    ) -> ThetaParameters:
        """
        CMA-ES or simple (μ, λ) evolution strategy.
        
        Parallelizable and gradient-free.
        """
        # Simple (μ+λ) ES implementation
        mu = 10  # Parents
        lambda_ = 40  # Offspring
        
        # Initialize population around initial_theta
        x0 = initial_theta.to_vector()
        population = [x0]
        for _ in range(mu - 1):
            x = x0 + np.random.randn(len(x0)) * 0.1
            x = np.clip(x, [b[0] for b in bounds], [b[1] for b in bounds])
            population.append(x)
        
        for generation in range(self.n_iter // lambda_):
            # Evaluate population
            fitness = []
            for x in population:
                theta = ThetaParameters.from_vector(x, initial_theta)
                loss = self.loss_function(theta)
                fitness.append(loss)
                
                self.history.append({
                    "iteration": len(self.history),
                    "theta": x.tolist(),
                    "loss": loss,
                    "generation": generation,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            # Select best mu
            indices = np.argsort(fitness)[:mu]
            parents = [population[i] for i in indices]
            
            # Generate offspring
            offspring = []
            for _ in range(lambda_):
                # Recombination (mean of two random parents)
                p1, p2 = np.random.choice(len(parents), 2, replace=False)
                child = (parents[p1] + parents[p2]) / 2
                
                # Mutation
                child += np.random.randn(len(child)) * 0.05
                child = np.clip(child, [b[0] for b in bounds], [b[1] for b in bounds])
                
                offspring.append(child)
            
            # Next generation
            population = parents + offspring
        
        # Return best
        best_idx = np.argmin([self.loss_function(ThetaParameters.from_vector(x, initial_theta)) for x in parents])
        return ThetaParameters.from_vector(parents[best_idx], initial_theta)
    
    def get_history(self) -> List[Dict]:
        """Return optimization history."""
        return self.history
    
    def save_history(self, filepath: str):
        """Save optimization history to JSON."""
        with open(filepath, "w") as f:
            json.dump(self.history, f, indent=2)
