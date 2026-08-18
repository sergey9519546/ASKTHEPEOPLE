# FORENSIC CODE AUDIT: ASKTHEPEOPLE SIMULATION SYSTEM
**Date:** 2026-08-18  
**Commit:** `8b616dc7fa02eeed5ada8c51998d8b197be28f8d` (main)  
**Auditor:** Kilo (forensic trace of actual implementation)

---

## EXECUTIVE SUMMARY

**What this application actually is architecturally:**
A **Zep-backed synthetic scenario explorer** that builds knowledge graphs from source documents, generates fictional agent profiles, runs OASIS-based Twitter/Reddit simulations as subprocesses, produces synthetic observation logs, and generates structured reports using ReACT agents. The system is explicitly designed around **truth contracts** that label all outputs as synthetic (0 human respondents, not forecasts, not public opinion).

**What it genuinely does today:**
1. **Ingests source text** → builds Zep graphs with LLM-proposed ontologies (entities/edges)
2. **Generates fictional agent profiles** from graph entities (Big Five + MBTI, rule-based or LLM-enhanced)
3. **Constructs simulation configs** via LLM (time, events, agent activity, platforms) — OR deterministic configs from human-reviewed "decision lenses"
4. **Runs OASIS simulations** as subprocesses (`run_parallel_simulation.py`) producing SQLite traces + JSONL action logs
5. **Generates ReACT-based reports** from simulation observations + graph retrieval
6. **Allows post-run interaction** via chat (report Q&A, fictional profile dialogue, group comparisons, opinion maps)

**Does it behave like the specified system?**
**Partially — but with critical architectural gaps and dead code paths.** The "World Construction → Environment Setup → Simulation → Analysis → Deep Interaction" pipeline **exists end-to-end** but key stages have significant limitations, and the legacy simulation pathway is **completely disabled** in production.

---

## CAPABILITY CLASSIFICATION MATRIX

| Capability | Classification | Evidence |
|------------|---------------|----------|
| **1. WORLD CONSTRUCTION** | | |
| Ingest source material | **IMPLEMENTED** | `graph_builder.py:82-167` - builds Zep graphs from text chunks with ontology |
| Extract entities/events/facts/relationships | **IMPLEMENTED** | `ontology_generator.py` proposes schema; `zep_entity_reader.py:235-351` filters nodes by labels |
| Construct graph/world model | **IMPLEMENTED** | Zep Cloud graphs with custom ontologies; `GraphInfo` with node/edge counts |
| Retrieval / GraphRAG | **IMPLEMENTED** | `zep_tools.py` provides `insight_forge`, `panorama_search`, `quick_search` |
| Individual + collective memory | **WEAK** | Graph stores entities; simulation observations stored separately in `actions.jsonl` + `simulation_observation_store.py`; no cross-run memory |
| **2. ENVIRONMENT SETUP** | | |
| Create agent personas | **IMPLEMENTED** | `oasis_profile_generator.py` produces `OasisAgentProfile` with bio, persona, Big Five, MBTI |
| Assign goals/beliefs/incentives/relationships | **PARTIAL** | `decision_lens_generator.py` produces functional lenses (goals, constraints, incentives, access conditions) — but legacy `AgentActivityConfig` has `stance`, `sentiment_bias`, `influence_weight` that are **neutral fictional defaults** |
| Configure environmental rules | **IMPLEMENTED** | `simulation_config_generator.py` produces `TimeSimulationConfig`, `EventConfig`, `PlatformConfig` |
| Natural-language → simulation config | **IMPLEMENTED** | LLM step-by-step generation in `simulation_config_generator.py:292-451` OR deterministic from decision lenses (`generate_from_decision_lenses`) |
| **3. SIMULATION** | | |
| Run multiple autonomous agents | **IMPLEMENTED** | `run_parallel_simulation.py` uses OASIS `agent_graph` with `LLMAction` per agent per round |
| Persistent agent/world state | **PARTIAL** | SQLite per-platform DBs + `actions.jsonl` + `run_state.json`; **no graph write-back** (explicitly rejected in `simulation.py:112-118`) |
| Agents interact with each other | **IMPLEMENTED** | OASIS handles post/like/reply/follow; network topology applied via `network_topology.py` |
| Update memory/environment over time | **PARTIAL** | Reflections every N rounds (`apply_reflection_round`) + homophily rewiring; **graph not updated** |
| Propagate consequences | **IMPLEMENTED** | Scheduled events (`apply_scheduled_events`), bootstrap posts, viral diffusion via OASIS |
| Steps/time progression/repeated/parallel/branching | **IMPLEMENTED** | Rounds with simulated hours; parallel Twitter+Reddit; forking via `/fork` endpoint (`branching_routes.py`) |
| **4. POST-SIMULATION ANALYSIS** | | |
| Analyze histories/state/interactions | **IMPLEMENTED** | `report_agent.py` ReACT agent searches observations + graph |
| Identify patterns/emergence/uncertainty | **PARTIAL** | Report sections cover paths, divergence, uncertainty; but **no quantitative analysis** of emergence |
| Reports grounded in stored results | **IMPLEMENTED** | All report claims require tool retrieval; `simulation_observations` tool searches `actions.jsonl` |
| **5. DEEP INTERACTION** | | |
| Interact with simulated agents post-run | **IMPLEMENTED** | `Step5Interaction.vue` — chat with report agent OR fictional profiles via `askSyntheticProfiles` |
| Preserve agent memories/state | **PARTIAL** | Profiles + decision lenses + observations persist; **no continued simulation** for follow-ups |
| Follow-up questions about events/decisions | **IMPLEMENTED** | `chatWithReport` (report Q&A) + `askSyntheticProfiles` (fictional dialogue) |
| Interrogate report/analysis | **IMPLEMENTED** | Chat mode 1 ("Explain the report") with retrieval tools |
| Modify assumptions / rerun | **PARTIAL** | Forking creates new simulation from turn N; **no in-place config mutation** |

