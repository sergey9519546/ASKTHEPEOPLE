---
title: "Temporal Simulation Architecture"
status: "Design Proposal"
version: "0.1.0"
owner: "Simulation Engineering"
created: "2026-08-03"
last_reviewed: "2026-08-03"
research_cutoff: "2026-08-03"
applies_to: "backend/app/services/temporal_simulation.py, simulation pipeline extensions"
---

# Temporal Simulation Architecture

> **Purpose.** This document specifies a multi-stage temporal simulation system for "what happens next" prediction. Current simulations are snapshots at T=0. This architecture extends the system to model evolution over T+1 week, month, 6 months with belief updating, events, and state persistence between stages.

## Executive Summary

The temporal simulation system transforms single-snapshot simulations into multi-stage trajectories that:
- Model belief evolution through Bayesian updating, social influence, and confirmation bias
- Support user-defined events (competitor launches, regulatory changes) and emergent events
- Persist agent state (beliefs, relationships, stances) between time stages
- Generate confidence intervals and probability distributions over time
- Enable adoption curve modeling (Diffusion of Innovations integration)

**Key principle:** Temporal stages represent **synthetic scenario progression**, not forecasts or predictions of real human behavior.

## 1. Architecture Overview

### 1.1 Multi-Stage Simulation Loop

```
T=0 (Initial State)
  ↓
[Stage 1: T+1 week]
  - Load agent state from T=0
  - Apply scheduled events
  - Run simulation rounds
  - Update beliefs based on observations
  - Persist updated agent state
  ↓
[Stage 2: T+1 month]
  - Load agent state from Stage 1
  - Apply scheduled events
  - Run simulation rounds
  - Update beliefs and relationships
  - Persist updated agent state
  ↓
[Stage 3: T+3 months]
  ↓
[Stage 4: T+6 months]
  ↓
[Final Analysis]
  - Generate adoption curves
  - Confidence intervals
  - Path probability distributions
```

### 1.2 Core Components

```
temporal_simulation.py
├── TemporalSimulationManager
│   ├── create_temporal_run()
│   ├── execute_stage()
│   └── analyze_trajectory()
├── BeliefUpdateEngine
│   ├── bayesian_update()
│   ├── social_influence_update()
│   └── apply_confirmation_bias()
├── EventSystem
│   ├── EventScheduler
│   ├── EmergentEventDetector
│   └── ExternalShockHandler
└── StateManager
    ├── save_stage_snapshot()
    ├── load_stage_snapshot()
    └── compute_deltas()
```

## 2. Belief Updating Mechanisms

### 2.1 Bayesian Belief Updating

Agents revise beliefs when exposed to new information:

```python
# Prior belief: P(H)
# New evidence: E
# Updated belief: P(H|E) = P(E|H) * P(H) / P(E)

class BayesianBeliefUpdate:
    def update_belief(self, agent, evidence, topic):
        """
        Update agent belief on a topic given new evidence.
        
        Args:
            agent: Agent with prior belief
            evidence: Observation or interaction
            topic: Belief dimension (e.g., "product_value", "safety_concern")
        
        Returns:
            Updated belief probability
        """
        prior = agent.beliefs.get(topic, 0.5)
        likelihood = self.compute_likelihood(evidence, topic, agent.stance)
        evidence_prob = self.compute_evidence_probability(evidence, topic)
        
        posterior = (likelihood * prior) / evidence_prob
        
        # Apply personality-based learning rate
        learning_rate = self.get_learning_rate(agent)
        updated_belief = prior + learning_rate * (posterior - prior)
        
        return self.clamp(updated_belief, 0.0, 1.0)
```

**Key parameters:**
- `learning_rate`: How quickly agent updates beliefs (0.1-0.9)
  - High openness → high learning rate
  - High confirmation bias → low learning rate for contradictory evidence
- `evidence_strength`: How compelling the evidence is (0.0-1.0)
- `prior_confidence`: How strongly agent holds prior belief

### 2.2 Social Influence Model

Agents are influenced by peers, with strength depending on:
- **Relationship strength**: Closer connections have more influence
- **Authority**: Some agents carry more weight (experts, influencers)
- **Homophily**: Similar agents influence each other more

```python
class SocialInfluenceEngine:
    def apply_social_influence(self, agent, network_state, topic):
        """
        Update agent belief based on peer opinions.
        
        Uses weighted average of connected agents' beliefs:
        belief_new = belief_old * (1-α) + Σ(w_i * belief_i) * α
        
        where:
        - α is social influence susceptibility
        - w_i is normalized influence weight of peer i
        """
        peer_beliefs = []
        weights = []
        
        for peer_id in agent.connections:
            peer = network_state.get_agent(peer_id)
            if not peer:
                continue
                
            # Influence weight factors
            relationship_strength = agent.relationships[peer_id].strength
            authority_weight = peer.influence_weight
            similarity = self.compute_similarity(agent, peer)
            
            weight = relationship_strength * authority_weight * similarity
            weights.append(weight)
            peer_beliefs.append(peer.beliefs.get(topic, 0.5))
        
        if not weights:
            return agent.beliefs.get(topic, 0.5)
        
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        # Weighted average of peer beliefs
        social_belief = sum(b * w for b, w in zip(peer_beliefs, normalized_weights))
        
        # Blend with current belief
        susceptibility = agent.personality.social_influence_susceptibility
        current_belief = agent.beliefs.get(topic, 0.5)
        
        return current_belief * (1 - susceptibility) + social_belief * susceptibility
```

**Personality modifiers:**
- High `authority_sensitivity` → more influenced by high-status peers
- Low `conflict_tolerance` → avoids adopting minority views
- High `novelty_seeking` → more open to divergent opinions

### 2.3 Confirmation Bias

Agents process evidence through biased filters:

