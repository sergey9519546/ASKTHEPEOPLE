# Approved External Claims Registry

**Purpose:** This document defines the approved and prohibited claims for ASKTHEPEOPLE external communications, marketing, and product descriptions. All claims must accurately represent the synthetic, exploratory nature of the tool.

**Gate 1 Requirement:** Truth contract enforcement - no misleading claims about human respondents, statistical validity, or predictive capability.

---

## ✅ Approved Claims

### Product Description
- "Explore decision perspectives synthetically"
- "Synthetic scenario explorer"
- "Non-representative exploration tool"
- "Starting point for research"
- "Stress-test a decision with source-informed synthetic scenarios"
- "Map possible paths before making a decision"
- "See the paths before you choose"
- "Source-informed synthetic exploration"

### Use Cases
- "Generate hypothetical scenarios for discussion"
- "Explore different perspectives on a decision"
- "Identify assumptions to validate with real people"
- "Create conversation starters for user research"
- "Map potential stakeholder viewpoints"
- "Structure research questions"

### Methodology
- "AI-generated scenarios based on source material"
- "Synthetic profiles derived from documents"
- "Model-generated dialogue"
- "0 human respondents"
- "Not based on real human responses"
- "Outputs are generated, not observed"

### Validation
- "Requires validation with real people"
- "Use as input for real research"
- "Take the paths outside to validate"
- "Starting point, not a conclusion"

---

## ❌ Prohibited Claims

### Predictive Claims
- ❌ "Predict outcomes"
- ❌ "Forecast behavior"
- ❌ "Anticipate market response"
- ❌ "Project future trends"
- ❌ "Estimate probability"
- ❌ "Calculate likelihood"

### Statistical Claims
- ❌ "Representative sample"
- ❌ "Statistically significant"
- ❌ "Confidence intervals"
- ❌ "Margin of error"
- ❌ "Sample size of X"
- ❌ "X% of people think..."

### Human Response Claims
- ❌ "Real human responses"
- ❌ "Survey results"
- ❌ "User feedback"
- ❌ "Customer opinions"
- ❌ "Public sentiment"
- ❌ "What people really think"

### Decision Support Claims
- ❌ "Make the right decision"
- ❌ "Optimal choice"
- ❌ "Best path forward"
- ❌ "Proven strategy"
- ❌ "Data-driven recommendation"
- ❌ "Evidence-based decision"

### Replacement Claims
- ❌ "Replace user research"
- ❌ "Skip customer interviews"
- ❌ "Eliminate need for surveys"
- ❌ "Substitute for market research"

---

## 🔍 Review Checklist

Before publishing any external communication, verify:

- [ ] No claims about human respondents (always "0 human respondents")
- [ ] No statistical validity claims (no confidence intervals, significance)
- [ ] No predictive capability claims (not a forecast)
- [ ] Clear synthetic/exploratory framing
- [ ] Validation requirement mentioned where appropriate
- [ ] Truth Rail equivalent disclosure present

---

## 📋 Required Disclosures

All product interfaces, exports, and external communications must include:

### Minimum Disclosure
```
SYNTHETIC EXPLORATION • 0 human respondents • Non-representative sample
```

### Export Disclosures
All exported reports, PDFs, CSV files, or presentations must include:
```
NOTICE: This output is synthetically generated using AI models. It contains
0 human respondents and is not a representative sample. Outputs are exploratory
scenarios, not predictions or evidence. Validate with real people before making
consequential decisions.
```

### API Response Metadata
All API responses must include:
```json
{
  "human_respondent_count": 0,
  "output_origin": "synthetic",
  "is_forecast": false,
  "generated_at": "ISO8601 timestamp"
}
```

---

## 🚨 Violation Protocol

If a prohibited claim is identified:

1. **Immediate:** Remove or update the claim
2. **Document:** Log the violation and context
3. **Review:** Assess how the claim was introduced
4. **Prevent:** Update review process to catch similar issues

---

## 📝 Change Log

- **2026-08-02:** Initial claim registry created for Gate 1 compliance
- Gate 1 requirement: Truth Rail and API metadata enforcement

---

## References

- **Truth Contract:** backend/app/services/claim_boundary.py
- **API Metadata:** backend/app/utils/response.py
- **Frontend Disclosure:** frontend/src/components/TruthRail.vue
- **Export Disclosures:** backend/app/services/export_service.py
