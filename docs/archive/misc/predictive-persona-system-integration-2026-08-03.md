---
title: "Predictive Persona System: Integration Architecture"
status: "Design"
version: "1.1.0"
created: "2026-08-03"
owner: "askthepeople-architect"
last_reviewed: "2026-08-03"
---

# Predictive Persona System: Integration Architecture

## Vision

Transform ASKTHEPEOPLE from "plausible synthetic exploration" to "predictive behavioral modeling" by grounding personas in real data, validated behavioral models, and calibrated predictions.

**Target capability:** "If we launch product X at price P, there's a 68% probability of hitting 10K users in month 1, with Competitor Z undercutting by 20% in week 3."

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PREDICTIVE PERSONA ENGINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Phase 1    │  │   Phase 2    │  │   Phase 3    │         │
│  │ Data Ground  │─▶│  Behavioral  │─▶│  Temporal +  │         │
│  │              │  │    Models    │  │  Strategic   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                 │                  │                  │
│         └─────────────────┴──────────────────┘                  │
│                           ▼                                      │
│                  ┌──────────────────┐                           │
│                  │    Phase 4       │                           │
│                  │   Calibration    │                           │
│                  │     Engine       │                           │
│                  └──────────────────┘                           │
│                           │                                      │
│                           ▼                                      │
│                  ┌──────────────────┐                           │
│                  │    Phase 5       │                           │
│                  │   Constraints    │                           │
│                  └──────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Current State Analysis

### Existing Architecture (from codebase)

**Core Components:**
- `backend/app/services/oasis_profile_generator.py` - Generates personas using LLMs
- `backend/app/services/simulation_orchestrator.py` - Runs OASIS simulations
- `backend/app/services/archetype_engine.py` - Creates agent archetypes
- `backend/app/services/graph_builder_service.py` - Builds discourse graphs
- `backend/app/services/validation_engine.py` - Gate 1 validation

**Current Persona Schema (OasisAgentProfile):**
```python
@dataclass
class OasisAgentProfile:
    user_id: str
    user_name: str
    name: str
    bio: str
    persona: str
    karma: Optional[int]
    friend_count: Optional[int]
    follower_count: Optional[int]
    statuses_count: Optional[int]
    age: Optional[int]
    gender: Optional[str]
    mbti: Optional[str]  # ← REPLACE with Big Five
    country: Optional[str]
    profession: Optional[str]
    interested_topics: Optional[List[str]]
    source_entity_uuid: Optional[str]
    source_entity_type: Optional[str]
```

**Gaps:**
- ❌ No real demographic data (all LLM-generated or user-provided)
- ❌ MBTI instead of validated Big Five
- ❌ No behavioral decision models (just LLM next-token prediction)
- ❌ Snapshot at T=0 only (no temporal evolution)
- ❌ Reactive agents (no strategic reasoning)
- ❌ No calibration/validation loop
- ❌ No resource constraints

---

## Phase-by-Phase Integration

### Phase 1: Data Grounding

**New Service:** `backend/app/services/demographic_data_service.py`

**Purpose:** Replace LLM demographic hallucinations with real population distributions

**Data Sources:**
- US Census Bureau API
- Pew Research datasets
- Social media (academic datasets + HackerNews)
- International: UN, World Bank, IPUMS

**Key Functions:**
```python
class DemographicDataService:
    def load_distributions(self, country: str, year: int) -> Dict[str, Distribution]
    def sample_persona_attributes(self, constraints: Dict) -> Dict[str, any]
    def get_realistic_distribution(self, attribute: str, filters: Dict) -> Distribution
    def validate_demographic_coherence(self, persona: Dict) -> bool
```

**Integration Point:** `oasis_profile_generator.py`
```python
# Current (LLM hallucination):
age = llm.generate("realistic age for this persona")

# New (real distribution):
age = demographic_service.sample_persona_attributes(
    country=context.get("country", "US"),
    constraints={"profession": "software engineer"}
)["age"]
```

**Storage:**
- Cache demographic distributions locally (CSV/SQLite)
- Refresh quarterly from API sources
- ~5-20 GB initial data