```python
class ConfirmationBiasFilter:
    def process_evidence(self, agent, evidence, topic):
        """
        Apply confirmation bias to evidence processing.
        
        Agents:
        - Overweight evidence supporting prior beliefs
        - Underweight contradictory evidence
        - Selectively attend to belief-consistent information
        """
        current_belief = agent.beliefs.get(topic, 0.5)
        evidence_valence = self.extract_valence(evidence, topic)
        
        # Does evidence support or contradict current belief?
        alignment = self.compute_alignment(current_belief, evidence_valence)
        
        # Bias strength from personality
        bias_strength = agent.personality.confirmation_bias
        
        # Modify evidence strength based on alignment
        if alignment > 0:  # Evidence supports belief
            effective_strength = evidence.strength * (1 + bias_strength * 0.5)
        else:  # Evidence contradicts belief
            effective_strength = evidence.strength * (1 - bias_strength * 0.5)
        
        return {
            'original_strength': evidence.strength,
            'effective_strength': self.clamp(effective_strength, 0.0, 1.0),
            'attended': self.attention_gate(alignment, bias_strength)
        }
    
    def attention_gate(self, alignment, bias_strength):
        """
        Determine if agent even processes the evidence.
        Strong bias → ignore contradictory information.
        """
        if alignment < 0:  # Contradictory
            ignore_probability = bias_strength * 0.3
            return random.random() > ignore_probability
        return True
```

### 2.4 Personality-Belief Interaction Matrix

| Personality Trait | Effect on Belief Updating |
|---|---|
| `openness` | High → faster learning, low confirmation bias |
| `conscientiousness` | High → slower updates, requires more evidence |
| `authority_sensitivity` | High → strong influence from high-status sources |
| `conflict_tolerance` | Low → avoids belief changes that create social tension |
| `novelty_seeking` | High → attracted to new/contrarian information |
| `confirmation_bias` | High → reinforces existing beliefs, resists change |

## 3. Time Stage Design

### 3.1 Configurable Time Intervals

Default stages for strategic scenario planning:

```python
DEFAULT_TEMPORAL_STAGES = [
    {"name": "baseline", "offset_days": 0, "label": "T+0 (Initial)"},
    {"name": "immediate", "offset_days": 7, "label": "T+1 week"},
    {"name": "short_term", "offset_days": 30, "label": "T+1 month"},
    {"name": "medium_term", "offset_days": 90, "label": "T+3 months"},
    {"name": "long_term", "offset_days": 180, "label": "T+6 months"},
]

# Alternative configurations for different use cases
FAST_ITERATION_STAGES = [
    {"offset_days": 0}, {"offset_days": 1}, {"offset_days": 3}, 
    {"offset_days": 7}, {"offset_days": 14}
]

LONG_HORIZON_STAGES = [
    {"offset_days": 0}, {"offset_days": 30}, {"offset_days": 90},
    {"offset_days": 180}, {"offset_days": 365}, {"offset_days": 730}
]
```

### 3.2 Multi-Timescale Processes

Different processes operate at different timescales:

| Process | Timescale | Stage Granularity |
|---|---|---|
| Viral content spread | Hours-days | Fine-grained (1-7 days) |
| Opinion shift | Days-weeks | Medium (7-30 days) |
| Adoption curve | Weeks-months | Coarse (30-90 days) |
| Relationship formation | Weeks-months | Coarse (30-180 days) |
| Cultural norms | Months-years | Very coarse (90-365 days) |

**Adaptive resolution:** System can run finer-grained sub-stages for fast processes while maintaining coarse snapshots for slow processes.

```python
class MultiTimescaleSimulation:
    def __init__(self, config):
        self.macro_stages = config.temporal_stages  # User-defined checkpoints
        self.micro_rounds_per_stage = self.compute_micro_rounds(config)
    
    def compute_micro_rounds(self, config):
        """
        Determine simulation rounds between macro stages.
        
        Example: T+0 to T+7 days with 60min/round
        = 7 days * 24 hours * (60/60) = 168 rounds
        """
        rounds_map = {}
        for i in range(len(self.macro_stages) - 1):
            current_stage = self.macro_stages[i]
            next_stage = self.macro_stages[i+1]
            
            days_between = next_stage['offset_days'] - current_stage['offset_days']
            hours_between = days_between * 24
            rounds = int(hours_between * (60 / config.minutes_per_round))
            
            rounds_map[current_stage['name']] = rounds
        
        return rounds_map
```

### 3.3 Stage Execution Flow

```python
class TemporalStage:
    """Represents one temporal checkpoint in the simulation."""
    
    def __init__(self, stage_config, previous_stage=None):
        self.name = stage_config['name']
        self.offset_days = stage_config['offset_days']
        self.previous_stage = previous_stage
        
        # State carried forward
        self.agent_states = None
        self.network_state = None
        self.belief_distributions = None
        self.content_corpus = None
    
    def execute(self, simulation_context):
        """Execute this temporal stage."""
        
        # 1. Load initial state
        if self.previous_stage:
            self.load_from_previous(self.previous_stage)
        else:
            self.initialize_baseline(simulation_context)
        
        # 2. Apply scheduled events for this stage
        events = simulation_context.get_events_at_stage(self.offset_days)
        self.apply_events(events)
        
        # 3. Run simulation rounds
        rounds = simulation_context.get_rounds_for_stage(self.name)
        for round_num in range(rounds):
            self.execute_round(round_num, simulation_context)
        
        # 4. Update beliefs based on accumulated observations
        self.update_all_beliefs()
        
        # 5. Detect emergent events
        emergent = self.detect_emergent_events()
        if emergent:
            simulation_context.register_emergent_events(emergent)
        
        # 6. Persist stage snapshot
        self.save_snapshot(simulation_context.storage)
        
        return self.generate_stage_summary()
```

## 4. Event System

### 4.1 Event Types

```python
class EventType(Enum):
    USER_SCHEDULED = "user_scheduled"      # Pre-defined by user
    EMERGENT = "emergent"                  # Triggered by simulation state
    EXTERNAL_SHOCK = "external_shock"      # Exogenous changes

class SimulationEvent:
    """Base class for all simulation events."""
    
    def __init__(self, event_type, trigger_time, description):
        self.event_type = event_type
        self.trigger_time = trigger_time  # Days since T=0
        self.description = description
        self.synthetic_provenance = True  # Machine-enforced
    
    def apply(self, simulation_state):
        """Apply event effects to simulation state."""
        raise NotImplementedError
```

