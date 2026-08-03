---
title: "Big Five Personality Model Integration"
status: "Design Specification"
version: "1.0.0"
owner: "askthepeople-ai-eval-steward"
last_reviewed: "2026-08-03"
created: "2026-08-02"
---

# Big Five Personality Model Integration

> **Implementation note (2026-08-03).** This spec proposed *replacing* MBTI.
> That is not what shipped, because it would break the simulation: the installed
> OASIS package indexes `profile["other_info"]["mbti"]` unconditionally at
> `oasis/social_agent/agents_generator.py:461` and interpolates it into the agent
> system prompt at `oasis/social_platform/config/user.py:97`, so a missing key
> raises `KeyError` mid-run. The delivered implementation in
> `backend/app/services/big_five.py` ADDS Big Five alongside `mbti` and derives
> the MBTI code from traits for interop. Read this document as background on the
> model; read the module docstring for what actually exists.

**Status:** Design Specification (superseded in part — see note above)  
**Created:** 2026-08-02  
**Purpose:** Adopt the empirically validated Big Five (OCEAN) personality model for agent persona generation

---

## Executive Summary

This document specifies the replacement of MBTI personality typing with the Big Five (Five-Factor Model) in OASIS agent profile generation. MBTI lacks predictive validity and scientific support, while Big Five demonstrates robust cross-cultural validity, behavioral prediction, and empirical foundation across decades of research.

**Key Changes:**
- Replace `mbti: str` field with five continuous trait scores (0-100 scale)
- Update OasisAgentProfile dataclass and database schema
- Implement trait-based behavioral mappings for agent reasoning
- Develop NLP-based trait inference from source material
- Create trait → Prospect Theory parameter modulation

---

## 1. Big Five Model Overview

### 1.1 Trait Definitions

The Big Five (OCEAN) groups personality variation into five continuous dimensions:

| Trait | Description | High Scorer | Low Scorer |
|-------|-------------|-------------|------------|
| **Openness (O)** | Intellectual curiosity, creativity, openness to new experiences | Curious, creative, open to emotion, willing to try new things | Prefers routine, practical, traditional, values familiarity |
| **Conscientiousness (C)** | Self-discipline, organization, goal-directed behavior | Organized, disciplined, achievement-oriented, detail-focused | Spontaneous, flexible, disorganized, less goal-driven |
| **Extraversion (E)** | Social energy, assertiveness, tendency to seek stimulation | Energetic, talkative, socially engaged, seeks excitement | Reserved, introspective, requires less stimulation, reflective |
| **Agreeableness (A)** | Compassion, cooperation, trust in others | Kind, helpful, trusting, cooperative, considers others | Competitive, skeptical, self-interested, analytical |
| **Neuroticism (N)** | Emotional instability, negative emotional reactivity | Anxious, prone to worry, emotionally reactive, stress-sensitive | Emotionally stable, calm, resilient, even-tempered |

### 1.2 Empirical Foundation

**Why Big Five > MBTI:**
- **Predictive Validity:** Big Five predicts job performance, academic success, health outcomes, relationship quality
- **Cross-Cultural Replication:** Five-factor structure validated across 50+ nations and languages
- **Continuous Scales:** Captures nuance vs. MBTI's binary forced-choice categories
- **Test-Retest Reliability:** Stable across lifespan from childhood to adulthood
- **No Type Fallacy:** Avoids pseudoscientific "type" categorization without empirical support

**Behavioral Predictions:**
- Conscientiousness → job performance, academic achievement, reduced mortality
- Neuroticism → mental health disorders (anxiety, depression), stress reactivity
- Agreeableness → transformational leadership, conflict resolution
- Openness → creative achievement, intellectual pursuits, political liberalism
- Extraversion → social network size, leadership emergence, subjective well-being

### 1.3 Measurement Instruments

**Validated Scales:**
- **BFI-10** (Big Five Inventory-10): 2 items per trait, ~1 minute, good reliability (α=0.65-0.87)
- **IPIP-NEO-50**: International Personality Item Pool, 50 items, public domain
- **TIPI** (Ten-Item Personality Inventory): Ultra-brief screening, research use
- **NEO-PI-R**: Gold standard, 240 items, 6 facets per trait (clinical/research)

**Sample Items:**
- Openness: "I have a vivid imagination" / "I am interested in abstract ideas"
- Conscientiousness: "I get chores done right away" / "I make plans and stick to them"
- Extraversion: "I am the life of the party" / "I talk to a lot of different people"
- Agreeableness: "I sympathize with others' feelings" / "I trust what people say"
- Neuroticism: "I get stressed out easily" / "I worry about things"