---

## CRITICAL FINDINGS

### 1. LEGACY SIMULATION PATH IS DEAD CODE (`simulation_manager.py:349-619`)
```python
# Line 349-352: IMMEDIATELY RAISES if DECISION_LENS_V1_ENABLED is False
if not Config.DECISION_LENS_V1_ENABLED:
    raise DecisionLensPreparationError("decision_lens_preparation_unavailable")
return self._prepare_decision_lens_review(...)  # Returns here

# Lines 386-619: COMPLETELY UNREACHABLE - legacy profile generation, config generation, preflight
```
**The entire legacy pipeline (entity reading → profile generation → LLM config generation) is unreachable.** Production only runs the **decision-lens path** which requires human review before execution.

### 2. NO GRAPH WRITE-BACK FROM SIMULATION (Explicit Design Decision)
```python
# simulation.py:112-118
raise InputPolicyError(
    "synthetic_graph_writes_unsupported",
    "Writing generated activity to a graph is unsupported. Generated activity remains in the simulation observation store."
)
```
**Consequence:** No cumulative learning across runs. Each simulation is isolated. The "collective memory" requirement is **NOT IMPLEMENTED**.

### 3. AGENT PERSONAS ARE NOT BEHAVIORALLY RICH
- `AgentActivityConfig` fields (`stance`, `sentiment_bias`, `conflict_tolerance`, `authority_sensitivity`, `novelty_seeking`, `influence_weight`) are **all neutral defaults** (`control_assumption_basis: "neutral_fictional_default"`)
- Big Five traits only attached if `ENABLE_TRAIT_INFERENCE=True` (default **off**) and spans verify — otherwise `ISTJ` placeholder
- Decision lenses are **functional** (goals, constraints, incentives) not psychological — no beliefs, no demographics, no identity narrative

### 4. OASIS IS THE SIMULATION ENGINE — NOT CUSTOM
The simulation runs **OASIS (oasis-ai)** via subprocess:
- `run_parallel_simulation.py` creates `oasis.make(platform=TWITTER/REDDIT)`
- Agents receive `LLMAction()` — OASIS decides what they do
- Actions logged to SQLite + `actions.jsonl` via `action_logger.py`
- **No custom agent loop, no custom decision logic** — it's OASIS with configured action sets

### 5. PREFLIGHT GATE IS THE EXECUTION CONTRACT
`simulation_preflight.py:170-351` `assert_decision_lens_execution_admission()` verifies:
- Decision lens artifact + review exist and match
- Runtime adapters match exactly
- Config matches deterministic regeneration from lenses
- No prohibited identity keys in config
- Model resolution valid
- **This is the "go/no-go" gate — simulation cannot start without human-approved decision lenses**