### 4.2 User-Defined Events

Users specify events at configuration time:

```json
{
  "temporal_stages": [...],
  "scheduled_events": [
    {
      "type": "user_scheduled",
      "trigger_day": 14,
      "event_class": "competitor_launch",
      "description": "Competitor X launches similar product",
      "effects": {
        "inject_posts": [
          {
            "platform": "twitter",
            "agent_archetypes": ["tech_enthusiast", "early_adopter"],
            "content_template": "Just heard about {competitor_product}. Looks interesting compared to {our_product}.",
            "sentiment": "neutral_curious"
          }
        ],
        "modify_beliefs": {
          "topic": "market_competition",
          "agents": "all",
          "shift": -0.1
        }
      }
    },
    {
      "type": "external_shock",
      "trigger_day": 45,
      "event_class": "regulatory_change",
      "description": "New data privacy regulation announced",
      "effects": {
        "inject_posts": [...],
        "modify_agent_concerns": {
          "topic": "privacy_risk",
          "shift": +0.3
        }
      }
    }
  ]
}
```

**Event application:**

```python
class UserScheduledEvent(SimulationEvent):
    def __init__(self, config):
        super().__init__(
            EventType.USER_SCHEDULED,
            config['trigger_day'],
            config['description']
        )
        self.effects = config['effects']
    
    def apply(self, simulation_state):
        """Apply pre-configured effects."""
        
        # Inject content
        if 'inject_posts' in self.effects:
            for post_spec in self.effects['inject_posts']:
                agents = self.select_agents(
                    simulation_state, 
                    post_spec.get('agent_archetypes', [])
                )
                for agent in agents:
                    self.create_post(agent, post_spec, simulation_state)
        
        # Modify beliefs
        if 'modify_beliefs' in self.effects:
            belief_mod = self.effects['modify_beliefs']
            topic = belief_mod['topic']
            shift = belief_mod['shift']
            
            target_agents = self.get_target_agents(
                simulation_state, 
                belief_mod.get('agents', 'all')
            )
            
            for agent in target_agents:
                current = agent.beliefs.get(topic, 0.5)
                agent.beliefs[topic] = self.clamp(current + shift, 0.0, 1.0)
        
        # Log event
        simulation_state.event_log.append({
            'stage': simulation_state.current_stage,
            'event': self.description,
            'type': 'user_scheduled',
            'synthetic_disclosure': True
        })
```

### 4.3 Emergent Events

Detected automatically based on simulation state:

```python
class EmergentEventDetector:
    """Detects patterns in simulation that trigger new events."""
    
    def detect_events(self, stage_state, previous_state):
        """
        Scan for emergent patterns:
        - Viral content (rapid spread threshold crossed)
        - Polarization (belief divergence exceeds threshold)
        - Consensus formation (belief convergence)
        - Network fragmentation (community splitting)
        - Tipping point (adoption acceleration)
        """
        events = []
        
        # Viral spread detection
        viral_posts = self.detect_viral_content(stage_state)
        for post in viral_posts:
            events.append(ViralContentEvent(post, stage_state.current_day))
        
        # Polarization detection
        if self.detect_polarization(stage_state, previous_state):
            events.append(PolarizationEvent(stage_state.current_day))
        
        # Tipping point detection (adoption acceleration)
        if self.detect_tipping_point(stage_state, previous_state):
            events.append(TippingPointEvent(stage_state.current_day))
        
        return events
    
    def detect_viral_content(self, state):
        """Identify posts crossing viral threshold."""
        viral_posts = []
        for post in state.recent_posts:
            engagement = post.likes + post.shares + post.comments
            velocity = engagement / post.hours_since_creation
            
            if velocity > state.config.viral_velocity_threshold:
                viral_posts.append(post)
        
        return viral_posts
    
    def detect_tipping_point(self, current, previous):
        """
        Detect adoption acceleration (Diffusion of Innovations).
        Tipping point: transition from early adopters to early majority.
        """
        if not previous:
            return False
        
        current_adoption = self.compute_adoption_rate(current)
        previous_adoption = self.compute_adoption_rate(previous)
        
        acceleration = (current_adoption - previous_adoption) / previous_adoption
        
        # Tipping point: adoption rate increases >50% AND crosses 16% threshold
        return (acceleration > 0.5 and 
                previous_adoption < 0.16 and 
                current_adoption >= 0.16)
```

### 4.4 External Shocks

Large exogenous changes:

```python
class ExternalShock(SimulationEvent):
    """
    Represents major external changes:
    - Economic shifts
    - Regulatory changes  
    - Competitor actions
    - Technology breakthroughs
    - Social movements
    """
    
    SHOCK_TYPES = {
        'economic_downturn': {
            'belief_shifts': {'affordability_concern': +0.3, 'purchase_intent': -0.2},
            'activity_changes': {'overall': -0.15}
        },
        'security_breach': {
            'belief_shifts': {'trust': -0.4, 'security_concern': +0.5},
            'activity_changes': {'negative_sentiment': +0.3}
        },
        'influencer_endorsement': {
            'belief_shifts': {'awareness': +0.2, 'social_proof': +0.3},
            'activity_changes': {'overall': +0.2}
        }
    }
    
    def apply(self, simulation_state):
        shock_config = self.SHOCK_TYPES[self.shock_type]
        
        # Apply belief shifts across all agents (with personality modulation)
        for topic, shift in shock_config['belief_shifts'].items():
            for agent in simulation_state.agents:
                modulated_shift = shift * agent.personality.external_sensitivity
                current = agent.beliefs.get(topic, 0.5)
                agent.beliefs[topic] = self.clamp(current + modulated_shift, 0.0, 1.0)
        
        # Modify activity levels
        for activity_type, change in shock_config['activity_changes'].items():
            simulation_state.activity_modifiers[activity_type] = change
```