### 1.4 Score Ranges & Population Distributions

**Scoring:**
- Raw scores converted to 0-100 percentile scale
- Mean ≈ 50, SD ≈ 15-20 (normalized to population)
- **No binary cutoffs** — traits are continuous

**Population Distributions:**
- Women score slightly higher on N, E, A, C (d=0.3-0.5)
- Gender differences larger in egalitarian nations
- Heritability: 40-60% genetic influence per trait
- Cultural variations exist but five-factor structure replicates globally

**Typical Ranges:**
- 0-20: Very low
- 21-40: Low
- 41-60: Moderate/Average
- 61-80: High
- 81-100: Very high

---

## 2. Schema Design Changes

### 2.1 OasisAgentProfile Dataclass Update

**Current Schema (Line 48 in oasis_profile_generator.py):**
```python
mbti: Optional[str] = None
```

**Proposed Schema:**
```python
# Big Five personality traits (0-100 percentile scale)
# None = not inferred from source material (use population defaults)
openness: Optional[float] = None
conscientiousness: Optional[float] = None
extraversion: Optional[float] = None
agreeableness: Optional[float] = None
neuroticism: Optional[float] = None
```

### 2.2 Validation Rules

**Field Constraints:**
```python
def validate_big_five_score(score: Optional[float]) -> bool:
    """Validate Big Five trait score is within valid range."""
    if score is None:
        return True  # Allow None (use defaults)
    return 0.0 <= score <= 100.0

# Add to ProfileValidator class
BIG_FIVE_TRAITS = ['openness', 'conscientiousness', 'extraversion', 
                    'agreeableness', 'neuroticism']
```

**Default Values:**
- When source material doesn't support inference: Use population mean (50.0)
- Institutional/group entities: Set N=30 (low), C=65 (high), others=50
- Explicitly fictional: Flag as `personality_source: "generated"` in metadata

### 2.3 Database Migration Strategy

**Migration Steps:**
1. Add five new columns to agent_profiles table: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism` (all FLOAT, nullable)
2. Keep `mbti` column temporarily for rollback capability
3. Backfill existing profiles with default values (all 50.0) + flag `personality_source: "legacy_mbti"`
4. Update all generation code to use Big Five
5. After 2-week validation period, deprecate `mbti` column (do not drop immediately)

**Migration Script Pseudocode:**
```sql
ALTER TABLE agent_profiles 
  ADD COLUMN openness FLOAT,
  ADD COLUMN conscientiousness FLOAT,
  ADD COLUMN extraversion FLOAT,
  ADD COLUMN agreeableness FLOAT,
  ADD COLUMN neuroticism FLOAT,
  ADD COLUMN personality_source VARCHAR(50) DEFAULT 'big_five';

-- Backfill existing profiles with neutral defaults
UPDATE agent_profiles 
SET openness = 50.0,
    conscientiousness = 50.0,
    extraversion = 50.0,
    agreeableness = 50.0,
    neuroticism = 50.0,
    personality_source = 'legacy_mbti'
WHERE openness IS NULL;

-- Institutional profiles get specialized defaults
UPDATE agent_profiles
SET conscientiousness = 65.0,
    neuroticism = 30.0
WHERE source_entity_type IN ('university', 'governmentagency', 'organization', 'ngo');
```

---

## 3. Generation Methods

### 3.1 NLP-Based Trait Inference

**Approach:** Use LLM to analyze source material (entity summary, bio, related facts) and estimate Big Five scores.

**Prompt Template (Add to backend/app/prompts/definitions/):**
```yaml
prompt_id: big_five_inference
version: 1.0.0
system_prompt: |
  You are a personality assessment expert. Analyze the provided text and estimate
  Big Five personality trait scores (0-100 percentile scale).
  
  Return ONLY scores that are clearly supported by the text. Use null for traits
  where evidence is insufficient. Do not stereotype or assume traits based on
  demographics, profession, or cultural background.
  
  Scoring guidelines:
  - 0-20: Very low (strong contrary evidence)
  - 21-40: Low (some contrary evidence)  
  - 41-60: Moderate (neutral or mixed evidence)
  - 61-80: High (clear supporting evidence)
  - 81-100: Very high (overwhelming evidence)

