# Appropriate Use and Limitations

## Policy

ASKTHEPEOPLE is for synthetic scenario exploration and pretesting. It may be
used to generate hypotheses and improve a real-human research plan. It must not
be presented as a source of human responses, public opinion, forecasts, causal
effects, or calibrated probabilities.

This document is a product safety policy, not legal advice. Operators remain
responsible for applicable law, research ethics, contracts, provider terms, and
data-governance requirements.

## Allowed uses

### Exploratory scenario planning

Generate multiple paths to widen a team’s thinking. The output must be labeled
synthetic, and important paths must remain hypotheses until externally tested.

### Assumption and stakeholder mapping

Use generated disagreement to identify missing stakeholders, contested
assumptions, research questions, or failure modes.

### Research pretesting

Draft interview prompts, workshop exercises, survey concepts, or pilot criteria.
Qualified humans must review instruments before fielding.

### Internal red-teaming

Explore how a message, policy, or product idea could be misunderstood or abused.
Do not turn synthetic criticism or support into a claim about real audiences.

### Fiction, education, and facilitation

Explore narrative branches or teach scenario-thinking when fictional and
generated elements are clearly disclosed.

## Required conditions

Before every run:

- Use a question framed as exploration: “What could happen?” rather than “What
  will happen?”
- Identify the decision owner and the cost of a wrong inference.
- Confirm authority to process the source material.
- Remove personal or sensitive information that is not essential.
- Review each configured model, graph, search, and storage provider.
- Decide how uploads, profiles, logs, and exports will be retained and deleted.

Before sharing output:

- State **Human respondents: 0**.
- State that actors, follow-up answers, posts, and metrics are synthetic.
- Keep source facts, assumptions, generated observations, and human evidence
  visually and semantically separate.
- Remove unsupported likelihood, confidence, representation, and causal language.
- Have an accountable human review the output and its intended use.

Before a consequential decision:

- Complete fit-for-purpose external validation.
- Document contradictions between synthetic and human findings.
- Use qualified domain, legal, privacy, ethics, safety, and accessibility review
  as appropriate.
- Preserve an audit record of sources, configuration, outputs, and decisions.

## Prohibited uses

Do not use ASKTHEPEOPLE to:

- Claim or imply that synthetic actors are real, recruited, sampled, consenting,
  representative, or observed people.
- Fabricate research participation, testimonials, reviews, comments, engagement,
  consensus, grassroots support, or opposition.
- Target or persuade voters, suppress participation, interfere with elections,
  or generate political disinformation.
- Make or recommend decisions about an identifiable person’s employment,
  promotion, credit, lending, housing, insurance, education, healthcare, legal
  status, public benefits, immigration, or access to essential services.
- Infer or act on protected or highly sensitive traits of identifiable people.
- Diagnose, treat, or triage medical conditions.
- Give individualized legal conclusions or determine guilt, risk, sentencing, or
  law-enforcement action.
- Direct financial trades, investment allocations, credit exposure, or market
  activity; manipulate markets; or spread unverified financial rumors.
- Conduct surveillance, social scoring, psychological targeting, or
  vulnerability exploitation.
- Impersonate a real person or attribute generated speech to one.
- Autonomously publish or send generated material to public platforms or real
  people without human review and disclosure.
- Create harassment, discrimination, fraud, malware, or other unlawful harm.
- Bypass human-subject protections, informed consent, institutional review, or
  professional standards.

## High-risk topics requiring an explicit stop

The included product templates historically covered political events, public
relations crises, finance, and regulation. Those are not evidence that such uses
are safe.

Stop the workflow and obtain qualified review when:

- An output could materially affect rights, safety, livelihood, reputation, or
  access to services.
- The source includes personal, health, financial, biometric, employment,
  education, legal, location, communications, or other sensitive data.
- The work concerns elections, protests, public safety, active conflict, minors,
  vulnerable groups, or a named individual.
- A stakeholder wants a probability, ranking, confidence score, or prediction.
- There is pressure to hide the synthetic origin of an output.
- Real-world publication or intervention is planned.
- The team cannot name the human validation method or accountable decision
  owner.

Documentation alone does not mitigate these risks. A deployment intended for
public use should enforce appropriate-use controls in the product and operating
process.

## Data and privacy

Source documents and generated artifacts can pass through third-party language
model, search, and graph-memory providers. Treat the configured provider chain as
part of the data boundary.

Minimum practice:

- Use data minimization.
- Do not upload secrets or credentials.
- De-identify or aggregate personal data where lawful and appropriate.
- Document purpose, authority, recipients, location, retention, and deletion.
- Check provider training, logging, residency, subprocessors, and retention
  terms.
- Restrict access to project artifacts and logs.
- Establish a deletion process before collecting data.
- Notify and obtain consent from real participants when required.

Synthetic profiles can still create privacy and reputational harm when they are
linked to a real person. “Generated” does not mean harmless.

## Bias and representativeness

Language models can reproduce stereotypes and overrepresent familiar,
English-language, online, or dominant-culture patterns. The application may
invent demographic or personality attributes and then treat those inventions as
behavioral inputs.

Do not correct this by merely increasing actor count. Instead:

- Remove unjustified attributes.
- Record which attributes came from sources and which were generated.
- Test sensitivity to alternate persona constructions.
- Include affected stakeholders in the human research design.
- Report missing populations and known coverage gaps.
- Treat differences across model/provider versions as uncertainty.

## Security and adversarial content

Uploaded documents and retrieved web material are untrusted input. They can
contain instructions intended to manipulate a model or expose data. Follow the
[OWASP prompt-injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
and the repository security guidance.

Do not place credentials in prompts, reports, exported HTML, filenames, or
shared screenshots.

## Governance references

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [AAPOR Responsible AI Integration in Survey Research
  (2026)](https://aapor.org/wp-content/uploads/2026/05/Responsible-AI-Integration-In-Survey-Research.pdf)
- [FTC Operation AI Comply announcement](https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-announces-crackdown-deceptive-ai-claims-schemes)
- [OWASP LLM01: Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

These are reference frameworks and enforcement examples, not certifications of
this project.

## Incident and misuse response

If output has been represented as human evidence or used for a prohibited
purpose:

1. Stop publication, automation, and further processing.
2. Preserve relevant logs and configuration without spreading sensitive data.
3. Correct the record with every recipient.
4. Notify the accountable operator, data/security owner, and legal or ethics
   reviewer as appropriate.
5. Assess affected people and downstream decisions.
6. Delete or restrict artifacts where required and lawful.
7. Document the cause and add a technical or procedural control before resuming.
