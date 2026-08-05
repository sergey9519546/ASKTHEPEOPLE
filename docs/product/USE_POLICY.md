---
title: "Use Policy"
status: "Normative"
version: "1.1.0"
owner: "Trust + Safety + Product + Legal"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "8b616dc7fa02eeed5ada8c51998d8b197be28f8d"
baseline_audit: "ASKTHEPEOPLE_GODMODE_BUILDPLAN.md §1–§6"
applies_to: "every HTTP route, every prompt, every export, every generated response, every model call"
---

# Use Policy

> **Document authority.** The capitalized terms **MUST**, **MUST NOT**, **SHOULD**,
> **SHOULD NOT**, and **MAY** are normative. A feature is not complete merely
> because the interface resembles the design; it must satisfy the domain,
> methodological, security, accessibility, and evidence requirements in this
> documentation system. Where this document conflicts with generated output,
> legacy copy, or an implementation convenience, this document controls until
> superseded through an approved architecture or product decision record.
> **Research status.** This document distinguishes binding product policy from
> external standards and research. External sources inform the requirements but
> do not automatically make the product compliant, valid, accurate, or fit for a
> particular legal jurisdiction. Legal and human-subject review remain separate
> launch responsibilities.

## Purpose

This policy determines whether a decision may enter the product, what safeguards
are required, and which capabilities must be refused. The final classification
is made by a deterministic server-side policy engine. A model MAY recommend a
classification but MUST NOT override policy.

## Policy outcomes

| Outcome | Product behavior |
|---|---|
| `ALLOWED` | Standard workflow with normal review gates |
| `ELEVATED_REVIEW` | Named reviewer, restricted outputs, stronger logging, and domain-specific approval |
| `PROHIBITED` | Refuse before source processing or model invocation; retain minimum audit metadata |
| `OUT_OF_SCOPE` | Explain that the product is not the appropriate method and provide a research-planning alternative |

## Use-risk policy

### Allowed by default

- Generate alternative implementation scenarios.
- Surface assumptions and missing information.
- Stress-test service or program designs.
- Prepare interview, workshop, observation, or survey instruments for later real research.
- Compare the effect of changing one assumption.
- Explain a completed synthetic run.
- Generate fictional profile responses when explicitly selected and visibly labeled.

### Elevated review required

- Public policy with material effects on rights or access.
- Health, safety, education, finance, housing, employment, or legal-adjacent topics used only for research planning.
- Decisions involving minors or vulnerable populations.
- Highly sensitive demographic or identity attributes.
- Public-interest communications that could materially influence behavior.

For elevated-risk runs:

- show an additional scope notice;
- require a named reviewer;
- prohibit direct recommendations or rankings;
- require a human-validation handoff before export;
- log the decision purpose and intended downstream use;
- prevent generated responses from being shared without the full disclosure block.

### Prohibited

- Claiming or implying real respondents, participants, public opinion, polling, survey results, measured sentiment, or predicted behavior.
- Election forecasting, voter targeting, political persuasion optimization, or synthetic polling.
- Deciding eligibility, employment, credit, insurance, housing, medical treatment, legal status, educational access, or public benefits.
- Generating a replica or “digital twin” of an identifiable person without a separately reviewed lawful basis and explicit consent; this capability is out of scope for the product.
- Generating fake testimonials, reviews, endorsements, constituent comments, public submissions, or evidence.
- Creating synthetic research to conceal the absence of human research.
- Targeting or manipulating protected, vulnerable, or highly sensitive groups.
- Inferring sensitive traits that the user did not explicitly and lawfully provide.
- Autonomous publishing, outreach, recruitment, or execution of a decision.

The server—not only the prompt—must enforce this policy.

---
## Consequential-decision rule

ASKTHEPEOPLE MUST NOT be used to make, recommend, rank, or materially influence
a decision about an identifiable person's:

- employment or worker management;
- credit, lending, insurance, or housing;
- education admission or discipline;
- healthcare diagnosis, treatment, eligibility, or access;
- legal status, benefits, immigration, or essential services;
- biometric, emotion, or protected-trait classification;
- safety-critical or emergency response.

It MAY be used to plan **general, non-person-specific research questions** about
a service or policy only when the workflow cannot generate an eligibility,
risk, priority, or treatment decision about a person.

## Political and civic integrity

The product MUST refuse:

- persuasion or targeting of voters or protected groups;
- election-outcome simulation presented as a forecast;
- manufactured consensus, fake grassroots content, or impersonation;
- public-opinion measurement without real respondents and valid methods;
- surveillance or profiling of political beliefs;
- candidate or issue messaging optimized against generated “voters.”