user_prompt: |
  Analyze this profile and estimate Big Five trait scores:
  
  Name: {entity_name}
  Type: {entity_type}
  Summary: {entity_summary}
  Context: {context}
  
  Return JSON:
  {{
    "openness": <float or null>,
    "conscientiousness": <float or null>,
    "extraversion": <float or null>,
    "agreeableness": <float or null>,
    "neuroticism": <float or null>,
    "reasoning": {{
      "openness": "<evidence from text>",
      "conscientiousness": "<evidence from text>",
      ...
    }}
  }}
```

**Implementation Location:**
- Add to `_generate_profile_with_llm()` method
- Call LLM with trait inference prompt after base profile generation
- Merge trait scores into profile_data

### 3.2 Demographic-Based Inference

**Avoid Direct Stereotyping:**
- DO NOT map profession → traits (e.g., "engineers are introverted")
- DO NOT map demographics → traits (e.g., "young people are open")
- DO use population distributions when no source material exists

**Rule-Based Fallbacks (Only When Source Material is Silent):**

**Individual Entities:**
```python
def get_individual_defaults(entity_type: str) -> Dict[str, float]:
    """Neutral defaults for individual entities."""
    return {
        "openness": 50.0,
        "conscientiousness": 50.0,
        "extraversion": 50.0,
        "agreeableness": 50.0,
        "neuroticism": 50.0,
    }
```

**Institutional Entities:**
```python
def get_institutional_defaults(entity_type: str) -> Dict[str, float]:
    """Institutional accounts have different personality profiles."""
    # Institutions: More conscientious, less neurotic, moderate on others
    return {
        "openness": 50.0,  # Neutral
        "conscientiousness": 65.0,  # High (formal, structured)
        "extraversion": 50.0,  # Neutral
        "agreeableness": 55.0,  # Slightly high (public-facing)
        "neuroticism": 30.0,  # Low (stable, measured communication)
    }
```

### 3.3 Default Distributions

**When No Source Material Available:**
- Sample from normal distribution with variance
- Mean = 50, SD = 15
- Clip to [20, 80] to avoid extreme profiles without evidence
- Add random jitter (±5 points) to ensure diversity

**Python Implementation:**
```python
import random

def sample_default_traits(entity_type: str, add_variance: bool = True) -> Dict[str, float]:
    """Generate default trait scores with population variance."""
    if entity_type.lower() in GROUP_ENTITY_TYPES:
        defaults = get_institutional_defaults(entity_type)
    else:
        defaults = get_individual_defaults(entity_type)
    
    if add_variance:
        # Add jitter to ensure no duplicate profiles
        return {
            trait: max(20.0, min(80.0, score + random.gauss(0, 5)))
            for trait, score in defaults.items()
        }
    return defaults
```

---

## 4. Behavioral Mappings

### 4.1 Trait → Behavior Dictionary

Document how each trait modulates agent behavior in OASIS simulations.

**Openness to Experience:**
- **High (70-100):**
  - Early adopter of new ideas/products
  - Prefers creative/novel solutions
  - More likely to challenge conventional wisdom
  - Higher information-seeking behavior
  - Less brand loyalty (explores alternatives)
  
- **Low (0-30):**
  - Prefers proven, traditional approaches
  - Risk-averse to novel ideas
  - Values routine and predictability
  - Strong brand loyalty
  - Skeptical of innovation

**Conscientiousness:**
- **High (70-100):**
  - Careful planning before decisions
  - Detail-oriented research
  - Completes tasks thoroughly
  - Delayed gratification (prefers long-term gains)
  - Risk-averse (follows rules, avoids uncertainty)
  
- **Low (0-30):**
  - Impulsive decision-making
  - Less thorough research
  - Spontaneous behavior
  - Immediate gratification preference
  - More risk-tolerant (flexible with rules)

**Extraversion:**
- **High (70-100):**
  - Initiates social interactions frequently
  - Seeks group consensus
  - High posting/engagement frequency
  - Responds quickly to others
  - Influenced by social proof
  
- **Low (0-30):**
  - Selective social engagement
  - Independent decision-making
  - Lower posting frequency
  - Thoughtful, delayed responses
  - Less influenced by social proof

**Agreeableness:**
- **High (70-100):**
  - Cooperative, avoids conflict
  - Trusts others' claims without verification
  - Empathetic responses
  - Compromises easily
  - Influenced by appeals to fairness
  
- **Low (0-30):**
  - Competitive, confrontational
  - Skeptical of others' claims
  - Analytical, critical responses
  - Prioritizes self-interest
  - Influenced by logical arguments

**Neuroticism:**
- **High (70-100):**
  - Amplifies negative information
  - Risk-averse (focuses on potential losses)
  - Anxious about decisions
  - High emotional reactivity
  - Seeks reassurance before acting
  
- **Low (0-30):**
  - Emotionally stable
  - Balanced risk assessment
  - Confident decision-making
  - Low emotional reactivity
  - Acts independently without reassurance

### 4.2 Decision-Making Modulation

**Content Engagement:**
```python
def calculate_engagement_probability(content, agent_traits):
    """Calculate likelihood agent engages with content based on Big Five."""
    base_prob = 0.5
    
    # Openness: Novelty-seeking
    if is_novel_content(content):
        base_prob += 0.2 * (agent_traits['openness'] - 50) / 50
    
    # Conscientiousness: Quality filter
    if is_well_researched(content):
        base_prob += 0.15 * (agent_traits['conscientiousness'] - 50) / 50
    
    # Extraversion: Social content
    if is_social_content(content):
        base_prob += 0.2 * (agent_traits['extraversion'] - 50) / 50
    
    # Agreeableness: Conflict avoidance
    if is_controversial_content(content):
        base_prob -= 0.2 * (agent_traits['agreeableness'] - 50) / 50
    
    # Neuroticism: Negative content amplification
    if is_negative_content(content):
        base_prob += 0.15 * (agent_traits['neuroticism'] - 50) / 50
    
    return np.clip(base_prob, 0.0, 1.0)