### 6. REPORT AGENT IS ReACT WITH TOOLS — NOT ANALYTICAL
`report_agent.py` uses 5 tools (`insight_forge`, `panorama_search`, `quick_search`, `simulation_observations`, `interview_agents`) with:
- Mandatory 3-5 tool calls per section
- Reasoning scaffold stripping (`strip_reasoning_scaffold`) to remove CoT from output
- Truth boundary prompts forbidding forecast/public-opinion language
- **No statistical analysis, no causal inference, no quantitative emergence detection**

---

## USE CASE SUITABILITY

| Use Case | Viability | Gaps |
|----------|-----------|------|
| **Finance/investment simulation** | **WEAK** | No quantitative models, no market mechanics, no portfolio simulation |
| **Policy/public-opinion forecasting** | **MISREPRESENTED** | Explicitly NOT a forecast; 0 human respondents; synthetic only |
| **Crisis/PR simulation** | **PARTIAL** | Can simulate narrative diffusion on Twitter/Reddit; no media ecosystem, no stakeholder mapping |
| **Marketing strategy testing** | **PARTIAL** | Can test message diffusion; no conversion funnels, no segment sizing, no ROI |
| **Fictional world/character simulation** | **IMPLEMENTED** | Core strength — generates fictional personas, runs social dynamics, produces narratives |
| **Academic social-behavior simulation** | **WEAK** | No calibrated parameters, no validation framework, no reproducible experimental design |

---

## WHAT'S MORE ADVANCED THAN SPEC

1. **Truth Contract System** — Every synthetic surface carries machine-enforced disclosure metadata (`claim_boundary.py`)
2. **Decision Lens Review Gate** — Human-in-the-loop approval before execution with cryptographic artifact/review binding
3. **Runtime Control Plane** — Leases, fencing tokens, heartbeats, idempotency keys, durable stop/pause/resume (`runtime_control_store.py`, `run_attempt_store.py`)
4. **Instruction Integrity Guard** — Verifies agent system prompts unchanged before/after every OASIS step (`instruction_integrity.py`)
5. **Forking with Lineage** — Counterfactual branching preserving parent simulation state (`simulation_fork_service.py`)
6. **Trait Inference with Span Verification** — Big Five only attached when source text spans support them (`trait_inference.py`)
7. **Run Manifest with Reproducibility Disclosure** — Documents non-determinism sources (`simulation_preflight.py:354-418`)

---

## MAJOR MISSING CAPABILITIES

| Missing Capability | Location | Impact |
|-------------------|----------|--------|
| Cross-run memory / learning | N/A | Each simulation isolated; no cumulative knowledge |
| Graph write-back from simulation | Explicitly forbidden | No world evolution across runs |
| Quantitative emergence detection | `report_agent.py` | Only narrative synthesis; no metrics |
| Calibrated behavioral parameters | `simulation_config_generator.py` | All controls are "neutral fictional defaults" |
| Multi-simulation comparison | `simulation.py:compare` routes exist but thin | No statistical comparison, no ensemble analysis |
| Causal inference / counterfactuals | Forking exists but no analysis | Fork creates new run; no diff analysis |
| Real-time human-in-the-loop during run | IPC supports interview/inject | No "steering" of running simulation |
| Population-level statistics | `diffusion_model.py` exists but not wired into config | Rogers curve computed but not used for activation |

---

## ARCHITECTURAL VERDICT

**The system is a well-engineered synthetic scenario explorer with strong truth-contract discipline, but it is NOT a general-purpose simulation platform.**

- **Core loop works**: Source → Graph → Profiles → Config → OASIS Run → Observations → Report → Interaction
- **Production path is narrow**: Decision-lens review required; legacy auto-config disabled
- **Simulation engine is OASIS**: Not custom; behavior determined by OASIS internals + action set config
- **No learning/accumulation**: Each run independent; graph static; no cross-run memory
- **Best suited for**: Fictional world exploration, narrative diffusion studies, scenario planning where outputs are explicitly hypotheses for human validation

**Closest to spec:** Steps 1, 2 (decision-lens path), 3 (execution), 4 (report), 5 (interaction) — all present but constrained by truth contracts.

**Furthest from spec:** Collective memory, behavioral richness, calibrated parameters, quantitative analysis, forecasting/forecasting-adjacent use cases (explicitly forbidden).