## 5. State Persistence Between Stages

### 5.1 Agent State Schema

```python
class AgentTemporalState:
    """Complete agent state at a temporal checkpoint."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.stage_name = None
        self.timestamp = None
        
        # Beliefs (topic → probability)
        self.beliefs = {}
        
        # Relationships (peer_id → relationship strength)
        self.relationships = {}
        
        # Stance evolution
        self.stance_history = []  # [(stage, stance, confidence)]
        
        # Behavioral state
        self.activity_level = 0.5
        self.sentiment_bias = 0.0
        
        # Memory (recent significant interactions)
        self.memory = []  # Limited to last N significant events
        
        # Influence metrics
        self.influence_weight = 1.0
        self.follower_count = 0
    
    def to_dict(self):
        return {
            'agent_id': self.agent_id,
            'stage': self.stage_name,
            'timestamp': self.timestamp,
            'beliefs': self.beliefs,
            'relationships': {str(k): v for k, v in self.relationships.items()},
            'stance_history': self.stance_history,
            'activity_level': self.activity_level,
            'sentiment_bias': self.sentiment_bias,
            'memory': self.memory[-50:],  # Keep last 50 events
            'influence_weight': self.influence_weight,
            'synthetic_provenance': True
        }
```

### 5.2 Stage Snapshot Storage

```sql
-- Database schema for temporal snapshots
CREATE TABLE temporal_stages (
    stage_id UUID PRIMARY KEY,
    simulation_id UUID NOT NULL,
    stage_name TEXT NOT NULL,
    offset_days INTEGER NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL,
    rounds_executed INTEGER,
    
    -- Aggregate metrics
    total_posts INTEGER,
    total_interactions INTEGER,
    adoption_rate FLOAT,
    
    -- Provenance
    synthetic_disclosure BOOLEAN DEFAULT TRUE,
    
    UNIQUE(simulation_id, stage_name)
);

CREATE TABLE agent_stage_snapshots (
    snapshot_id UUID PRIMARY KEY,
    stage_id UUID REFERENCES temporal_stages(stage_id),
    agent_id INTEGER NOT NULL,
    
    -- Serialized state
    beliefs_json JSONB NOT NULL,
    relationships_json JSONB NOT NULL,
    stance TEXT,
    stance_confidence FLOAT,
    activity_level FLOAT,
    sentiment_bias FLOAT,
    influence_weight FLOAT,
    
    -- Memory
    memory_json JSONB,
    
    UNIQUE(stage_id, agent_id)
);

CREATE TABLE stage_events (
    event_id UUID PRIMARY KEY,
    stage_id UUID REFERENCES temporal_stages(stage_id),
    event_type TEXT NOT NULL,
    trigger_day INTEGER,
    description TEXT,
    effects_json JSONB,
    synthetic_disclosure BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_snapshots_stage ON agent_stage_snapshots(stage_id);
CREATE INDEX idx_events_stage ON stage_events(stage_id);
```

### 5.3 State Manager

```python
class TemporalStateManager:
    """Manages state persistence and loading between stages."""
    
    def save_stage_snapshot(self, stage_name, simulation_state, db_conn):
        """
        Save complete simulation state at stage checkpoint.
        """
        # Create stage record
        stage_id = str(uuid.uuid4())
        stage_data = {
            'stage_id': stage_id,
            'simulation_id': simulation_state.simulation_id,
            'stage_name': stage_name,
            'offset_days': simulation_state.current_day,
            'executed_at': datetime.now(),
            'rounds_executed': simulation_state.rounds_completed,
            'total_posts': len(simulation_state.all_posts),
            'total_interactions': simulation_state.total_interactions,
            'adoption_rate': self.compute_adoption_rate(simulation_state),
            'synthetic_disclosure': True
        }
        
        self.insert_stage(stage_data, db_conn)
        
        # Save all agent states
        for agent in simulation_state.agents:
            agent_snapshot = AgentTemporalState(agent.agent_id)
            agent_snapshot.stage_name = stage_name
            agent_snapshot.timestamp = datetime.now()
            agent_snapshot.beliefs = agent.beliefs.copy()
            agent_snapshot.relationships = agent.relationships.copy()
            agent_snapshot.stance_history = agent.stance_history[-10:]
            agent_snapshot.activity_level = agent.activity_level
            agent_snapshot.sentiment_bias = agent.sentiment_bias
            agent_snapshot.memory = agent.memory[-50:]
            agent_snapshot.influence_weight = agent.influence_weight
            
            self.insert_agent_snapshot(stage_id, agent_snapshot, db_conn)
        
        # Save events that occurred during this stage
        for event in simulation_state.events_this_stage:
            self.insert_stage_event(stage_id, event, db_conn)
        
        return stage_id
    
    def load_stage_snapshot(self, stage_id, db_conn):
        """
        Load complete simulation state from checkpoint.
        """
        # Load stage metadata
        stage_data = self.fetch_stage(stage_id, db_conn)
        
        # Load all agent states
        agent_snapshots = self.fetch_agent_snapshots(stage_id, db_conn)
        
        # Reconstruct simulation state
        simulation_state = SimulationState()
        simulation_state.simulation_id = stage_data['simulation_id']
        simulation_state.current_stage = stage_data['stage_name']
        simulation_state.current_day = stage_data['offset_days']
        
        # Restore agents
        for snapshot in agent_snapshots:
            agent = self.restore_agent_from_snapshot(snapshot)
            simulation_state.agents.append(agent)
        
        return simulation_state
    
    def compute_delta(self, previous_stage_id, current_stage_id, db_conn):
        """
        Compute changes between two stages for analysis.
        """
        prev_snapshots = self.fetch_agent_snapshots(previous_stage_id, db_conn)
        curr_snapshots = self.fetch_agent_snapshots(current_stage_id, db_conn)
        
        deltas = []
        for prev, curr in zip(prev_snapshots, curr_snapshots):
            delta = {
                'agent_id': prev['agent_id'],
                'belief_changes': {},
                'relationship_changes': {},
                'stance_change': None
            }
            
            # Belief deltas
            prev_beliefs = prev['beliefs_json']
            curr_beliefs = curr['beliefs_json']
            for topic in set(prev_beliefs.keys()) | set(curr_beliefs.keys()):
                prev_val = prev_beliefs.get(topic, 0.5)
                curr_val = curr_beliefs.get(topic, 0.5)
                if abs(curr_val - prev_val) > 0.05:  # Significant change threshold
                    delta['belief_changes'][topic] = {
                        'from': prev_val,
                        'to': curr_val,
                        'change': curr_val - prev_val
                    }
            
            # Stance change
            if prev['stance'] != curr['stance']:
                delta['stance_change'] = {
                    'from': prev['stance'],
                    'to': curr['stance']
                }
            
            deltas.append(delta)
        
        return deltas
```

