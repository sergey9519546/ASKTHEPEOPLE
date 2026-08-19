---
title: "Scenario Rules & Participation Protocol"
status: "Normative Reference"
version: "1.0.0"
created: "2026-08-18"
owner: "askthepeople-architect + askthepeople-orchestration-engineer + askthepeople-ai-eval-steward"
last_reviewed: "2026-08-18"
applies_to: "all OASIS/CAMEL simulation runs, all synthetic decision lens deployments, all generated paths"
---

# Scenario Rules & Participation Protocol

> **Document authority.** These rules govern how synthetic decision lenses participate in simulation runs. They are **not** rules for human participants. They define the computational contract between the scenario engine and the generated lenses.

> **Product Truth Contract compliance:** This protocol ensures no simulation run can be mistaken for human research, population measurement, or behavioral prediction.

---

## Channel Architecture

### Communication Channels

| Channel ID | Purpose | Participants | Modality | Latency Budget |
|---|---|---|---|---|
| `scenario:brief` | Decision context, assumptions, uncertainties | All lenses (broadcast) | Structured JSON | <100ms |
| `scenario:lens_declaration` | Each lens declares its posture | Each lens → Engine | Structured JSON | <500ms |
| `scenario:action_proposal` | Lens proposes synthetic action | Lens → Engine | Structured JSON | <1s |
| `scenario:action_resolution` | Engine resolves conflicts, emits canonical action | Engine → All lenses | Structured JSON | <2s |
| `scenario:state_update` | World state delta after action | Engine → All lenses | Structured JSON | <500ms |
| `scenario:disconfirmation_check` | Engine requests disconfirmation evidence | Engine → Specific lenses | Structured JSON | <1s |
| `scenario:path_branching` | Critical uncertainty state selection | Engine → All lenses | Structured JSON | <1s |
| `scenario:run_termination` | Stop condition met | Engine → All lenses | Structured JSON | <100ms |

### Channel Invariants

- **No peer-to-peer lens communication** — All interaction mediated by engine
- **No persistent memory across rounds** — Lenses receive full context each round (stateless)
- **No private channels** — All declarations visible to all lenses (transparency)
- **Engine is authoritative** — Engine resolves conflicts, enforces rules, emits canonical state

---

## Timing Rules

### Simulation Clock

```ts
interface SimulationClock {
  totalSimulatedHours: number;        // From TimeSimulationConfig (default: 72)
  minutesPerRound: number;            // From TimeSimulationConfig (default: 60)
  currentRound: number;               // 0-indexed
  currentSimulatedHour: number;       // currentRound * minutesPerRound / 60
  peakHours: number[];                // High-activity windows
  offPeakHours: number[];             // Low-activity windows
}
```

### Round Structure

Each round executes in **strict sequence**:

1. **Brief/Context Distribution** (Round 0 only, or on path branch)
   - Engine broadcasts `scenario:brief` with decision, assumptions, uncertainties, lens roster

2. **Lens Posture Declaration** (All rounds)
   - Each lens emits `scenario:lens_declaration`:
     ```json
     {
       "lensId": "GP-01",
       "round": 3,
       "posture": "engaged | observing | constrained | blocked",
       "activeConstraints": ["budget_ceiling", "deadline"],
       "informationGaps": ["vendor_roadmap_q4"],
       "proposedFocus": "integration_feasibility"
     }
     ```

3. **Action Proposal Window** (All rounds)
   - Engaged lenses propose synthetic actions via `scenario:action_proposal`:
     ```json
     {
       "lensId": "GP-01",
       "round": 3,
       "actionId": "SA-047",
       "actionType": "post | comment | share | react | query | escalate | defer",
       "content": "Structured synthetic action content",
       "targetEntities": ["entity-uuid-1", "entity-uuid-2"],
       "rationale": "Bounded rationale referencing lens constraints/incentives",
       "confidence": 0.73,
       "disconfirmationTriggers": ["vendor_announces_breaking_change", "budget_reduced_15pct"]
     }
     ```

4. **Engine Resolution** (All rounds)
   - Engine applies conflict resolution (see **Conflict Resolution** below)
   - Emits canonical `scenario:action_resolution` with selected actions

5. **World State Update** (All rounds)
   - Engine computes state delta, emits `scenario:state_update`
   - Includes: new posts, reactions, metric shifts, entity state changes

6. **Disconfirmation Check** (Every N rounds, configurable)
   - Engine queries lenses with `scenario:disconfirmation_check`
   - Lenses must respond with specific conditions that would invalidate their posture

7. **Path Branching Evaluation** (At critical uncertainty points)
   - Engine evaluates uncertainty coverage via `scenario:path_branching`
   - May spawn parallel path executions

8. **Termination Check** (All rounds)
   - Engine evaluates stop conditions (see **Stop Conditions** below)
   - Emits `scenario:run_termination` if met