---

### Phase 2A: Big Five Personality Model — IMPLEMENTED

**CORRECTION to the original plan.** This section previously said to *replace*
`mbti` with Big Five. That was wrong and would have broken every simulation.
The installed OASIS package indexes the key unconditionally:

- `oasis/social_agent/agents_generator.py:461` — `profile["other_info"]["mbti"] = agent_info[i]["mbti"]`
- `oasis/social_platform/config/user.py:97` — interpolates it into the agent system prompt

A missing `mbti` key raises `KeyError` mid-run. MBTI is also referenced in 80+
places across 15 files including `simulation_artifacts.py`.

**What was actually built:** Big Five added *alongside* `mbti`, with the MBTI
code *derived* from traits for interop.

```python
@dataclass
class OasisAgentProfile:
    # ... existing fields ...
    mbti: Optional[str] = None            # RETAINED for OASIS interop
    big_five: Optional[Dict[str, float]] = None   # substantive representation

    @property
    def traits(self): ...                 # -> BigFive | None

    def effective_mbti(self) -> str:      # derives from traits; never None
        ...
```

**Delivered:** `backend/app/services/big_five.py` (+35 tests, all passing).

**Honest scope limits, marked ASSUMPTION in the source:**
- Population mean/SD defaults are reasonable priors, not a specific citable sample.
- Big-Five-to-MBTI mapping is lossy and one-way; Neuroticism has no MBTI
  counterpart and is discarded.
- Trait weightings in `innovativeness()` and the loss-aversion band are design
  choices, not measured effect sizes.

**Not yet done:** deriving traits from source text via NLP. Traits currently
default to population values or are jittered from an archetype. Until text-based
inference lands, `big_five` is `None` for LLM-generated profiles — deliberately,
so we never fabricate a personality that was not source-derived.

---

### Phase 2B: Prospect Theory

**New Service:** `backend/app/services/prospect_theory.py`

**Purpose:** Model real human decision-making (loss aversion, framing, probability weighting)

**Key Functions:**
```python
class ProspectTheory:
    def compute_value(self, outcome: float, reference_point: float, 
                     loss_aversion: float = 2.25) -> float
    def weight_probability(self, p: float) -> float
    def evaluate_prospect(self, options: List[Prospect], 
                         reference_point: float) -> Distribution[Choice]
```

**Integration Point:** Agent decision-making in simulation loop

**Example:**
```python
# Agent choosing between options A and B
options = [
    Prospect(outcomes=[100], probabilities=[0.5], frame="gain"),
    Prospect(outcomes=[50], probabilities=[1.0], frame="gain")
]
reference_point = agent.current_state_value
choice_distribution = prospect_theory.evaluate_prospect(options, reference_point)
# Result: 70% choose certain $50 over 50% chance of $100 (risk aversion in gains)
```

**Personality Modulation:**
- High Neuroticism → stronger loss aversion (coefficient 2.5 vs 2.25)
- High Openness → less probability weighting distortion

---

### Phase 2C: Diffusion of Innovations

**New Service:** `backend/app/services/diffusion_model.py`

**Purpose:** Model how innovations/ideas spread through populations with validated adoption curves

**Key Functions:**
```python
class DiffusionModel:
    def classify_adopter(self, persona: OasisAgentProfile) -> AdopterCategory
    def compute_adoption_curve(self, innovation: Innovation, 
                              population: List[Agent]) -> TimeSeries
    def propagate_influence(self, network: Graph, adopters: Set[Agent], 
                           timestep: int) -> Set[Agent]
```

**Adopter Categories (Rogers):**
- Innovators: 2.5% (high Openness, high income, high education)
- Early Adopters: 13.5% (opinion leaders, high social capital)
- Early Majority: 34% (deliberate, peers must adopt first)
- Late Majority: 34% (skeptical, economic necessity)
- Laggards: 16% (traditional, resistant to change)

**Integration:** Works with Phase 3A (temporal simulation) to model adoption over time

---