## 6. Integration with Existing System

### 6.1 New Module Structure

```
backend/app/services/
├── temporal_simulation.py          # NEW: Main temporal orchestrator
├── belief_engine.py                 # NEW: Belief updating logic
├── event_system.py                  # NEW: Event scheduling and detection
├── temporal_state_manager.py        # NEW: State persistence
├── simulation_runner.py             # EXTEND: Add temporal mode
├── simulation_manager.py            # EXTEND: Support temporal configs
└── simulation_config_generator.py   # EXTEND: Generate temporal params
```

### 6.2 API Extensions

```python
# New endpoint: POST /api/simulation/temporal
@simulation_bp.route('/temporal', methods=['POST'])
@limiter.limit("5 per hour")
def create_temporal_simulation():
    """
    Create a multi-stage temporal simulation.
    
    Request body:
    {
        "project_id": "proj_xyz",
        "graph_id": "graph_abc",
        "simulation_requirement": "What happens if we launch product X?",
        "temporal_config": {
            "stages": [
                {"name": "immediate", "offset_days": 7},
                {"name": "short_term", "offset_days": 30},
                {"name": "medium_term", "offset_days": 90}
            ],
            "enable_belief_updating": true,
            "enable_social_influence": true,
            "belief_update_params": {
                "learning_rate_range": [0.1, 0.7],
                "social_influence_weight": 0.3,
                "confirmation_bias_strength": 0.5
            }
        },
        "scheduled_events": [
            {
                "trigger_day": 14,
                "type": "competitor_launch",
                "description": "Competitor releases similar feature",
                "effects": {...}
            }
        ]
    }
    
    Response:
    {
        "temporal_simulation_id": "tsim_123abc",
        "status": "created",
        "stages": [...],
        "synthetic_disclosure": true
    }
    """
    data = request.get_json()
    
    # Validate temporal configuration
    validator = TemporalConfigValidator()
    validator.validate(data['temporal_config'])
    
    # Create temporal simulation
    manager = TemporalSimulationManager()
    temporal_sim = manager.create_temporal_simulation(
        project_id=data['project_id'],
        graph_id=data['graph_id'],
        requirement=data['simulation_requirement'],
        temporal_config=data['temporal_config'],
        scheduled_events=data.get('scheduled_events', [])
    )
    
    return jsonify({
        'temporal_simulation_id': temporal_sim.id,
        'status': 'created',
        'stages': temporal_sim.stages,
        'synthetic_disclosure': True,
        **truth_metadata()
    })

# Get temporal simulation status
@simulation_bp.route('/temporal/<temporal_sim_id>/status', methods=['GET'])
def get_temporal_status(temporal_sim_id):
    """
    Get execution status of temporal simulation.
    
    Response:
    {
        "temporal_simulation_id": "tsim_123",
        "status": "running",
        "current_stage": "short_term",
        "stages_completed": 2,
        "total_stages": 4,
        "progress": 0.5,
        "adoption_curve": [...],
        "synthetic_disclosure": true
    }
    """
    manager = TemporalSimulationManager()
    status = manager.get_status(temporal_sim_id)
    
    return jsonify({
        **status,
        'synthetic_disclosure': True,
        **truth_metadata()
    })

# Get stage comparison
@simulation_bp.route('/temporal/<temporal_sim_id>/compare', methods=['GET'])
def compare_stages(temporal_sim_id):
    """
    Compare two temporal stages.
    
    Query params: ?from_stage=immediate&to_stage=short_term
    
    Response:
    {
        "from_stage": "immediate",
        "to_stage": "short_term",
        "belief_changes": [...],
        "adoption_delta": 0.15,
        "stance_shifts": [...],
        "emergent_events": [...],
        "synthetic_disclosure": true
    }
    """
    from_stage = request.args.get('from_stage')
    to_stage = request.args.get('to_stage')
    
    manager = TemporalSimulationManager()
    comparison = manager.compare_stages(temporal_sim_id, from_stage, to_stage)
    
    return jsonify({
        **comparison,
        'synthetic_disclosure': True,
        **truth_metadata()
    })
```

### 6.3 Database Migrations