```

**Response Style:**
```python
def generate_response_style(agent_traits):
    """Determine agent's communication style based on Big Five."""
    style = {
        'formality': 0.5 + 0.3 * (agent_traits['conscientiousness'] - 50) / 50,
        'emotion_expression': 0.5 + 0.3 * (agent_traits['neuroticism'] - 50) / 50,
        'verbosity': 0.5 + 0.2 * (agent_traits['extraversion'] - 50) / 50,
        'critical_tone': 0.5 - 0.3 * (agent_traits['agreeableness'] - 50) / 50,
        'creativity': 0.5 + 0.3 * (agent_traits['openness'] - 50) / 50,
    }
    return {k: np.clip(v, 0.0, 1.0) for k, v in style.items()}
```

---

## 5. Prospect Theory Integration

### 5.1 Big Five → Prospect Theory Parameters

**Prospect Theory Parameters:**
- **λ (lambda):** Loss aversion coefficient (losses hurt more than gains feel good)
- **α (alpha):** Risk attitude for gains (curvature of value function)
- **β (beta):** Risk attitude for losses
- **γ (gamma):** Probability weighting (overweight small probabilities)

**Trait-Based Modulation:**

```python
def get_prospect_theory_params(big_five_traits: Dict[str, float]) -> Dict[str, float]:
    """
    Derive Prospect Theory parameters from Big Five traits.
    
    Based on research:
    - Neuroticism → higher loss aversion
    - Conscientiousness → lower risk-seeking
    - Openness → lower probability weighting distortion
    - Agreeableness → lower loss aversion (other-focused)
    """
    
    # Normalize traits to [-1, 1] range
    def norm(score): return (score - 50) / 50
    
    # Base parameters (typical population averages)
    lambda_base = 2.25  # Loss aversion
    alpha_base = 0.88   # Risk attitude for gains
    beta_base = 0.88    # Risk attitude for losses
    gamma_base = 0.65   # Probability weighting
    
    # Modulate based on Big Five
    lambda_adj = lambda_base * (1 + 0.3 * norm(big_five_traits['neuroticism'])
                                  - 0.15 * norm(big_five_traits['agreeableness']))
    
    alpha_adj = alpha_base * (1 - 0.1 * norm(big_five_traits['conscientiousness'])
                               + 0.1 * norm(big_five_traits['openness']))
    
    beta_adj = beta_base * (1 - 0.1 * norm(big_five_traits['conscientiousness']))
    
    gamma_adj = gamma_base * (1 - 0.1 * norm(big_five_traits['openness']))
    
    return {
        'lambda': np.clip(lambda_adj, 1.0, 4.0),
        'alpha': np.clip(alpha_adj, 0.5, 1.0),
        'beta': np.clip(beta_adj, 0.5, 1.0),
        'gamma': np.clip(gamma_adj, 0.4, 0.8),
    }
