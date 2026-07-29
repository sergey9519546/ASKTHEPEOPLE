# Validate With People

## The handoff

ASKTHEPEOPLE ends where evidence about people begins.

The synthetic run can supply possible paths, assumptions, counterarguments, and
questions. A separate research process must determine whether any of them match
real people, behavior, or outcomes.

The current application does not recruit participants, obtain consent, field a
representative survey, or establish external validity. A “Validate with people”
stage must never imply that clicking a button performs those activities.

## Workflow

### 1. Define the real decision

Record:

- The decision to be made
- The accountable decision owner
- The people who could be affected
- The decision date
- The consequences of a false positive and false negative
- What evidence would be sufficient

If the decision is high-risk under the
[appropriate-use policy](APPROPRIATE_USE.md), stop and obtain qualified review.

### 2. Turn the run into an assumption register

For every important path, record:

| Field | Example |
| --- | --- |
| Path | Reduced service shifts some trips to cars |
| Source facts | Current ridership and route data |
| Generated assumption | Riders have access to a car |
| Synthetic observation | Generated actors discuss driving |
| Missing perspective | Riders without cars or weekend shift workers |
| Testable question | How would you make this trip if service ended? |
| Evidence needed | Interviews plus origin/destination behavior data |
| Decision threshold | Defined by the responsible team before collection |

Do not treat the number of synthetic actors that followed a path as prevalence.

### 3. Check sensitivity before fieldwork

Run materially different assumptions, prompts, models, persona constructions,
and repetitions. Ask:

- Which paths appear only under one configuration?
- Which paths disappear when an invented persona attribute is removed?
- Which stakeholders remain absent?
- Does a different model reverse the narrative?
- Are generated conclusions driven by a bootstrap event or prompt wording?
- Are metrics stable enough to be useful as internal descriptions?

Instability is not a defect to hide. It tells the research team where uncertainty
is concentrated.

### 4. Choose a human method

Match the method to the question:

| Need | Possible method |
| --- | --- |
| Understand language, motives, and missing paths | Semi-structured interviews |
| Test comprehension or usability | Moderated or unmoderated usability study |
| Facilitate tradeoffs among stakeholders | Deliberative workshop |
| Estimate prevalence in a defined population | Probability-based or otherwise methodologically justified survey |
| Observe actual behavior | Pilot, experiment, administrative data, or field observation |
| Evaluate causal impact | Qualified causal design with appropriate controls |
| Assess specialist constraints | Domain-expert review |

These methods have different validity limits. A convenience sample should not be
described as representative merely because real people participated.

### 5. Design and review the study

At minimum, document:

- Research question and target population
- Sampling frame, recruitment, inclusion, and exclusion
- Intended sample size and rationale
- Instrument or protocol
- Consent and participant information
- Privacy, data security, retention, and deletion
- Compensation
- Accessibility and language support
- Risks to participants and mitigations
- Analysis plan and stopping rules
- Conflicts of interest
- Required ethics, institutional, legal, or domain review

Keep synthetic scenario details from leading participants unnecessarily. Where
appropriate, test unprompted reactions before showing scenario branches.

### 6. Collect human evidence separately

Do not mix generated actors into the human respondent count. Preserve:

- Number invited
- Number who consented
- Number who completed
- Recruitment dates and mode
- Missingness and exclusions
- Questionnaire or discussion guide version
- Raw-data access controls
- Any weighting or adjustment

Use the AAPOR disclosure principle: state what AI did, how many human respondents
participated, and what validation and human oversight occurred. See
[Responsible AI Integration in Survey Research
(2026)](https://aapor.org/wp-content/uploads/2026/05/Responsible-AI-Integration-In-Survey-Research.pdf).

### 7. Compare, do not retrofit

Create a comparison table:

| Synthetic path | Human support | Human contradiction | Missing in simulation | Decision implication |
| --- | --- | --- | --- | --- |
| Path A | Evidence and sample | Evidence and sample | New path D | Revise assumption |

Report contradictions prominently. Do not edit or select synthetic runs after
seeing human findings to make the model appear prescient. If the synthetic paths
are used to build a benchmark, separate development and held-out evaluation
data.

### 8. Decide with accountable judgment

The decision record should distinguish:

- Verified source facts
- Synthetic hypotheses
- Human-reported findings
- Observed behavioral data
- Domain or legal constraints
- Remaining uncertainty
- The accountable owner’s judgment

ASKTHEPEOPLE output should never be the sole basis for a consequential decision.

## Validation record template

Copy this section into the project’s research record:

```markdown
# Human validation record

Decision:
Decision owner:
Research owner:
Date:

## ASKTHEPEOPLE input
Application commit:
Run IDs:
Source hashes:
Models/providers:
Synthetic LLM actors:
Rule-based followers:
Repeated runs:
Human respondents in synthetic run: 0

## Human study
Target population:
Method:
Recruitment:
Invited:
Consented:
Completed:
Field dates:
Instrument version:
Consent/privacy review:
Accessibility/language support:
Analysis plan:

## Results
Supported synthetic paths:
Contradicted synthetic paths:
Important paths missing from the simulation:
Unexpected human findings:
Sampling and measurement limitations:

## Decision
Evidence used:
Evidence rejected:
Remaining uncertainty:
Decision and rationale:
Approvals:
```

## Publishing language

Acceptable:

> ASKTHEPEOPLE generated three synthetic scenario paths. We then conducted 18
> interviews with separately recruited participants. Interview recruitment and
> limitations are described below. The synthetic actors are not included in the
> participant count.

Not acceptable:

> ASKTHEPEOPLE surveyed thousands of people and predicted the most likely
> outcome.

## Product requirements not yet implemented

For the application itself to support this handoff, it should eventually:

- Persist the current run manifest in durable, append-only or tamper-evident
  storage.
- Separate source facts, assumptions, synthetic observations, and human evidence
  in its data model and interface.
- Show “0 human respondents” on every synthetic screen and export.
- Export an assumption register and research-question set.
- Record, but not fabricate, external validation metadata.
- Prevent synthetic actor counts from being displayed as respondent counts.
- Remove or rename uncalibrated confidence scores.
- Support run comparison across models, assumptions, and repetitions.
- Preserve contradictions rather than optimizing for agreement.