```python
# migration: add_temporal_simulation_tables.py

def upgrade():
    # Add temporal simulation tracking
    op.create_table(
        'temporal_simulations',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('project_id', sa.String(50), nullable=False),
        sa.Column('graph_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('config_json', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, onupdate=datetime.utcnow),
        sa.Column('synthetic_disclosure', sa.Boolean, default=True)
    )
    
    # Temporal stages
    op.create_table(
        'temporal_stages',
        sa.Column('stage_id', sa.String(50), primary_key=True),
        sa.Column('temporal_simulation_id', sa.String(50), 
                  sa.ForeignKey('temporal_simulations.id')),
        sa.Column('stage_name', sa.String(50), nullable=False),
        sa.Column('offset_days', sa.Integer, nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('executed_at', sa.DateTime),
        sa.Column('rounds_executed', sa.Integer),
        sa.Column('adoption_rate', sa.Float),
        sa.Column('synthetic_disclosure', sa.Boolean, default=True)
    )
    
    # Agent snapshots
    op.create_table(
        'agent_stage_snapshots',
        sa.Column('snapshot_id', sa.String(50), primary_key=True),
        sa.Column('stage_id', sa.String(50), 
                  sa.ForeignKey('temporal_stages.stage_id')),
        sa.Column('agent_id', sa.Integer, nullable=False),
        sa.Column('beliefs_json', sa.JSON, nullable=False),
        sa.Column('relationships_json', sa.JSON, nullable=False),
        sa.Column('stance', sa.String(20)),
        sa.Column('activity_level', sa.Float),
        sa.Column('influence_weight', sa.Float)
    )
    
    # Stage events
    op.create_table(
        'stage_events',
        sa.Column('event_id', sa.String(50), primary_key=True),
        sa.Column('stage_id', sa.String(50), 
                  sa.ForeignKey('temporal_stages.stage_id')),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('trigger_day', sa.Integer),
        sa.Column('description', sa.Text),
        sa.Column('effects_json', sa.JSON),
        sa.Column('synthetic_disclosure', sa.Boolean, default=True)
    )
    
    # Indexes
    op.create_index('idx_stages_temporal_sim', 'temporal_stages', 
                    ['temporal_simulation_id'])
    op.create_index('idx_snapshots_stage', 'agent_stage_snapshots', 
                    ['stage_id'])
    op.create_index('idx_events_stage', 'stage_events', ['stage_id'])

def downgrade():
    op.drop_table('stage_events')
    op.drop_table('agent_stage_snapshots')
    op.drop_table('temporal_stages')
    op.drop_table('temporal_simulations')
```

### 6.4 Diffusion of Innovations Integration

```python
class DiffusionCurveAnalyzer:
    """
    Analyze adoption curves across temporal stages.
    Implements Rogers' Diffusion of Innovations model.
    """
    
    ADOPTER_CATEGORIES = {
        'innovators': {'threshold': 0.025, 'label': 'Innovators (2.5%)'},
        'early_adopters': {'threshold': 0.135, 'label': 'Early Adopters (13.5%)'},
        'early_majority': {'threshold': 0.50, 'label': 'Early Majority (34%)'},
        'late_majority': {'threshold': 0.84, 'label': 'Late Majority (34%)'},
        'laggards': {'threshold': 1.0, 'label': 'Laggards (16%)'}
    }
    
    def analyze_adoption_trajectory(self, temporal_simulation_id):
        """
        Compute adoption curve across all stages.
        
        Returns:
        {
            "stages": ["T+0", "T+7d", "T+30d", "T+90d"],
            "adoption_rates": [0.02, 0.08, 0.25, 0.52],
            "adopter_categories": {
                "innovators": {"count": 15, "percentage": 0.025},
                "early_adopters": {"count": 81, "percentage": 0.135},
                ...
            },
            "tipping_point_stage": "T+30d",
            "diffusion_velocity": 0.15,
            "confidence_intervals": {
                "T+90d": {"low": 0.45, "high": 0.60},
                ...
            }
        }
        """
        stages = self.load_stages(temporal_simulation_id)
        adoption_data = []
        
        for stage in stages:
            snapshots = self.load_agent_snapshots(stage.stage_id)
            adoption_rate = self.compute_adoption_rate(snapshots)
            adoption_data.append({
                'stage': stage.stage_name,
                'offset_days': stage.offset_days,
                'adoption_rate': adoption_rate,
                'adopter_count': sum(1 for s in snapshots if self.is_adopter(s))
            })
        
        # Classify agents into adopter categories
        final_snapshots = self.load_agent_snapshots(stages[-1].stage_id)
        adopter_categories = self.classify_adopters(final_snapshots, stages)
        
        # Detect tipping point
        tipping_stage = self.detect_tipping_point(adoption_data)
        
        # Compute diffusion velocity (rate of change)
        velocity = self.compute_diffusion_velocity(adoption_data)
        
        # Generate confidence intervals (based on variance in agent beliefs)
        confidence_intervals = self.compute_confidence_intervals(stages)
        
        return {
            'stages': [d['stage'] for d in adoption_data],
            'adoption_rates': [d['adoption_rate'] for d in adoption_data],
            'adopter_categories': adopter_categories,
            'tipping_point_stage': tipping_stage,
            'diffusion_velocity': velocity,
            'confidence_intervals': confidence_intervals,
            'synthetic_disclosure': True
        }
    
    def classify_adopters(self, snapshots, stages):
        """
        Classify agents into Rogers' categories based on adoption timing.
        """
        # Find when each agent adopted
        adoption_times = {}
        for agent_id in [s['agent_id'] for s in snapshots]:
            adoption_stage = self.find_adoption_stage(agent_id, stages)
            if adoption_stage:
                adoption_times[agent_id] = adoption_stage.offset_days
        
        # Sort by adoption time
        sorted_adopters = sorted(adoption_times.items(), key=lambda x: x[1])
        total_adopters = len(sorted_adopters)
        
        categories = {}
        for category_name, config in self.ADOPTER_CATEGORIES.items():
            threshold = config['threshold']
            count = int(total_adopters * threshold)
            categories[category_name] = {
                'count': count,
                'percentage': threshold,
                'label': config['label']
            }
        
        return categories
    
    def detect_tipping_point(self, adoption_data):
        """
        Identify the stage where adoption accelerates (crosses 16% threshold).
        """
        for i in range(1, len(adoption_data)):
            prev_rate = adoption_data[i-1]['adoption_rate']
            curr_rate = adoption_data[i]['adoption_rate']
            
            # Tipping point: crosses 16% AND shows acceleration
            if prev_rate < 0.16 <= curr_rate:
                acceleration = (curr_rate - prev_rate) / prev_rate
                if acceleration > 0.3:  # 30% increase
                    return adoption_data[i]['stage']
        
        return None
    
    def compute_confidence_intervals(self, stages):
        """
        Generate confidence intervals based on belief variance.
        Higher variance → wider intervals.
        """
        intervals = {}
        
        for stage in stages:
            snapshots = self.load_agent_snapshots(stage.stage_id)
            adoption_beliefs = [
                s['beliefs_json'].get('adoption_intent', 0.5) 
                for s in snapshots
            ]
            
            mean = np.mean(adoption_beliefs)
            std = np.std(adoption_beliefs)
            
            # 95% confidence interval
            intervals[stage.stage_name] = {
                'mean': mean,
                'low': max(0.0, mean - 1.96 * std),
                'high': min(1.0, mean + 1.96 * std),
                'std': std
            }
        
        return intervals
```