```

### 5.2 Research Citations

**Supporting Evidence:**
- Booij et al. (2020): Neuroticism correlates with loss aversion (r=0.23, p<0.001)
- Lauriola & Levin (2001): Conscientiousness negatively predicts risk-taking
- Nicholson et al. (2005): Openness associated with financial risk tolerance
- Weller & Tikir (2011): Agreeableness moderates loss aversion in social contexts

---

## 6. Implementation Plan

### 6.1 Phase 1: Schema & Infrastructure (Week 1)

**Tasks:**
1. Add Big Five fields to OasisAgentProfile dataclass
2. Update `to_dict()`, `to_reddit_format()`, `to_twitter_format()` methods
3. Create database migration script
4. Add Big Five validation to ProfileValidator
5. Update test fixtures with Big Five traits

**Files to Modify:**
- `backend/app/services/oasis_profile_generator.py` (lines 28-112)
- `backend/app/services/profile_validators.py` (add Big Five checks)
- `backend/app/services/archetype_engine.py` (update variant generation)
- `backend/app/services/simulation_artifacts.py` (line 20-30)

### 6.2 Phase 2: Generation Logic (Week 2)

**Tasks:**
1. Create Big Five inference prompt in prompt registry
2. Implement `_infer_big_five_from_context()` method
3. Update `_generate_profile_with_llm()` to call trait inference
4. Implement default sampling with variance
5. Add trait reasoning to profile metadata

**New Methods:**
```python
def _infer_big_five_from_context(
    self,
    entity_name: str,
    entity_type: str,
    entity_summary: str,
    context: str
) -> Dict[str, Optional[float]]:
    """Use LLM to infer Big Five traits from source material."""
    # Implementation here
    pass

def _apply_big_five_defaults(
    self,
    traits: Dict[str, Optional[float]],
    entity_type: str
) -> Dict[str, float]:
    """Fill in missing traits with appropriate defaults."""
    # Implementation here
    pass
```

### 6.3 Phase 3: Behavioral Integration (Week 3)

**Tasks:**
1. Document trait → behavior mappings
2. Create `AgentPersonalityModule` for decision modulation
3. Integrate with OASIS simulation engine
4. Implement Prospect Theory parameter derivation
5. Add trait-based content filtering

**New Module:**
```python
# backend/app/services/personality_module.py
class AgentPersonalityModule:
    """Modulates agent behavior based on Big Five personality traits."""
    
    def calculate_engagement_probability(self, content, traits): ...
    def generate_response_style(self, traits): ...
    def get_prospect_theory_params(self, traits): ...
    def modulate_decision(self, decision_context, traits): ...
```

### 6.4 Phase 4: Testing & Validation (Week 4)

**Tasks:**
1. Unit tests for trait inference
2. Integration tests for profile generation
3. Validate trait distributions across generated profiles
4. Ensure no stereotype patterns in inferred traits
5. A/B test Big Five vs. MBTI in simulation outcomes

**Test Coverage:**
- Trait scores within valid range [0, 100]
- No demographic → trait stereotyping
- Institutional profiles get appropriate defaults
- Trait inference returns None when evidence lacking
- Population distributions match expected variance

---

## 7. Migration Checklist

### 7.1 Backward Compatibility

**During Transition:**
- Keep `mbti` field in database (deprecated, not removed)
- Accept both MBTI and Big Five in API requests
- Return both in API responses (with deprecation warning)
- Log MBTI usage for monitoring

**Deprecation Timeline:**
- Week 1-2: Add Big Five, keep MBTI functional
- Week 3-4: Default to Big Five, log MBTI access
- Week 5-8: Show deprecation warnings for MBTI
- Week 9+: Remove MBTI from new profile generation (keep in DB for historical data)

### 7.2 Data Validation

**Pre-Migration Checks:**
- [ ] All existing profiles have valid MBTI values (or null)
- [ ] Database schema allows nullable Big Five fields
- [ ] Migration script tested on staging environment
- [ ] Rollback procedure documented

**Post-Migration Checks:**
- [ ] All new profiles have Big Five scores
- [ ] No profiles have all-null Big Five traits
- [ ] Trait distributions approximately normal (μ≈50, σ≈15)
- [ ] No stereotype patterns in generated traits
- [ ] Institutional profiles have appropriate trait patterns

---

## 8. Future Enhancements

### 8.1 Facet-Level Traits

Big Five has 6 facets per trait (30 total). Consider implementing for higher fidelity:

**Openness Facets:** Imagination, Artistic Interests, Emotionality, Adventurousness, Intellect, Liberalism

**Implementation:** Add optional `big_five_facets` JSON field for detailed profiles.

### 8.2 Dynamic Trait Adjustment

Personality traits can shift in response to life events. Consider:
- Context-dependent trait expression (e.g., work vs. social contexts)
- Trait drift over simulation time (major events → trait changes)
- Relationship-specific trait modulation

### 8.3 Trait-Based Clustering

Replace manual archetype labeling with automated trait-based clustering:
```python
from sklearn.cluster import KMeans