### Activity Windows

Lenses are **only active** during their configured `activeHours` (from `AgentActivityConfig`):

```json
{
  "activeHours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
  "peakHours": [19, 20, 21, 22],
  "offPeakHours": [0, 1, 2, 3, 4, 5],
  "peakMultiplier": 1.5,
  "offPeakMultiplier": 0.05
}
```

Outside active hours: lens emits `posture: "observing"` with zero actions.

---

## Participation Rules

### Lens Eligibility

A lens participates in a run **iff**:

1. `status === "approved"` in profile registry
2. Lens `id` is in the run's `generatedProfileIds` array
3. Lens has at least one `decisionCriterion` relevant to the decision
4. Lens is not excluded by `excludedInferences` conflicting with run assumptions

### Lens Posture States

| Posture | Meaning | Action Capacity |
|---|---|---|
| `engaged` | Actively proposing actions per its constraints/incentives | Full (per `postsPerHour`, `commentsPerHour`) |
| `observing` | Monitoring but not acting (outside active hours, or no relevant action) | Zero actions; receives state updates |
| `constrained` | Wants to act but blocked by `accessConditions` or `switchingCosts` | Zero actions; emits `blockedBy` in declaration |
| `blocked` | Hard stop — `switchingCosts` exceed threshold or `constraints` violated | Zero actions; emits `blockReason`; may trigger path branch |

### Action Proposal Rules

Each lens may propose **up to** its configured rate per hour:

```json
{
  "postsPerHour": 1.0,
  "commentsPerHour": 2.0,
  "activityLevel": 0.5  // Scales both rates
}
```

**Per-round maximum** = `ceil(rate * minutesPerRound / 60 * activityLevel)`

Actions **MUST** include:
- `rationale` referencing specific lens fields (constraints, incentives, informationConditions)
- `disconfirmationTriggers` — specific, measurable conditions that would invalidate the action
- `confidence` in [0.0, 1.0] — lens's own assessment of action coherence

Actions **MUST NOT**:
- Claim human experience ("I felt", "In my experience", "As a [demographic]")
- Predict outcomes ("This will cause", "Users will respond")
- Reference unapproved assumptions
- Use first-person narrative voice

### Information Asymmetry Enforcement

Lenses **only know** what their `informationConditions` declare:

- If `informationConditions` lacks "vendor_roadmap", lens cannot propose actions requiring that knowledge
- Engine validates each action against lens's declared `informationConditions`
- Violations → action rejected, lens moves to `constrained` posture

### Incentive Alignment

Each action's `rationale` **must** trace to at least one declared `incentive`:

```json
{
  "incentives": ["on_time_delivery", "technical_debt_reduction"],
  "action": { "rationale": "Proposing phased integration to meet deadline (on_time_delivery) while isolating legacy billing (technical_debt_reduction)" }
}
```

Actions without incentive trace → rejected.

---

## Conflict Resolution

### Conflict Types

| Type | Detection | Resolution |
|---|---|---|
| **Resource contention** | Multiple lenses target same entity with incompatible actions | Engine applies `influenceWeight` priority; lower weight deferred |
| **Constraint violation** | Action contradicts lens's own `constraints` | Action rejected; lens moves to `constrained` |
| **Information overreach** | Action requires knowledge outside `informationConditions` | Action rejected; lens moves to `constrained` |
| **Incentive misalignment** | Action contradicts declared `incentives` | Action rejected; lens moves to `constrained` |
| **Narrative contradiction** | Actions create logically inconsistent world state | Engine selects maximally coherent subset; logs `CONFLICT_ACROSS_PATHS` |
| **Stalemate** | No lens can act (all `constrained` or `blocked`) | Engine triggers `scenario:disconfirmation_check`; if unresolved, emits `run_termination: INCOMPLETE` |

### Resolution Precedence

1. **Hard constraints** (budget, deadline, law, physics) — never violated
2. **Lens `switchingCosts`** — actions exceeding threshold require explicit override
3. **`influenceWeight`** — higher weight wins resource contention
4. **`activityLevel`** — more active lenses get priority in tied contention
5. **Round-robin** — final tiebreaker for fairness

### Conflict Audit Trail

Every conflict resolution emits a `CONFLICT` record:

```json
{
  "type": "CONFLICT",
  "subtype": "RESOURCE_CONTENTION | CONSTRAINT_VIOLATION | ...",
  "round": 12,
  "involvedLenses": ["GP-01", "GP-04"],
  "conflictingActions": ["SA-047", "SA-052"],
  "resolution": "GP-01 action selected (influenceWeight 1.2 > 0.8)",
  "disconfirmationTrigger": "If GP-04's constraint changes, re-evaluate at round 15"
}
```

---

## Stop Conditions

The engine **MUST** terminate with `run_termination` when ANY condition is met:

### Completion Conditions (→ `COMPLETED`)

1. **Clock exhausted** — `currentSimulatedHour >= totalSimulatedHours`
2. **Coverage satisfied** — All critical uncertainty states covered by at least one path; all approved lenses have acted in at least 3 rounds
3. **Stability reached** — No new considerations, conflicts, or missing information in last 5 rounds; state delta < threshold
4. **Decision coherence** — At least one path has zero `DISCONFIRMING_CONDITION` and all `VALIDATION_QUESTIONS` assigned

### Incomplete Conditions (→ `INCOMPLETE`)

1. **Stalemate** — All lenses `blocked` or `constrained` for 3 consecutive rounds
2. **Assumption collapse** — A `BLOCKING` assumption is rejected during run
3. **Source conflict unresolved** — Material `conflicting_source` flag persists without path coverage
4. **Validator failure** — Truth, provenance, or safety validator fails
5. **Provider failure** — LLM returns malformed output after retry budget exhausted

### Prohibited Conditions (→ `BLOCKED`)

1. **Prohibited use** — Intended use matches prohibited domain (per Methodology §Required decision intake)
2. **Predictive demand** — Request asks for probability, forecast, or public opinion measure
3. **Privacy violation** — Source material contains PII not authorized for synthesis
4. **Safety violation** — Generated content violates safety policy

---

## Path Branching Protocol

### Trigger Points

Path branching occurs at **declared critical uncertainty points** from the run configuration:

```json
{
  "criticalUncertainties": [
    {
      "id": "U-01",
      "statement": "Availability of live enrollment support",
      "states": [
        { "id": "U-01-A", "label": "Reliably available" },
        { "id": "U-01-B", "label": "Intermittent" },
        { "id": "U-01-C", "label": "Unavailable at decision moment" }
      ],
      "branchAtRound": 6
    }
  ]
}
```

### Branching Mechanics

1. At `branchAtRound`, engine pauses main path
2. For each uncertainty state, engine spawns **parallel sub-run** with:
   - Cloned world state at branch point
   - Modified `scenario:brief` with selected uncertainty state
   - Same lens roster (lenses re-declare posture under new condition)
3. Sub-runs execute independently per **Timing Rules**
4. Engine aggregates results via **Cross-Path Analysis** (see below)

### Path Independence

- Sub-runs **do not communicate**
- Lenses **re-evaluate posture** from scratch in each sub-run
- No shared state, no cross-contamination
- Each sub-run produces independent `PossiblePath` artifact

---

## Cross-Path Analysis

After all sub-runs complete, engine performs:

### Classification Matrix

| Classification | Criteria | Output |
|---|---|---|
| `RECURS_WITHIN_THIS_SYNTHETIC_RUN` | Consideration appears in ≥2 paths with same valence | `recurringConsiderations[]` |
| `ASSUMPTION_DEPENDENT` | Consideration appears only in paths sharing an assumption | `assumptionDependentConsiderations[]` with assumption ID |
| `CONFLICTS_ACROSS_PATHS` | Paths produce contradictory considerations | `crossPathConflicts[]` |
| `MISSING_INFORMATION` | Information gap appears in all paths | `universalMissingInformation[]` |
| `NEEDS_HUMAN_VALIDATION` | Validation question appears in all paths | `universalValidationQuestions[]` |

### Prohibited Outputs

The analysis **MUST NOT** produce:
- Probabilities, likelihoods, confidence scores
- "Majority", "consensus", "winning path"
- "Evidence supports", "validated by"
- Any language implying external validity

### Required Output Format

```json
{
  "recurringConsiderations": [
    { "statement": "...", "paths": ["P-01", "P-03"], "category": "risk" }
  ],
  "assumptionDependentConsiderations": [
    { "statement": "...", "paths": ["P-02"], "assumptionId": "A-04" }
  ],
  "crossPathConflicts": [
    { "pathA": "P-01", "pathB": "P-04", "conflict": "..." }
  ],
  "universalMissingInformation": ["..."],
  "universalValidationQuestions": ["..."]
}
```

---

## Disconfirmation Protocol

### Per-Lens Disconfirmation

Every lens **must** declare `disconfirmationTriggers` for each action and in its posture declaration.

Engine queries via `scenario:disconfirmation_check` every `disconfirmationInterval` rounds (default: 5).

Lens responds with:

```json
{
  "lensId": "GP-01",
  "round": 10,
  "disconfirmingConditions": [
    "Vendor announces breaking API change before round 15",
    "Budget reduced by >15% before deadline",
    "Key team member (DevOps) becomes unavailable"
  ],
  "triggered": false,
  "evidenceRequired": "Vendor release notes; budget amendment; HR notification"
}
```

If `triggered: true`, lens moves to `blocked` posture and may trigger path branch.

