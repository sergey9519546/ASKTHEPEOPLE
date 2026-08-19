"""
Hybrid Simulator: Statistical Behavioral Policy + LLM Semantic Layer

This is the actual simulation engine that produces predictions from θ.

Authority: PREDICTIVE_SIMULATION_ROADMAP.md Phase 3.3 + "Reality is the final evaluator"

Architecture:
    REAL OBSERVED PLATFORM STATE
            ↓
    POPULATION / COMMUNITY ESTIMATION
            ↓
    EXPOSURE + RECOMMENDER MODEL
            ↓
    NETWORK + TEMPORAL DYNAMICS
            ↓
    BEHAVIORAL ACTION POLICY (statistical, not LLM)
            ↓
    LLM SEMANTIC REASONING (text generation only)
            ↓
    MULTI-AGENT INTERACTION
            ↓
    RAW SIMULATION DISTRIBUTION
            ↓
    CALIBRATION MODEL
            ↓
    FINAL PREDICTIVE DISTRIBUTION
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict

from app.optimization.theta_optimizer import ThetaParameters
from app.optimization.multi_objective_loss import SimulationOutput


@dataclass
class Agent:
    """
    Computational behavioral model (not a "persona" in the old sense).
    
    Agents are learned parameters that approximate real population heterogeneity.
    """
    agent_id: int
    
    # Behavioral parameters (statistical)
    engagement_level: float  # 0-1, how active
    stance: float  # -1 to 1, position on issue
    susceptibility: float  # 0-1, likelihood to change stance
    activity_history: List[str]  # Past actions
    
    # Network position
    neighbors: List[int]  # Connected agent IDs
    centrality: float  # Network importance
    
    # Temporal state
    last_active: float  # Simulation time
    interest_decay: float  # Current interest level
    
    # LLM only generates text, not decisions
    generated_text: Optional[str] = None


@dataclass
class SimulationState:
    """Complete simulation state at time t."""
    agents: Dict[int, Agent]
    network: np.ndarray  # Adjacency matrix
    content_feed: List[Dict]  # Exposed content
    interaction_history: List[Dict]  # All interactions
    current_time: float  # Simulation hours


class HybridSimulator:
    """
    Hybrid statistical-LLM simulator.
    
    Key insight: LLM is ONE COMPONENT, not the whole system.
    Behavioral policy, network dynamics, exposure mechanisms are statistical.
    LLM only handles semantic reasoning and text generation.
    """
    
    def __init__(self, theta: ThetaParameters):
        """
        Initialize simulator with parameters θ.
        
        Args:
            theta: Complete parameter vector
        """
        self.theta = theta
        self.rng = np.random.default_rng(seed=42)
    
    def simulate(self, query: Dict) -> SimulationOutput:
        """
        Run simulation and return predictions.
        
        Args:
            query: Forecast query with context
                {
                    "platform": "reddit",
                    "community": "r/politics",
                    "scenario": "How will community respond to policy X?",
                    "initial_state": {...},  # Real observed state
                    "forecast_window_hours": 336  # 2 weeks
                }
        
        Returns:
            Simulation output with probabilistic predictions
        """
        # 1. Population estimation
        agents = self._generate_population(
            size=self.theta.population_size,
            reference_distribution=query.get("initial_state", {}),
        )
        
        # 2. Network construction
        network = self._construct_network(agents)
        
        # 3. Initialize simulation state
        state = SimulationState(
            agents={a.agent_id: a for a in agents},
            network=network,
            content_feed=[],
            interaction_history=[],
            current_time=0.0,
        )
        
        # 4. Run time-stepped simulation
        num_steps = self.theta.simulation_steps
        time_step = self.theta.time_step_hours
        
        for step in range(num_steps):
            state = self._simulation_step(state, query)
            state.current_time += time_step
        
        # 5. Aggregate results
        outcomes = self._aggregate_outcomes(state)
        
        # 6. Apply calibration
        calibrated_outcomes = self._apply_calibration(outcomes)
        
        # 7. Package as SimulationOutput
        return self._to_simulation_output(calibrated_outcomes, state)
    
    def _generate_population(
        self,
        size: int,
        reference_distribution: Dict,
    ) -> List[Agent]:
        """
        Generate population with importance weighting.
        
        NOT uniform random personas. Uses reference distribution to match
        real population characteristics.
        """
        agents = []
        
        # Extract reference statistics (if available)
        ref_engagement_mean = reference_distribution.get("engagement_mean", 0.3)
        ref_engagement_std = reference_distribution.get("engagement_std", 0.15)
        ref_stance_distribution = reference_distribution.get("stance_distribution", [0.4, 0.3, 0.3])  # [oppose, neutral, support]
        
        for i in range(size):
            # Sample engagement level (log-normal, most users inactive)
            engagement = self.rng.lognormal(
                mean=np.log(ref_engagement_mean),
                sigma=ref_engagement_std,
            )
            engagement = np.clip(engagement, 0.0, 1.0)
            
            # Sample stance from reference distribution
            stance_category = self.rng.choice(
                ["oppose", "neutral", "support"],
                p=ref_stance_distribution,
            )
            if stance_category == "oppose":
                stance = self.rng.uniform(-1.0, -0.3)
            elif stance_category == "neutral":
                stance = self.rng.uniform(-0.3, 0.3)
            else:
                stance = self.rng.uniform(0.3, 1.0)
            
            # Sample other behavioral parameters
            susceptibility = self.rng.beta(2, 5)  # Most people less susceptible
            
            agents.append(Agent(
                agent_id=i,
                engagement_level=engagement,
                stance=stance,
                susceptibility=susceptibility,
                activity_history=[],
                neighbors=[],
                centrality=0.0,
                last_active=0.0,
                interest_decay=1.0,
            ))
        
        return agents
    
    def _construct_network(self, agents: List[Agent]) -> np.ndarray:
        """
        Construct social network with homophily and preferential attachment.
        
        Network dynamics matter MORE than agent dialogue for final outcomes.
        """
        n = len(agents)
        network = np.zeros((n, n), dtype=bool)
        
        # Preferential attachment + homophily
        degrees = np.zeros(n)
        
        for i in range(n):
            # Number of edges for this agent
            num_edges = self.rng.poisson(
                lam=self.theta.network_density * n
            )
            num_edges = min(num_edges, n - 1)
            
            if num_edges == 0:
                continue
            
            # Preferential attachment probabilities
            pa_probs = (degrees + 1) ** self.theta.preferential_attachment_alpha
            pa_probs[i] = 0  # No self-loops
            pa_probs = pa_probs / pa_probs.sum()
            
            # Homophily adjustment (more likely to connect to similar agents)
            stance_diff = np.array([
                abs(agents[i].stance - agents[j].stance)
                for j in range(n)
            ])
            homophily_weight = np.exp(-self.theta.homophily_strength * stance_diff)
            homophily_weight[i] = 0
            
            # Combined probability
            probs = pa_probs * homophily_weight
            probs = probs / probs.sum()
            
            # Sample neighbors
            neighbors = self.rng.choice(
                n,
                size=num_edges,
                replace=False,
                p=probs,
            )
            
            for j in neighbors:
                network[i, j] = True
                network[j, i] = True  # Undirected
                degrees[i] += 1
                degrees[j] += 1
                agents[i].neighbors.append(j)
                agents[j].neighbors.append(i)
        
        # Compute centrality (PageRank approximation)
        if degrees.sum() > 0:
            centralities = degrees / degrees.sum()
            for i, agent in enumerate(agents):
                agent.centrality = centralities[i]
        
        return network
    
    def _simulation_step(
        self,
        state: SimulationState,
        query: Dict,
    ) -> SimulationState:
        """
        Single time step of simulation.
        
        Key: Action selection is STATISTICAL, not LLM-based.
        LLM only generates text content AFTER action is selected.
        """
        # 1. Decay interest over time
        for agent in state.agents.values():
            agent.interest_decay *= self.theta.engagement_decay
        
        # 2. Exposure mechanism (who sees what)
        exposed_agents = self._compute_exposure(state)
        
        # 3. Action selection (statistical behavioral policy)
        for agent_id in exposed_agents:
            agent = state.agents[agent_id]
            
            # Decide action (comment, upvote, ignore)
            action = self._select_action(agent, state)
            
            if action == "ignore":
                continue
            
            # 4. LLM text generation (ONLY if action is comment)
            if action == "comment":
                # LLM generates semantic content
                text = self._generate_text_llm(agent, state, query)
                agent.generated_text = text
                
                # Record interaction
                state.interaction_history.append({
                    "agent_id": agent_id,
                    "action": "comment",
                    "text": text,
                    "stance": agent.stance,
                    "time": state.current_time,
                })
            
            elif action == "upvote":
                # No LLM needed for upvote
                state.interaction_history.append({
                    "agent_id": agent_id,
                    "action": "upvote",
                    "time": state.current_time,
                })
            
            # 5. Update agent state
            agent.last_active = state.current_time
            agent.activity_history.append(action)
            
            # 6. Stance shift (influenced by neighbors)
            if self.rng.random() < self.theta.stance_shift_rate:
                agent.stance = self._update_stance(agent, state)
        
        return state
    
    def _compute_exposure(self, state: SimulationState) -> List[int]:
        """
        Exposure mechanism: who sees content in their feed?
        
        This is the FEED ALGORITHM — often dominates outcomes more than agent behavior.
        """
        exposed = []
        
        for agent_id, agent in state.agents.items():
            # Probability of being exposed (based on engagement + recency + popularity)
            p_exposed = (
                agent.engagement_level * agent.interest_decay *
                self.theta.exposure_recency_weight
            )
            
            # Add popularity boost (if highly central)
            p_exposed += agent.centrality * self.theta.exposure_popularity_weight
            
            # Personalization (content matching agent's stance)
            # TODO: Implement content-agent affinity
            p_exposed += self.theta.exposure_personalization_weight * 0.5
            
            p_exposed = np.clip(p_exposed, 0.0, 1.0)
            
            if self.rng.random() < p_exposed:
                exposed.append(agent_id)
        
        return exposed
    
    def _select_action(self, agent: Agent, state: SimulationState) -> str:
        """
        Statistical behavioral policy: select action WITHOUT LLM.
        
        LLM only generates text AFTER action is selected.
        This is much faster and more controllable.
        """
        # Action probabilities based on agent parameters
        p_comment = self.theta.action_base_rate["comment"] * agent.engagement_level
        p_upvote = self.theta.action_base_rate["upvote"] * agent.engagement_level
        p_ignore = 1.0 - p_comment - p_upvote
        
        # Normalize
        total = p_comment + p_upvote + p_ignore
        probs = [p_comment / total, p_upvote / total, p_ignore / total]
        
        action = self.rng.choice(
            ["comment", "upvote", "ignore"],
            p=probs,
        )
        
        return action
    
    def _generate_text_llm(
        self,
        agent: Agent,
        state: SimulationState,
        query: Dict,
    ) -> str:
        """
        LLM generates text content (semantic layer only).
        
        This is the ONLY place LLM is used. Everything else is statistical.
        
        In production, this would call OpenAI API. For now, template.
        """
        # TODO: Actual LLM call with theta.llm_model, theta.llm_temperature
        
        # Template-based placeholder (replace with actual LLM)
        if agent.stance > 0.3:
            sentiment = "support"
        elif agent.stance < -0.3:
            sentiment = "oppose"
        else:
            sentiment = "neutral"
        
        return f"[Agent {agent.agent_id} {sentiment}s the policy]"
    
    def _update_stance(self, agent: Agent, state: SimulationState) -> float:
        """
        Update agent stance based on neighbor influence.
        
        Social influence mechanism (statistical).
        """
        if len(agent.neighbors) == 0:
            return agent.stance
        
        # Average neighbor stance
        neighbor_stances = [
            state.agents[n].stance
            for n in agent.neighbors
            if n in state.agents
        ]
        
        if len(neighbor_stances) == 0:
            return agent.stance
        
        mean_neighbor_stance = np.mean(neighbor_stances)
        
        # Move toward neighbor average (weighted by susceptibility)
        new_stance = (
            agent.stance * (1 - agent.susceptibility) +
            mean_neighbor_stance * agent.susceptibility
        )
        
        return np.clip(new_stance, -1.0, 1.0)
    
    def _aggregate_outcomes(self, state: SimulationState) -> Dict:
        """
        Aggregate simulation results into predictions.
        """
        # Count stances
        stance_counts = defaultdict(int)
        for agent in state.agents.values():
            if agent.stance > 0.3:
                stance_counts["support"] += 1
            elif agent.stance < -0.3:
                stance_counts["oppose"] += 1
            else:
                stance_counts["neutral"] += 1
        
        total = sum(stance_counts.values())
        outcome_probs = {
            k: v / total for k, v in stance_counts.items()
        }
        
        # Extract social dynamics
        cascade_sizes = self._compute_cascade_sizes(state)
        reply_depths = self._compute_reply_depths(state)
        branching_factors = self._compute_branching_factors(state)
        
        return {
            "outcome_probabilities": outcome_probs,
            "cascade_sizes": cascade_sizes,
            "reply_depths": reply_depths,
            "branching_factors": branching_factors,
            "num_interactions": len(state.interaction_history),
        }
    
    def _compute_cascade_sizes(self, state: SimulationState) -> List[int]:
        """Compute reply cascade sizes."""
        # TODO: Implement thread tracking
        return [1] * len(state.interaction_history)  # Placeholder
    
    def _compute_reply_depths(self, state: SimulationState) -> List[int]:
        """Compute reply depths."""
        # TODO: Implement thread tracking
        return [1] * len(state.interaction_history)  # Placeholder
    
    def _compute_branching_factors(self, state: SimulationState) -> List[float]:
        """Compute branching factors."""
        # TODO: Implement thread tracking
        return [1.0] * len(state.interaction_history)  # Placeholder
    
    def _apply_calibration(self, outcomes: Dict) -> Dict:
        """
        Apply Platt scaling calibration to raw probabilities.
        
        This corrects systematic over/under-confidence.
        """
        calibrated = {}
        
        for outcome, p in outcomes["outcome_probabilities"].items():
            # Platt scaling: p_cal = 1 / (1 + exp(-(a*logit(p) + b)))
            if p == 0:
                p = 1e-10
            if p == 1:
                p = 1 - 1e-10
            
            logit_p = np.log(p / (1 - p))
            scaled_logit = self.theta.calibration_temperature * logit_p + self.theta.calibration_bias
            p_cal = 1 / (1 + np.exp(-scaled_logit))
            
            calibrated[outcome] = p_cal
        
        # Renormalize
        total = sum(calibrated.values())
        calibrated = {k: v / total for k, v in calibrated.items()}
        
        outcomes["outcome_probabilities"] = calibrated
        return outcomes
    
    def _to_simulation_output(
        self,
        outcomes: Dict,
        state: SimulationState,
    ) -> SimulationOutput:
        """Package results as SimulationOutput."""
        
        # Create distributions (placeholder histograms)
        response_dist = np.array([
            outcomes["outcome_probabilities"].get("oppose", 0),
            outcomes["outcome_probabilities"].get("neutral", 0),
            outcomes["outcome_probabilities"].get("support", 0),
        ])
        
        engagement_dist = np.histogram(
            [a.engagement_level for a in state.agents.values()],
            bins=10,
            density=True,
        )[0]
        
        timing_dist = np.histogram(
            [i["time"] for i in state.interaction_history],
            bins=10,
            density=True,
        )[0]
        
        toxicity_scores = [0.1] * len(state.interaction_history)  # Placeholder
        
        return SimulationOutput(
            outcome_probabilities=outcomes["outcome_probabilities"],
            response_distribution=response_dist,
            engagement_distribution=engagement_dist,
            timing_distribution=timing_dist,
            cascade_sizes=outcomes["cascade_sizes"],
            reply_depths=outcomes["reply_depths"],
            branching_factors=outcomes["branching_factors"],
            toxicity_scores=toxicity_scores,
            num_agents=len(state.agents),
            num_interactions=outcomes["num_interactions"],
            simulation_time_hours=state.current_time,
        )
