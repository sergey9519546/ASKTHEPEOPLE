---
title: "Persona Depth Analysis: Should We Go Deeper?"
status: "Analysis"
version: "1.0.0"
created: "2026-08-03"
owner: "askthepeople-architect"
last_reviewed: "2026-08-03"
---

# Persona Depth Analysis: Should We Go Deeper?

## Question

Should we expand persona complexity and multi-agent sophistication? Will deeper personas make the simulation stronger? How advanced can we get?

## Current State (OASIS + Our Implementation)

**What we have now:**

From `backend/app/services/oasis_profile_generator.py`:
- **Rich personas** with: bio, karma, follower counts, age, gender, MBTI, country, profession, interested topics
- **LLM-generated depth** when use_llm=True (detailed backgrounds, motivations, personality)
- **Rule-based fallback** for basic personas
- **Validation enforcement** (Gate 1: prevents malformed agents)
- **Multiple entity types:** person, organization, event, trend, document, concept, technology, location, historical_figure

OASIS (camel-oasis) already includes:
- Social networks (relationships between agents)
- Belief systems
- Memory and learning
- Multi-turn discourse
- Recommendation engines
- Psychological modeling

**What we DON'T have:**
- ❌ Hierarchical organizations (leaders, members, decision structures)
- ❌ Dynamic coalitions (agents forming groups mid-simulation)
- ❌ Temporal evolution (how beliefs/behaviors change over time)
- ❌ Resource constraints (budgets, time, information limits)
- ❌ Strategic reasoning (game theory, anticipating others' moves)
- ❌ Emotional dynamics (affect contagion, sentiment shifts)
- ❌ Power structures (influence, authority, dependency)

## The Core Tension

**Product Truth Contract (`docs/product/PRODUCT_TRUTH_CONTRACT.md`):**

> ASKTHEPEOPLE MUST NOT claim, imply, or visualize that it:
> - measured public opinion, sentiment, preference, intent, or behavior;
> - recruited, sampled, observed, interviewed, or surveyed people;
> - generated representative respondents or a population;
> - predicts what people will do or assigns real-world likelihood;

**The risk:** Deeper personas → more "realistic" outputs → users mistake synthetic exploration for predictive research.

**The opportunity:** Deeper personas → richer exploration of edge cases, group dynamics, emergent behavior → better decision support.

## Arguments FOR Deeper Personas

### 1. **Group Dynamics Matter**
Real decisions involve organizations, coalitions, power structures. Examples:
- Policy decisions: lobbying groups, government agencies, advocacy coalitions
- Product launches: internal teams, competitors, user segments, press
- Infrastructure projects: local government, community groups, businesses, residents

**Current gap:** Individual personas don't model:
- Organizational decision-making (committees, hierarchies, approval chains)
- Coalition formation (groups forming around shared interests)
- Power asymmetries (who influences whom)

**Impact:** User sees "what individuals might think" but misses "how groups act collectively."

### 2. **Temporal Evolution Is Underexplored**
Current system is essentially "snapshot at T=0." But real scenarios unfold over time:
- Initial reactions → informed opinions → behavior change
- Early adopters → mainstream → laggards
- Crisis response → adaptation → new normal

**What we could add:**
- Multi-stage simulations: T+1 week, T+1 month, T+1 year
- Agent belief updating based on interactions
- Event triggers that shift the landscape mid-simulation

**Value:** "What happens next?" is often more important than "what happens initially."

### 3. **Constraints Add Realism**
Current personas are "unconstrained actors." But real people face:
- **Information asymmetry:** Not everyone knows the same things
- **Resource limits:** Budget, time, attention constraints
- **Structural barriers:** Regulations, norms, dependencies

**Example:**
- Without constraints: "Persona A opposes the policy"
- With constraints: "Persona A opposes the policy but lacks budget to campaign, so joins Coalition B instead"

**Impact:** Unconstrained agents generate "what people think" but miss "what people can actually do."

### 4. **Strategic Reasoning Unlocks New Insights**
Current agents are "reactive" (respond to prompts). Strategic agents:
- Anticipate others' moves
- Form alliances
- Negotiate, compromise, compete
- Play multi-move games

**Example:** Product pricing decision
- Reactive: "Customer segment X likes price Y"
- Strategic: "Competitor will undercut us, customers will wait for discount, so we should bundle instead"

**Value:** Surface second-order effects and competitive dynamics.

### 5. **Multi-Agent Systems Can Be Arbitrarily Sophisticated**
Technically, we can add:
- **Hierarchical agents:** Organizations with internal structure
- **Emergence:** Patterns that arise from interactions (trends, norms, tipping points)
- **Learning:** Agents adapt strategies based on outcomes
- **Cultural models:** Shared beliefs, norms, identity groups
- **Emotional contagion:** Sentiment spreading through networks

State-of-the-art examples:
- Generative Agents (Stanford): 25 agents in a virtual town, emergent social behavior
- PettingZoo: Multi-agent RL environments with complex interactions
- GATO, Voyager: Agents that learn and adapt

**Bottom line:** We're not technically limited. Question is: should we?

## Arguments AGAINST (or Cautions)

### 1. **Complexity → False Confidence**
More realistic outputs → users forget it's synthetic → treat as predictive.

**Risk:**
- "The simulation said customers will love this" → launch without real research
- "The AI predicted this coalition would form" → assume it will happen

**Product Truth violation:** We explicitly MUST NOT imply predictive capability.

**Mitigation:**
- Even more aggressive disclaimers as depth increases
- Always show "synthetic" badge on deeper simulations
- Require users to acknowledge "not predictive" before accessing advanced features

### 2. **Diminishing Returns**
**Question:** Do users need Game of Thrones-level complexity to make better decisions?

**Hypothesis:** 80% of value comes from:
- "I hadn't considered stakeholder X"
- "Edge case Y could derail this"
- "Assumption Z is critical to test"

Simple personas might suffice for that.

**Need:** User research to validate whether current depth is adequate or insufficient.

### 3. **Cost**
Deeper agents = more LLM calls = higher cost per simulation.

**Current cost drivers:**
- Persona generation (LLM calls per entity)
- Discourse graph (multi-turn conversations)
- Report synthesis

**If we add:**
- Multi-stage temporal simulations → 3x-5x cost
- Strategic reasoning → 2x-3x cost per turn (agents need to model others)
- Organizational hierarchies → complexity grows with org size

**Need:** Cost-benefit analysis. Is 5x cost justified by 2x better insights?

### 4. **Speed**
Deeper = slower. Current simulation time is already measured in minutes.

**User expectation:** "Faster than real research" is a core value prop.

**If we add:**
- Game-theoretic reasoning → each agent needs to simulate others' moves → exponential blowup
- Multi-stage evolution → linear 3x-5x time increase
- Large coalitions → interaction complexity grows O(n²)

**Need:** Performance profiling. What's the ceiling before users abandon?

### 5. **Interpretability**
Overly complex agents are black boxes.

**Current strength:** Users can see persona profiles, understand their reasoning.

**Risk with depth:**
- "Why did Coalition A form?" → "Emergent from 200 interactions" → user can't audit
- "Why did Agent B change position?" → "Learning algorithm updated weights" → opaque

**Product Truth requirement:** Users must understand what assumptions drove the output.

**Need:** Explainability grows with complexity. Can we maintain transparency?

### 6. **We're Already Sophisticated**
OASIS is a research-grade framework (camel-ai + oasis extensions). Current personas have:
- Detailed bios, personality traits (MBTI), demographics
- Source-derived attributes (karma, followers, interests)
- Multi-turn discourse capability
- Validation enforcement (Gate 1)

**Question:** Are we underusing current depth? Maybe the problem isn't "not deep enough" but "not surfacing depth well."

**Example:** Do users even see MBTI, interested_topics, karma in the UI? If not, adding more depth is premature.

## Technical Possibilities (What We Could Build)

### Tier 3: Organizational Depth (3-4 weeks)
**Add:**
- Organizations as hierarchical agents (CEO → VPs → teams)
- Decision-making structures (voting, consensus, veto power)
- Internal politics (competing factions within orgs)

**Use case:** Policy decisions involving government agencies, corporations

**Cost impact:** +50% LLM calls (organizations need internal deliberation)

### Tier 4: Temporal Evolution (2-3 weeks)
**Add:**
- Multi-stage simulations (T+0, T+1 week, T+1 month, T+1 year)
- Belief updating based on interactions
- Event shocks (external triggers mid-simulation)

**Use case:** "How will this play out over time?"

**Cost impact:** +200-400% (3-5 stages)

### Tier 5: Strategic Reasoning (4-6 weeks)
**Add:**
- Game-theoretic agents (anticipate others' moves)
- Coalition formation (agents join groups dynamically)
- Negotiation, compromise, trade-offs

**Use case:** Competitive scenarios (market entry, political campaigns)

**Cost impact:** +150-250% (agents need to model others)

### Tier 6: Resource Constraints (2-3 weeks)
**Add:**
- Budgets, time limits, attention constraints
- Information asymmetry (not everyone knows everything)
- Dependency modeling (Agent A needs Agent B's approval)

**Use case:** "What can actors actually DO, not just think?"

**Cost impact:** +30-50% (constraint checking)

### Tier 7: Emotional/Cultural Depth (3-4 weeks)
**Add:**
- Emotional models (affect, sentiment, contagion)
- Cultural identity groups (shared norms, in-group bias)
- Network influence (opinions spread through connections)

**Use case:** Social movements, cultural shifts

**Cost impact:** +50-100% (network propagation algorithms)

## Recommendation: Tiered Depth Strategy

**Don't make personas uniformly deeper. Let users choose depth based on their needs.**

### Quick Exploration Mode (current, 0 changes)
- **Use case:** "I need diverse perspectives fast"
- **Depth:** Current OASIS personas (bio, demographics, interests)
- **Speed:** Minutes
- **Cost:** Baseline
- **UI badge:** "Exploratory simulation"

### Standard Mode (Tier 3: Organizations, 3-4 weeks)
- **Use case:** "I need to model group dynamics"
- **Depth:** + Organizational hierarchies, coalition formation
- **Speed:** 2-3x slower
- **Cost:** 1.5x
- **UI badge:** "Group dynamics simulation"

### Deep Analysis Mode (Tier 3 + 4 + 6, 6-8 weeks)
- **Use case:** "I need to see how this unfolds over time with real constraints"
- **Depth:** + Temporal evolution, resource constraints
- **Speed:** 5-7x slower
- **Cost:** 3-5x
- **UI badge:** "Deep temporal analysis (synthetic)"
- **Requires:** Extra disclaimer on non-predictive nature

### Strategic Mode (All tiers, 10-12 weeks)
- **Use case:** "I need game-theoretic competitive analysis"
- **Depth:** + Strategic reasoning, emotional/cultural dynamics
- **Speed:** 10x+ slower
- **Cost:** 5-10x
- **UI badge:** "Advanced strategic simulation (synthetic, not predictive)"
- **Requires:** Strongest disclaimers + mandatory "validate with real research" handoff

## What to Do NOW

### Step 1: User Research (1-2 weeks)
**Questions:**
1. Is current persona depth sufficient for your decision-making needs?
2. What's missing? (group dynamics, time evolution, constraints, strategic thinking?)
3. Would you pay 3x-5x more for deeper simulations?
4. How do you currently use persona profiles? Do you read MBTI, interests, bio?

**Method:** Interview 5-10 users, review session recordings, analyze which persona fields are viewed

### Step 2: Surface Current Depth Better (1 week)
**Before building new depth, expose existing depth:**
- Show MBTI, interested_topics, karma in persona cards (currently hidden?)
- Visualize relationships between personas (social graph)
- Explain why Agent X said Y based on their profile

**Hypothesis:** We may already have depth users want, just not surfacing it.

### Step 3: Prototype Tier 3 (Organizations) (2-3 weeks)
**If user research shows group dynamics are critical:**
- Build organizational hierarchy support
- Test with 3-5 pilot users
- Measure: Does it change their decisions? Is cost/speed acceptable?

### Step 4: Build Depth Selector in UI (1 week)
**Add to Home.vue:**
- "Simulation depth" radio buttons: Quick / Standard / Deep / Strategic
- Show estimated time and cost for each
- Require extra disclaimer for Deep/Strategic

### Step 5: A/B Test Impact (ongoing)
**Measure:**
- Do deeper simulations lead to better decisions? (follow-up surveys)
- Do users validate with real research afterward? (adherence to product truth)
- What's the cost/speed tolerance?

## Decision Criteria

**Invest in deeper personas IF:**
1. ✅ User research shows current depth is insufficient
2. ✅ Users willing to pay 2x-5x more for depth
3. ✅ We can maintain product truth (not predictive) with strong disclaimers
4. ✅ Interpretability remains high (users can audit reasoning)
5. ✅ Speed stays within tolerance (users don't abandon)

**Don't invest (or deprioritize) IF:**
1. ❌ Current depth is adequate (underutilized)
2. ❌ Users want speed over depth
3. ❌ Deeper outputs increase false confidence
4. ❌ Cost/speed tradeoffs are unacceptable
5. ❌ Other features (e.g., better handoff to real research) have higher ROI

## Conclusion

**Short answer:** Yes, we CAN go arbitrarily deeper. OASIS + modern multi-agent systems support organizational hierarchies, temporal evolution, strategic reasoning, emotional dynamics, and more.

**Strategic answer:** We SHOULD go deeper IF user research validates the need AND we can maintain product truth (synthetic, not predictive) AND cost/speed tradeoffs are acceptable.

**Immediate next step:** User research. Talk to 5-10 users about current persona depth. Are they reading the MBTI? Do they want group dynamics? Time evolution? Strategic reasoning? Would they pay more for it?

**Fallback:** If users say "current depth is fine, I just want it faster/cheaper," then optimize current system instead of adding complexity.

**My gut:** Tier 3 (organizational depth) is likely high-value and underexplored. Personas interacting as individuals misses how real decisions involve groups, coalitions, and power structures. I'd prioritize that over emotional/cultural models.

But validate with users first.