## 7. UI/UX Considerations

### 7.1 Timeline Visualization

```javascript
// Frontend component for temporal stage timeline
class TemporalTimeline extends React.Component {
    render() {
        const { stages, currentStage, adoptionCurve } = this.props;
        
        return (
            <div className="temporal-timeline">
                {/* Stage markers */}
                <div className="stage-markers">
                    {stages.map((stage, idx) => (
                        <StageMarker 
                            key={stage.name}
                            stage={stage}
                            isActive={stage.name === currentStage}
                            isComplete={idx < this.getCurrentStageIndex()}
                            onClick={() => this.jumpToStage(stage.name)}
                        />
                    ))}
                </div>
                
                {/* Adoption curve graph */}
                <AdoptionCurveChart 
                    data={adoptionCurve}
                    confidenceIntervals={this.props.confidenceIntervals}
                />
                
                {/* Stage scrubber */}
                <StageScubber 
                    stages={stages}
                    currentStage={currentStage}
                    onStageChange={this.handleStageChange}
                />
                
                {/* Event markers */}
                <EventMarkers 
                    scheduledEvents={this.props.scheduledEvents}
                    emergentEvents={this.props.emergentEvents}
                />
            </div>
        );
    }
}
```

### 7.2 Stage Comparison View

```javascript
class StageComparisonView extends React.Component {
    render() {
        const { fromStage, toStage, comparison } = this.props;
        
        return (
            <div className="stage-comparison">
                <div className="comparison-header">
                    <StageSelector stage={fromStage} label="From" />
                    <ArrowIcon />
                    <StageSelector stage={toStage} label="To" />
                </div>
                
                {/* Belief changes */}
                <BeliefChangesTable 
                    changes={comparison.belief_changes}
                    showSignificantOnly={true}
                />
                
                {/* Adoption delta */}
                <MetricCard 
                    label="Adoption Change"
                    value={comparison.adoption_delta}
                    format="percentage"
                    trend={comparison.adoption_delta > 0 ? 'up' : 'down'}
                />
                
                {/* Stance shifts */}
                <StanceShiftVisualization 
                    shifts={comparison.stance_shifts}
                />
                
                {/* Emergent events */}
                <EmergentEventsList 
                    events={comparison.emergent_events}
                />
            </div>
        );
    }
}
```

### 7.3 Confidence Interval Display

```javascript
// Display adoption curve with confidence bands
class AdoptionCurveChart extends React.Component {
    renderChart() {
        const { data, confidenceIntervals } = this.props;
        
        // Plot mean adoption curve
        const meanLine = {
            x: data.map(d => d.stage),
            y: data.map(d => d.adoption_rate),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Mean Adoption Rate',
            line: { color: '#2563eb', width: 3 }
        };
        
        // Plot confidence band
        const upperBound = {
            x: data.map(d => d.stage),
            y: confidenceIntervals.map(ci => ci.high),
            type: 'scatter',
            mode: 'lines',
            name: '95% CI Upper',
            line: { width: 0 },
            fillcolor: 'rgba(37, 99, 235, 0.2)',
            fill: 'tonexty'
        };
        
        const lowerBound = {
            x: data.map(d => d.stage),
            y: confidenceIntervals.map(ci => ci.low),
            type: 'scatter',
            mode: 'lines',
            name: '95% CI Lower',
            line: { width: 0 }
        };
        
        // Rogers' adopter category boundaries
        const categoryLines = [
            { y: 0.025, label: 'Innovators' },
            { y: 0.16, label: 'Early Adopters' },
            { y: 0.50, label: 'Early Majority' }
        ];
        
        return (
            <Plot 
                data={[lowerBound, upperBound, meanLine]}
                layout={{
                    title: 'Adoption Trajectory Over Time',
                    xaxis: { title: 'Temporal Stage' },
                    yaxis: { title: 'Adoption Rate', range: [0, 1] },
                    shapes: categoryLines.map(cl => ({
                        type: 'line',
                        x0: 0,
                        x1: 1,
                        xref: 'paper',
                        y0: cl.y,
                        y1: cl.y,
                        line: { dash: 'dash', color: '#9ca3af' }
                    })),
                    annotations: categoryLines.map(cl => ({
                        x: 0.95,
                        xref: 'paper',
                        y: cl.y,
                        text: cl.label,
                        showarrow: false
                    }))
                }}
            />
        );
    }
}
```

## 8. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Create `temporal_simulation.py` module
- [ ] Implement `TemporalStateManager` with snapshot save/load
- [ ] Add database migrations for temporal tables
- [ ] Extend `SimulationRunner` to support stage execution

### Phase 2: Belief Engine (Week 3-4)
- [ ] Implement `BeliefUpdateEngine` with Bayesian updating
- [ ] Add social influence model
- [ ] Implement confirmation bias filtering
- [ ] Add personality-belief interaction matrix

### Phase 3: Event System (Week 5-6)
- [ ] Build `EventScheduler` for user-defined events
- [ ] Implement `EmergentEventDetector`
- [ ] Add external shock handlers
- [ ] Create event application logic

### Phase 4: API & Integration (Week 7-8)
- [ ] Add `/api/simulation/temporal` endpoint
- [ ] Add stage comparison endpoint
- [ ] Integrate with existing simulation pipeline
- [ ] Add Diffusion of Innovations analyzer

### Phase 5: UI/UX (Week 9-10)
- [ ] Build temporal timeline component
- [ ] Add adoption curve visualization
- [ ] Create stage scrubber
- [ ] Add confidence interval displays