### Phase 3A: Multi-Stage Temporal Simulation

**New Service:** `backend/app/services/temporal_simulation.py`

**Purpose:** Simulate "what happens next" with belief updating and events

**Architecture:**
```python
class TemporalSimulation:
    def run_stages(self, initial_state: SimulationState, 
                  stages: List[TimeStage]) -> List[StageSnapshot]
    def update_beliefs(self, agent: Agent, new_info: Information) -> Agent
    def apply_event(self, state: SimulationState, event: Event) -> SimulationState
    def compute_confidence_intervals(self, snapshots: List[StageSnapshot]) -> Intervals
```

**Time Stages:**
- T+0: Initial state
- T+1 week: Early reactions
- T+1 month: Informed opinions
- T+3 months: Behavior change
- T+6 months: New equilibrium

**Belief Updating:**
- Bayesian: `P(belief|new_info) ∝ P(new_info|belief) × P(belief)`
- Social influence: `belief_t+1 = α × own_belief + (1-α) × peer_average`
- Confirmation bias: weight confirming evidence 2x higher

**Integration:** New API endpoint `/api/simulation/temporal`

---

### Phase 3B: Strategic/Game-Theoretic Agents

**New Service:** `backend/app/services/game_theory.py`

**Purpose:** Model competitive dynamics (agents anticipate others' moves)

**Key Functions:**
```python
class GameTheory:
    def compute_nash_equilibrium(self, game: NormalFormGame) -> List[Strategy]
    def form_coalitions(self, agents: List[Agent], 
                       payoff_matrix: Matrix) -> List[Coalition]
    def negotiate(self, agents: List[Agent], issue_space: Space) -> Agreement
    def best_response(self, agent: Agent, others_strategies: Dict) -> Strategy
```

**Use Cases:**
- Market entry: Predict competitor responses
- Policy advocacy: Model coalition formation
- Product pricing: Game-theoretic pricing strategies

**Integration:** Optional mode in simulation (`strategic=True` flag)

---

### Phase 4: Calibration Engine

**New Service:** `backend/app/services/calibration_engine.py`

**Purpose:** Track predictions vs reality, calibrate models

**Database Schema:**
```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY,
    simulation_id UUID,
    prediction_text TEXT,
    outcome_variable TEXT,
    predicted_probability FLOAT,
    confidence_lower FLOAT,
    confidence_upper FLOAT,
    target_date DATE,
    created_at TIMESTAMP
);

CREATE TABLE outcomes (
    id UUID PRIMARY KEY,
    prediction_id UUID REFERENCES predictions(id),
    actual_outcome TEXT,
    actual_value FLOAT,
    reported_at TIMESTAMP,
    user_id UUID
);

CREATE TABLE calibration_models (
    id UUID PRIMARY KEY,
    agent_type TEXT,
    scenario_type TEXT,
    bias_coefficient FLOAT,
    variance_adjustment FLOAT,
    brier_score FLOAT,
    sample_size INT,
    updated_at TIMESTAMP
);
```

**Key Functions:**
```python
class CalibrationEngine:
    def extract_predictions(self, simulation: Simulation) -> List[Prediction]
    def collect_outcome(self, prediction_id: UUID, actual: Outcome) -> void
    def compute_calibration_metrics(self) -> CalibrationMetrics
    def apply_corrections(self, raw_prediction: Prediction) -> CalibratedPrediction
```

**Metrics:**
- **Brier score:** `(predicted_prob - actual_outcome)²` averaged
- **Calibration curve:** Predicted probability vs observed frequency
- **Discrimination:** AUC, separation of outcomes

**Integration:** 
- API: `POST /api/calibration/report_outcome`
- UI: Outcome reporting form in Results page
- Auto-correction: Apply bias adjustments to new predictions

---

### Phase 5: Resource Constraints & Structural Realism

**New Service:** `backend/app/services/constraint_engine.py`

**Purpose:** Model what actors CAN do, not just what they want

**Constraint Types:**
```python
@dataclass
class Constraint:
    type: str  # "budget", "time", "information", "legal", "social"
    value: float
    enforcement_level: str  # "hard", "soft", "probabilistic"
    source: str

@dataclass
class ConstrainedAgent(OasisAgentProfile):
    constraints: List[Constraint]
    dependencies: List[UUID]  # agent IDs this agent depends on
```

**Key Functions:**
```python
class ConstraintEngine:
    def check_feasibility(self, agent: Agent, action: Action) -> FeasibilityResult
    def evaluate_cost(self, agent: Agent, action: Action) -> Cost
    def resolve_dependencies(self, agents: List[Agent], 
                            action_plan: Plan) -> ExecutionOrder
    def model_information_asymmetry(self, agents: List[Agent], 
                                   knowledge_graph: Graph) -> InformationStates
```

**Examples:**
- Budget: Activist group with $10K can't run TV ads
- Time: Product launch deadline constrains options
- Information: Not all agents know about regulatory change
- Legal: Can't do X without approval from authority Y
- Social: Reputation costs for controversial actions

**Integration:** Constraint checking in agent action selection

---

## Data Flow Architecture

```
User Input (decision + source material)
    ↓
Phase 1: Sample from real demographic distributions
    ↓
Generate personas with Big Five (Phase 2A)
    ↓
If temporal simulation:
    ↓
    T=0: Initial simulation with Prospect Theory (Phase 2B)
    ↓
    Classify adopters (Phase 2C: Diffusion)
    ↓
    T=1 week: Update beliefs, propagate adoption
    ↓
    T=1 month: Apply events, strategic responses (Phase 3B)
    ↓
    T=3 months: Continue evolution
    ↓
    T=6 months: Final state
    ↓
Check constraints throughout (Phase 5)
    ↓
Extract predictions (Phase 4: Calibration)
    ↓
Generate report with confidence intervals
    ↓
Later: User reports actual outcome → calibrate models
```

---

## Implementation Roadmap

### Sprint 1-4: Phase 1 (Data Grounding) — 4 weeks
- Week 1: Census API integration, data ingestion
- Week 2: Social media datasets (academic), HackerNews API
- Week 3: Demographic sampling service, integration with profile generator
- Week 4: Testing, validation, documentation

**Deliverables:**
- `demographic_data_service.py`
- `social_data_service.py`
- Real distribution sampling in persona generation

### Sprint 5-7: Phase 2A (Big Five) — 3 weeks
- Week 1: Schema migration, Big Five generation algorithms
- Week 2: Text-to-trait models, demographic correlations
- Week 3: Integration, testing, behavioral mappings

**Deliverables:**
- Updated `OasisAgentProfile` schema
- Big Five generation in `oasis_profile_generator.py`
- Documentation on trait → behavior mappings

### Sprint 8-11: Phase 2B (Prospect Theory) — 4 weeks
- Week 1-2: Prospect Theory implementation (value function, probability weighting)
- Week 3: Integration with agent decision-making
- Week 4: Testing against experimental results, calibration

**Deliverables:**
- `prospect_theory.py`
- Agent decision loop using Prospect Theory
- Validation against Kahneman/Tversky experiments

### Sprint 12-15: Phase 2C (Diffusion) — 4 weeks
- Week 1-2: Rogers model implementation, adopter classification
- Week 3: Network propagation algorithms
- Week 4: Integration with temporal simulation, testing

**Deliverables:**
- `diffusion_model.py`
- Adopter classification for personas
- Adoption curve computation

### Sprint 16-20: Phase 3A (Temporal) — 5 weeks
- Week 1-2: Multi-stage simulation architecture
- Week 3: Belief updating algorithms
- Week 4: Event system
- Week 5: Integration, UI timeline component

**Deliverables:**
- `temporal_simulation.py`
- API: `/api/simulation/temporal`
- Frontend timeline visualization

### Sprint 21-25: Phase 3B (Strategic) — 5 weeks
- Week 1-2: Nash equilibrium solver
- Week 3: Coalition formation algorithms
- Week 4: Negotiation models
- Week 5: Integration, testing on game theory scenarios

**Deliverables:**
- `game_theory.py`
- Strategic mode in simulations
- Competitive scenario modeling

### Sprint 26-32: Phase 4 (Calibration) — 7 weeks
- Week 1-2: Prediction extraction, database schema
- Week 3-4: Outcome tracking UI, API
- Week 5-6: Calibration algorithms (Brier score, correction models)
- Week 7: Integration, dashboard

**Deliverables:**
- `calibration_engine.py`
- Database tables, API endpoints
- Outcome reporting UI
- Accuracy dashboard

### Sprint 33-37: Phase 5 (Constraints) — 5 weeks
- Week 1-2: Constraint modeling, schema extension
- Week 3-4: Feasibility checking, dependency resolution
- Week 5: Integration, testing

**Deliverables:**
- `constraint_engine.py`
- Constrained agent profiles
- Feasibility checking in simulation loop

**Total Timeline: 37 weeks (~9 months)**

---

## Cost Estimates

### Development Costs
- 9 months × 1 senior engineer = ~$120K-180K salary
- OR: 9 months × contracted dev = ~$80K-150K

### Infrastructure Costs (monthly)
- Demographic data storage: $50-200
- Social media data processing: $100-500
- Increased LLM usage (more sophisticated agents): $500-2000
- Database (prediction/outcome tracking): $100-300
- **Total: $750-3000/month**

### Data Acquisition Costs
- Census/Pew/UN: Free
- Social media academic datasets: Free
- HackerNews API: Free
- Optional Reddit Academic: $0-500/month if approved
- **Total: $0-500/month**

**Grand Total Operating Cost: $750-3500/month**

---

## Success Metrics

### Technical Metrics
- **Persona authenticity:** Demographic distributions match real Census data within 5%
- **Behavioral validity:** Prospect Theory tests match Kahneman/Tversky results within 10%
- **Adoption accuracy:** Diffusion curves match historical adoption (smartphones, etc.) within 15%
- **Calibration:** 70% confidence predictions are correct 65-75% of the time (Brier score <0.2)

### Product Metrics
- **User validation rate:** 30%+ of users report outcomes back
- **Decision impact:** 50%+ of users say simulation influenced their decision
- **Accuracy perception:** Users rate predictions 7+/10 for realism
- **Conversion:** 20%+ of simulations lead to real research (product truth maintained)

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users treat as predictive, skip real research | High | High | Mandatory disclaimers, "validate with people" prompts |
| Calibration sample too small | High | Medium | Start with priors from research literature, gradual improvement |
| Computational cost explodes | High | Medium | Tiered depth (quick/standard/deep), cost warnings |
| Demographic data becomes stale | Medium | Low | Quarterly refresh from APIs |
| Game theory intractable | Medium | Low | Approximation algorithms, limit game size |
| False confidence from complexity | High | High | Always show confidence intervals, not point estimates |

---

## Next Steps

1. **Validate with stakeholders:** Is 9-month timeline acceptable? Budget approved?
2. **Start Phase 1 immediately:** Census/demographic integration is foundational
3. **Parallel track:** Social media data (Agent 2 completed) can proceed independently
4. **Defer Phase 3B:** Strategic/game theory is lowest priority — focus on data grounding + behavioral models first
5. **Build calibration ASAP:** Need feedback loop early to measure if this is working

---

## Conclusion

This architecture transforms ASKTHEPEOPLE from synthetic exploration to predictive behavioral modeling through:
1. **Real data grounding** (not LLM hallucinations)
2. **Validated behavioral models** (Prospect Theory, Diffusion, Big Five)
3. **Temporal evolution** (what happens next, not just T=0)
4. **Strategic reasoning** (competitive dynamics)
5. **Calibration loop** (measure accuracy, improve over time)

**Timeline:** 9 months, ~$150K development + $750-3500/month operating cost

**ROI:** Transform from "thought exercise" to "strategic advantage that beats consultants"

**Critical path:** Phase 1 (data) → Phase 2A/B (Big Five + Prospect Theory) → Phase 4 (calibration) → others in parallel