def cluster_by_traits(profiles, n_clusters=10):
    """Cluster agents by Big Five similarity."""
    trait_matrix = np.array([
        [p.openness, p.conscientiousness, p.extraversion, 
         p.agreeableness, p.neuroticism]
        for p in profiles
    ])
    kmeans = KMeans(n_clusters=n_clusters)
    return kmeans.fit_predict(trait_matrix)
```

---

## 9. References

### Academic Literature

1. **Costa & McCrae (1992).** "Revised NEO Personality Inventory (NEO-PI-R) and NEO Five-Factor Inventory (NEO-FFI) professional manual." *Psychological Assessment Resources.*

2. **Gosling et al. (2003).** "A very brief measure of the Big-Five personality domains." *Journal of Research in Personality, 37*(6), 504-528.

3. **Schmitt et al. (2007).** "The geographic distribution of Big Five personality traits: Patterns and profiles of human self-description across 56 nations." *Journal of Cross-Cultural Psychology, 38*(2), 173-212.

4. **Roberts et al. (2007).** "The power of personality: The comparative validity of personality traits, socioeconomic status, and cognitive ability for predicting important life outcomes." *Perspectives on Psychological Science, 2*(4), 313-345.

5. **Booij et al. (2020).** "Risk-taking behavior and the relation with personality, impulsivity, and frontal brain function." *Neuropsychologia*, 144, 107494.

6. **Nicholson et al. (2005).** "Personality and domain-specific risk taking." *Journal of Risk Research, 8*(2), 157-176.

### Measurement Instruments

- **BFI-10:** John & Srivastava (1999). "The Big Five trait taxonomy."
- **IPIP-NEO:** Goldberg et al. (2006). International Personality Item Pool.
- **TIPI:** Gosling et al. (2003). Ten-Item Personality Inventory.

### Online Resources

- IPIP Item Pool: https://ipip.ori.org/
- NEO Inventory: https://www.parinc.com/Products/Pkey/283
- Big Five Research: https://www.personalityresearch.org/

---

## Appendix A: MBTI → Big Five Approximate Mapping

**For Reference Only — DO NOT Use for Backfill**

This mapping is theoretically unsound (MBTI lacks validity) but provided for conceptual comparison:

| MBTI Type | O | C | E | A | N | Notes |
|-----------|---|---|---|---|---|-------|
| INTJ | 65 | 60 | 30 | 40 | 45 | High O (intuition), Low E |
| ENFP | 75 | 40 | 80 | 65 | 55 | High O & E, Low C |
| ISTJ | 35 | 75 | 30 | 50 | 35 | High C, Low O & E |
| ESFJ | 40 | 60 | 75 | 75 | 50 | High E & A |

**Do not use this for migration.** Generate new Big Five scores from source material or use population defaults.

---

## Appendix B: Sample Profile Comparison

### Before (MBTI):
```json
{
  "name": "Dr. Sarah Chen",
  "age": 34,
  "gender": "female",
  "mbti": "INTJ",
  "persona": "Research scientist interested in climate policy..."
}
```

### After (Big Five):
```json
{
  "name": "Dr. Sarah Chen",
  "age": 34,
  "gender": "female",
  "openness": 72.0,
  "conscientiousness": 68.0,
  "extraversion": 42.0,
  "agreeableness": 55.0,
  "neuroticism": 48.0,
  "personality_source": "inferred",
  "persona": "Research scientist interested in climate policy..."
}
```

**Behavioral Implications:**
- High O (72): Open to novel climate solutions, seeks cutting-edge research
- High C (68): Thorough research methodology, detail-oriented analysis
- Moderate-Low E (42): Prefers small group discussions over large conferences
- Moderate A (55): Balanced between collaboration and critical analysis
- Moderate N (48): Stable emotional responses, not overly anxious

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-02  
**Next Review:** After Phase 1 completion