General civic-service design, public-meeting planning, and policy scenario
work MAY be allowed when the truth layer remains explicit and no persuasion,
targeting, public-opinion, or prediction claim is produced.

## Sensitive attributes

The system MUST NOT infer a sensitive attribute from source material or use it
to create a generated profile unless:

1. the attribute is demonstrably necessary for an allowed research-planning
   objective;
2. the user explicitly supplies and approves it;
3. a named reviewer approves the use;
4. the profile describes a functional access condition rather than a stereotype;
5. the attribute is never linked to a real person;
6. retention and export restrictions are applied.

## Data-rights and authority attestation

Before upload, the user MUST attest that they are authorized to process the
material and that the chosen providers, retention, and region are acceptable.
This attestation does not transfer legal responsibility to the product and does
not cure unlawful processing.

## Enforcement architecture

The policy engine MUST evaluate:

- decision text and intended use;
- declared domain and stakes;
- whether identifiable people are targeted;
- requested output mode;
- source classifications;
- destination/export type;
- organization policy overlays;
- jurisdictional configuration;
- prior policy events and abuse signals.

The response MUST include stable reason codes. Free-text explanations are
secondary.

```json
{
  "classification": "elevated_review",
  "reason_codes": ["CIVIC_POLICY_CONTEXT", "AFFECTED_GROUPS"],
  "required_controls": ["NAMED_REVIEWER", "NO_PERSUASION_OUTPUT"],
  "prohibited_capabilities": ["PUBLIC_OPINION_SCORE", "TARGETING"],
  "policy_version": "use-policy-1.0.0"
}
```

## Abuse handling

Suspected misuse MAY result in:

- run cancellation;
- export revocation;
- organization-level capability restrictions;
- preservation of minimum security evidence;
- account suspension;
- legal or regulatory escalation where required.

## Claim integrity and regulatory triggers

### Consumer-protection claims