### Cross-Path Disconfirmation

At analysis phase, engine identifies:

- Conditions that would **invalidate entire path families**
- Assumptions that, if false, collapse multiple paths
- Missing information that, if resolved, would eliminate path divergence

These become `DISCONFIRMING_CONDITION` records in the `PossiblePath` schema.

---

## Provenance & Audit Requirements

Every simulation artifact carries immutable provenance:

### Run Manifest (Immutable)

```json
{
  "runId": "RUN-2026-08-18-001",
  "decisionVersion": "DEC-2026-08-15-v3",
  "sourceAssetHashes": ["sha256:...", "sha256:..."],
  "acceptedStartingConditions": ["SC-01", "SC-03"],
  "acceptedAssumptions": ["A-01", "A-02", "A-04"],
  "selectedUncertainties": ["U-01", "U-02"],
  "approvedLenses": ["GP-01", "GP-02", "GP-07", "GP-24"],
  "scenarioRules": "docs/research/scenario-rules.md@v1.0.0",
  "methodologyVersion": "1.1.0",
  "promptRegistryVersions": { "profile_generation": "v2.3", "config_generation": "v1.7" },
  "modelConfig": { "provider": "openai", "model": "gpt-4.1", "temperature": 0.7 },
  "randomSeeds": { "numpy": 42, "python": 12345, "simulation": 999 },
  "concurrencyStrategy": "sequential_rounds",
  "schemaVersions": { "profile": "1.0", "config": "1.0", "path": "1.0" },
  "timestamps": { "started": "...", "completed": "..." },
  "contentHashes": { "brief": "sha256:...", "profiles": "sha256:...", "paths": "sha256:..." }
}
```

### Per-Action Provenance

```json
{
  "actionId": "SA-047",
  "lensId": "GP-01",
  "round": 3,
  "origin": "SYNTHETIC_GENERATED",
  "epistemicRole": "PATH_STEP",
  "assumptionBasis": ["A-01", "A-04"],
  "uncertaintyStateBasis": ["U-01-A"],
  "profileConstraintsUsed": ["budget_ceiling", "deadline"],
  "profileIncentivesUsed": ["on_time_delivery"],
  "informationConditionsMet": ["current_system_internals"],
  "disconfirmationTriggers": ["vendor_breaking_change", "budget_reduction"],
  "modelCall": {
    "promptId": "action_proposal",
    "promptVersion": "v1.2",
    "promptSha256": "...",
    "systemPromptSha256": "...",
    "outputSha256": "...",
    "temperature": 0.7
  }
}
```

---

## Validation Gates (Pre-Run, In-Run, Post-Run)

### Pre-Run (Gate 0 — MUST PASS)

- [ ] Decision intake complete (Methodology §Required decision intake)
- [ ] All `acceptedAssumptions` have `status: "ACCEPTED_FOR_THIS_RUN"`
- [ ] All `selectedUncertainties` have ≥2 states each
- [ ] All `approvedLenses` have `status: "approved"` and pass validator
- [ ] At least one edge-condition lens included (GP-06, GP-13, GP-18, GP-24)
- [ ] At least one lens challenges decision owner's default assumption
- [ ] No `BLOCKING` assumptions
- [ ] Intended use not prohibited
- [ ] Source material rights attested
- [ ] Run manifest template ready

### In-Run (Continuous)

- [ ] No prohibited language in any action (validator checks each round)
- [ ] All actions trace to lens constraints/incentives/informationConditions
- [ ] No lens exceeds configured action rate
- [ ] Conflict resolutions logged with rationale
- [ ] Disconfirmation checks executed on schedule
- [ ] Stop conditions evaluated each round

### Post-Run (Gate 1 — MUST PASS)

- [ ] Run manifest complete and immutable
- [ ] All paths have ≥1 validation question
- [ ] No path lacks disconfirming condition
- [ ] Coverage ledger: all uncertainty states covered or explicitly excluded
- [ ] No semantic duplicate paths (validator checks)
- [ ] All profile `status` fields updated to `approved`/`rejected` with reason
- [ ] Exports include Truth Rail and machine-readable disclosure
- [ ] Comprehension test: moderated users confirm synthetic nature

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-18 | Initial scenario rules and participation protocol |

---

## References

- [`docs/research/synthetic-decision-lenses.md`](../research/synthetic-decision-lenses.md) — Profile library
- [`docs/architecture/state-machines.md`](../architecture/state-machines.md) — Four independent state machines
- [`backend/app/services/simulation_config_generator.py`](../../backend/app/services/simulation_config_generator.py) — Config generation
- [`backend/app/services/simulation_runner.py`](../../backend/app/services/simulation_runner.py) — Execution engine

---

**END OF DOCUMENT**

*This protocol governs fictional scenario devices only. No rule implies human participation, measurement, or prediction.*