### Phase 6: Testing & Documentation (Week 11-12)
- [ ] Unit tests for belief engine
- [ ] Integration tests for temporal pipeline
- [ ] Performance testing (large agent counts)
- [ ] User documentation and examples

## 9. Open Questions & Design Decisions

### 9.1 Computational Cost
**Question:** How to handle computational cost of multi-stage simulations?

**Options:**
1. Run stages sequentially (longer wall time, simpler)
2. Pre-compute multiple branches in parallel (faster, more complex)
3. Adaptive resolution (fine-grained for fast processes, coarse for slow)

**Recommendation:** Start with sequential execution. Add adaptive resolution in Phase 2.

### 9.2 Belief Convergence
**Question:** How to prevent belief "lock-in" where all agents converge?

**Solutions:**
- Inject diversity through scheduled events
- Model subpopulations with different information access
- Add stochastic perturbations to belief updates
- Maintain "stubborn" agents with low learning rates

### 9.3 Event Chaining
**Question:** Should emergent events trigger additional scheduled events?

**Recommendation:** Yes, but with depth limits to prevent runaway cascades. Max chain depth: 3.

### 9.4 Confidence Calibration
**Question:** How to calibrate confidence intervals?

**Approach:**
- Variance in agent beliefs → confidence width
- Number of agents → confidence precision
- Explicitly label as "scenario variance" not "forecast uncertainty"

## 10. Success Metrics

### 10.1 Technical Metrics
- **Stage execution time**: < 5 minutes per stage for 500 agents
- **State snapshot size**: < 50MB per stage
- **Belief update latency**: < 100ms per agent per round
- **Database query performance**: < 500ms for stage comparison

### 10.2 User Experience Metrics
- **Timeline interaction**: Users can scrub between stages < 2 seconds
- **Adoption curve clarity**: 80%+ users understand tipping point concept
- **Event configuration**: Users can add custom events < 5 minutes

### 10.3 Scientific Validity Metrics
- **Belief convergence detection**: System detects and warns about excessive convergence
- **Event impact measurement**: Clear delta attribution for each event
- **Confidence interval coverage**: 95% CI actually contains true variance

## 11. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| State snapshot corruption | Low | High | Checksums, versioning, backups |
| Belief update instability | Medium | Medium | Clamping, stability checks, rollback |
| Computational overload | Medium | High | Adaptive resolution, rate limiting |
| User confusion about synthetic nature | High | High | Prominent disclosures, truth metadata |
| Event cascade explosions | Low | Medium | Depth limits, circuit breakers |

## 12. References

- Rogers, E. M. (2003). *Diffusion of Innovations* (5th ed.). Free Press.
- Friedkin, N. E., & Johnsen, E. C. (2011). "Social influence network theory: A sociological examination of small group dynamics." Cambridge University Press.
- Lord, C. G., Ross, L., & Lepper, M. R. (1979). "Biased assimilation and attitude polarization: The effects of prior theories on subsequently considered evidence." *Journal of Personality and Social Psychology*, 37(11), 2098-2109.
- Bass, F. M. (1969). "A new product growth model for consumer durables." *Management Science*, 15(5), 215-227.

---

## Appendix A: Configuration Example

```json
{
  "temporal_simulation_config": {
    "simulation_id": "tsim_abc123",
    "project_id": "proj_xyz789",
    "graph_id": "graph_456def",
    "simulation_requirement": "Model adoption of sustainable packaging initiative over 6 months",
    
    "temporal_stages": [
      {"name": "baseline", "offset_days": 0},
      {"name": "launch", "offset_days": 7},
      {"name": "early_feedback", "offset_days": 30},
      {"name": "market_response", "offset_days": 90},
      {"name": "sustained_adoption", "offset_days": 180}
    ],
    
    "belief_update_config": {
      "enable_bayesian_update": true,
      "enable_social_influence": true,
      "enable_confirmation_bias": true,
      
      "learning_rate_distribution": {
        "mean": 0.4,
        "std": 0.15,
        "min": 0.1,
        "max": 0.8
      },
      
      "social_influence_weight": 0.3,
      "confirmation_bias_strength": 0.5,
      
      "personality_modulation": true
    },
    
    "scheduled_events": [
      {
        "trigger_day": 14,
        "event_type": "user_scheduled",
        "event_class": "competitor_response",
        "description": "Competitor announces similar initiative",
        "effects": {
          "inject_posts": [
            {
              "platform": "twitter",
              "count": 5,
              "agent_archetypes": ["sustainability_advocate", "industry_watcher"],
              "sentiment": "competitive_concern"
            }
          ],
          "modify_beliefs": {
            "topic": "uniqueness",
            "target": "all",
            "shift": -0.15
          }
        }
      },
      {
        "trigger_day": 45,
        "event_type": "external_shock",
        "event_class": "regulatory_support",
        "description": "Government announces tax incentives for sustainable packaging",
        "effects": {
          "modify_beliefs": {
            "topic": "economic_viability",
            "target": "all",
            "shift": +0.25
          },
          "activity_changes": {
            "positive_sentiment": +0.2
          }
        }
      }
    ],
    
    "emergent_event_detection": {
      "enable_viral_detection": true,
      "viral_threshold": 50,
      "enable_polarization_detection": true,
      "polarization_threshold": 0.6,
      "enable_tipping_point_detection": true
    },
    
    "output_config": {
      "generate_adoption_curve": true,
      "generate_confidence_intervals": true,
      "generate_belief_trajectories": true,
      "generate_event_impact_analysis": true
    },
    
    "synthetic_disclosure": true,
    "human_respondent_count": 0,
    "is_forecast": false
  }
}
```

---

**Document Status:** Design Proposal  
**Next Steps:** Review with simulation engineering team, validate computational feasibility, begin Phase 1 implementation.  
**Owner:** Simulation Engineering  
**Reviewers:** Product, Security, Privacy  
**Approval Required:** Architecture Review Board