No marketing or in-product claim of accuracy, efficacy, human equivalence, representativeness, bias freedom, or prediction may ship without competent, reliable, use-specific evidence. FTC actions against unsupported AI performance and substitution claims make this a release concern, not merely copy preference.([FTC Workado accuracy-claims order](https://www.ftc.gov/news-events/news/press-releases/2025/08/ftc-approves-final-order-against-workado-llc-which-misrepresented-accuracy-its-artificial))([FTC DoNotPay order](https://www.ftc.gov/news-events/news/press-releases/2025/02/ftc-finalizes-order-donotpay-prohibits-deceptive-ai-lawyer-claims-imposes-monetary-relief-requires))

## Claim registry

Create a versioned registry for every substantive product claim:

```yaml
claim_id: no-human-respondents
surface: product-ui
claim: "0 human respondents"
status: approved
support: domain invariant
owner: product-trust
review_date: 2026-07-29

claim_id: improves-research-planning
surface: marketing
claim: "Helps teams turn assumptions into questions for human validation"
status: test-required
support:
  - moderated usability study
  - handoff completion data
prohibited_variants:
  - "replaces research"
  - "predicts human response"
```

Marketing CI should fail when an unregistered high-risk claim appears.

## Incident response

Incident classes:

- cross-tenant disclosure;
- prompt injection succeeded;
- source content affected system instructions;
- incorrect origin label;
- export missing disclosure;
- prohibited-use generation;
- model/prompt regression;
- source parser vulnerability;
- signing/provenance failure;
- sensitive-data exposure;
- unsupported public claim.

Required incident capabilities:

- identify affected prompt/model/source/run versions;
- disable prompt/model configuration by feature flag;
- stop queued runs;
- revoke shared artifacts;
- notify affected users where appropriate;
- preserve investigation evidence;
- document root cause and corrective action;
- add regression tests before re-enable;
- publish user-facing correction when an exported artifact was materially misleading.

---
## Policy tests

The release test corpus MUST include:

- benign allowed examples;
- near-boundary elevated examples;
- prohibited examples with euphemisms;
- multilingual and obfuscated requests;
- attempts to reframe polling as simulation;
- attempts to use profiles for protected-trait targeting;
- attempts to generate individualized high-impact recommendations;
- requests to remove disclosures from exports;
- prompt-injected documents that request prohibited actions.

Critical prohibited cases require a 100% block rate on the maintained release
corpus. False-positive rates MUST be measured and reviewed rather than hidden.

## References

- [AAPOR, Responsible AI Integration in Survey Research (2026)](https://aapor.org/announcements/task-force-on-responsible-ai-integration-in-survey-research-report/) — Professional guidance on validity, reliability, sensitivity, performance, transparency, and human oversight when AI is used in survey research.
- [NIST AI Risk Management Framework 1.0 and GenAI Profile](https://www.nist.gov/itl/ai-risk-management-framework) — Voluntary framework and GenAI profile for governing, mapping, measuring, and managing AI risk.
- [European Commission Article 50 transparency guidelines](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) — Final July 2026 guidance on transparency obligations that apply from 2 August 2026.

---

## Project-specific enforcement status (baseline `8b616dc7`)

This section maps every clause above to the actual code under
[`backend/app/`](../../backend/app/) and the existing CI checks in
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml). Items are
marked **CURRENT** (implemented and verified), **PARTIAL** (implemented but
materially deficient against the clause), or **TARGET** (clause is
normative; the implementation has not reached it). See
[`docs/architecture/index.md`](../architecture/index.md) for the legend.

## Application-level enforcement — PARTIAL

The current `create_app()` factory
([`app/__init__.py:25`](../../backend/app/__init__.py:25)) is the only
deterministic server-side policy today. It enforces:

- A constant-time bearer-token comparison via `hmac.compare_digest` on every
  `/api/*` request when `APP_TOKEN` is set
  ([`app/__init__.py:125-141`](../../backend/app/__init__.py:125));
- Fail-closed application creation if `REQUIRE_APP_AUTH` is set and
  `APP_TOKEN` is missing or weak
  ([`app/__init__.py:30-39`](../../backend/app/__init__.py:30));
- Production CORS lockdown — `CORS_ORIGINS='*'` is refused in non-debug mode
  and replaced with `http://127.0.0.1`
  ([`app/__init__.py:74-82`](../../backend/app/__init__.py:74));
- Production stripping of `traceback` and 5xx `error` strings
  ([`app/__init__.py:198-226`](../../backend/app/__init__.py:198));
- Per-route rate limits via `flask-limiter` and the `RateLimitExceeded` →
  `429 {"success": false, "error": "rate_limit_exceeded"}` handler
  ([`app/__init__.py:254-261`](../../backend/app/__init__.py:254));
- `SafePathError` → `400 {"success": false, "error": "invalid_id"}` for any
  unsafe path traversal attempt
  ([`app/__init__.py:263-267`](../../backend/app/__init__.py:263)).

**Gap:** there is no deterministic per-decision policy engine that
classifies a run as `ALLOWED`, `ELEVATED_REVIEW`, `PROHIBITED`, or
`OUT_OF_SCOPE` based on the decision text, the intended use, the affected
groups, or the requested output mode. The current code relies on convention
and on the `validation_engine` and `claim_boundary` services to catch
post-hoc violations. The policy engine is **TARGET** and is part of gate 0
(see
[`docs/exec-plans/00-repository-census-and-governance.md`](../exec-plans/00-repository-census-and-governance.md)
and the audit's P0 cluster).

## Consequential-decision rule — PARTIAL

The current application does not embed a per-decision policy check, but the
outer security boundary provides a partial guard: the bearer-token
middleware refuses unauthenticated traffic and the in-memory rate limiter
caps request volume
([`app/api/__init__.py:36-42`](../../backend/app/api/__init__.py:36)).
None of the seven enumerated decision categories (employment, credit,
housing, education, healthcare, legal, biometric, safety-critical) is
specially classified in code.

**Gap:** every route that creates a simulation accepts a free-text
`simulation_requirement`
([`models/project.py:48-49`](../../backend/app/models/project.py:48)) and
does not classify it. The policy engine and the decision-class registry
are **TARGET**.

## Political and civic integrity — PARTIAL (defense in depth)

The Civic Wayfinding design direction
([`docs/design/DIRECTION_C.md`](../design/DIRECTION_C.md)) is a research-
planning visual system. It is intentionally not a polling, persuasion, or
targeting interface. The semantic route list
([`adr/ADR-0006-route-map-list-parity.md`](../architecture/adr/ADR-0006-route-map-list-parity.md))
makes "possible path" the canonical term and forbids rendering
probability/support/prevalence visually. The Truth Rail and prohibited-
language linter in
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) block
the words "predict what people will do", "know what people think",
"representative synthetic sample", "human-level accuracy", "digital twin",
"bias-free personas", and "scientifically proven simulation" in
`docs/product/`, `docs/design/`, `docs/release/`, and the repo root
`README.md`.

**Gap:** there is no in-product refusal flow. A user pasting a civic-policy
question into `simulation_requirement` will start a run today. The policy
engine that classifies and refuses is **TARGET** and is part of gate 0.

## Sensitive attributes — TARGET

The application does not currently infer sensitive attributes from source
material. The current `validation_engine`
([`services/validation_engine.py`](../../backend/app/services/validation_engine.py))
checks the request schema and the prompt-output schema; it does not
classify protected traits. The `ontology_generator` and
`oasis_profile_generator` use the LLM to invent profile dimensions from
the source material; whether a profile dimension is a "sensitive
attribute" in the sense of this policy is **not** classified by the code.

**Gap:** the attribute-classification layer and the named-reviewer gate
are **TARGET**. Tracked in
[`docs/exec-plans/02-tenancy-data-and-secure-ingestion.md`](../exec-plans/02-tenancy-data-and-secure-ingestion.md).

## Data-rights and authority attestation — PARTIAL

The current upload route
([`api/graph.py`](../../backend/app/api/graph.py)) accepts a file via
`FileStorage` and persists it under
`backend/uploads/projects/{project_id}/files/{uuid}{ext}`
([`models/project.py:247-278`](../../backend/app/models/project.py:247))
with a randomized safe filename. There is no pre-upload attestation
captured in the schema, and no provider/region attestation either.

**Gap:** the pre-upload attestation UI and the provider/region selector are
**TARGET** and are part of gate 1 (typed API boundary).

## Enforcement architecture — PARTIAL (state and audit)

The `state.json` per simulation
(`backend/uploads/simulations/{simulation_id}/state.json`)
is not a database, has no constraints, no audit log, and no transactional
boundary. The `TaskManager`
([`models/task.py:114`](../../backend/app/models/task.py:114)) records
per-task status (PENDING, PROCESSING, COMPLETED, FAILED) and a
`public_error` field for client-safe error codes, but it is process-local
and best-effort to Redis.

**Gap:** the policy-engine response contract (with stable reason codes
`CIVIC_POLICY_CONTEXT`, `AFFECTED_GROUPS`, etc.) is **TARGET** and requires
the canonical persistence layer per
[`adr/ADR-0012-canonical-transactional-and-object-persistence.md`](../architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md).

## Abuse handling — TARGET

The current application does not have a run-cancellation or export-
revocation endpoint. Stop is a route flag
(`stop_simulation` in
[`api/routes/execution_routes.py`](../../backend/app/api/routes/execution_routes.py))
that sets the simulation to "paused" in the audit's terminology, and
`close_environment` is a separate route. The current state is the
audit-flagged contradictory lifecycle semantics. The durable workflow that
supports cancellation, revocation, and audit-grade redaction is
**TARGET** and is gate 2, owned by `askthepeople-orchestration-engineer`.

## Claim integrity — PARTIAL (CI) + TARGET (registry)

The CI workflow
[`.github/workflows/docs.yml`](../../.github/workflows/docs.yml) blocks
prohibited marketing language in `docs/product/`, `docs/design/`,
`docs/release/`, and the repo root `README.md`. The list checked by the
linter today:

```text
predict what people will do
predict public response
ask thousands of people instantly
know what people think
human-level accuracy
digital twin of (your|the) (audience|users|customers|people)
bias-free personas
scientifically proven (people |)simulation
representative synthetic sample
validate the decision (with|using) ASKTHEPEOPLE
```

**Gap:** there is no claim registry (Claim ID, exact approved wording,
owner, evidence, scope, limitations, approval, expiry, surfaces, rollback).
The registry is **TARGET** and is part of gate 5 (evals, accessibility,
release), owned jointly by `askthepeople-ai-eval-steward` and
`askthepeople-release-operator`.

## Policy tests — PARTIAL (corpus), TARGET (release gate)

The current test suite under `backend/tests/` covers request schema,
extraction, ontology, and graph builder unit tests. It does not yet
include the corpus of:

- benign allowed examples;
- near-boundary elevated examples;
- prohibited examples with euphemisms;
- multilingual and obfuscated requests;
- attempts to reframe polling as simulation;
- attempts to use profiles for protected-trait targeting;
- attempts to generate individualized high-impact recommendations;
- requests to remove disclosures from exports;
- prompt-injected documents that request prohibited actions.

**Gap:** the policy-corpus tests and the 100% block-rate gate for
critical prohibited cases are **TARGET**. Tracked in
[`docs/exec-plans/07-evals-accessibility-and-release.md`](../exec-plans/07-evals-accessibility-and-release.md).
