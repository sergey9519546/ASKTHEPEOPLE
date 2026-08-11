# ASKTHEPEOPLE

## See the paths before you choose

ASKTHEPEOPLE is an experimental tool for **synthetic scenario exploration and
pretesting**. Give it source material and a decision to examine; it constructs a
model-generated social environment, runs possible interaction paths, and helps a
team find assumptions and questions worth testing with real people.

> **Human respondents: 0. Evidence type: synthetic. Not a survey, public-opinion
> measure, forecast, prediction, or digital twin.**

The product name is a call to complete the process by asking people. It is not a
claim that the software has already done so.

## What it does

1. Accepts source material and a scenario question.
2. Extracts entities and relationships into a knowledge graph.
3. Generates synthetic personas from that material with a language model.
4. Runs those personas in OASIS-powered, Twitter-like and Reddit-like
   environments.
5. Records model-generated posts, comments, actions, optional follow-up
   answers, and internal network metrics.
6. Uses a report agent to organize the synthetic run into possible paths,
   assumptions, and follow-up questions.
7. Hands those questions to a separate real-human validation process.

ASKTHEPEOPLE is most useful at the beginning of a decision: widening the set of
possibilities, challenging a plan, and designing better research. It cannot tell
you what people will do.

## Read every output correctly

| The product shows | What it means | What it does not mean |
| --- | --- | --- |
| Synthetic agents | Language-model or rule-based actors created from supplied context | Sampled, recruited, or consenting people |
| Posts, comments, and follow-up answers | Generated events inside one simulated run | Observed statements, testimony, or preferences |
| Scenario paths | Coherent branches worth investigating | Probabilities or forecasts |
| Run metrics | Descriptions of the synthetic interaction graph | Population statistics or validated social-science measures |
| Within-run trace examples | Generated records selected after report creation by keyword overlap | Proof, support, a citation, or exact lineage for a report statement |
| Numeric evidence scores | Current implementation heuristics attached by source type | Calibrated confidence, likelihood, or error bounds |

The trace examples are a post-hoc inspection aid, not citations. They show
generated records that share keywords with a report section; they do not show
that a record caused or supports a particular statement. The reporting model is
still interpreting output produced by other models in the same pipeline. That
circularity does not validate the result against human behavior.

## Good uses

- Generate several plausible consequences before choosing a policy, product, or
  communication approach.
- Make hidden assumptions and missing stakeholders visible.
- Red-team a plan by exploring failure paths and second-order effects.
- Turn broad uncertainty into interview, survey, workshop, or pilot questions.
- Compare qualitative branches under explicitly different inputs.
- Explore fictional narratives or educational exercises.

## Do not use it for

- Measuring public opinion, sentiment, preferences, or voting intention.
- Replacing surveys, interviews, focus groups, field studies, or domain experts.
- Forecasting events, market movement, adoption, behavior, or policy impact.
- Ranking paths by likelihood when no external calibration exists.
- Inferring causal effects.
- Making decisions about a real person’s employment, credit, housing, insurance,
  education, healthcare, legal status, benefits, or access to essential services.
- Political persuasion or targeting, election interference, surveillance,
  impersonation, deceptive content, or manufactured consensus.
- Financial trading, market manipulation, legal conclusions, medical advice,
  safety-critical operation, or emergency response.
- Profiling protected or sensitive traits, especially when the inferred profile
  could affect a real person.

See the complete [appropriate-use policy](docs/APPROPRIATE_USE.md).

## Validation with people

Synthetic exploration is **phase one**, not the answer. Before using a scenario
to support a consequential decision:

1. Record the source material, assumptions, model/provider, configuration, and
   generated population composition.
2. Run multiple variants and repetitions; treat instability as a finding.
3. Convert scenario branches into testable questions.
4. Recruit an appropriate human sample with consent and suitable privacy
   protections.
5. Compare human findings with the synthetic paths, including contradictions and
   missing paths.
6. Base the decision on fit-for-purpose real evidence and accountable human
   judgment.

The application does not currently recruit people or collect a representative
human sample. A button or stage named “Validate with people” is a handoff to a
real research process, not an automated validation claim. Use the
[validation handoff guide](docs/VALIDATE_WITH_PEOPLE.md).

## Current methodological status

This repository is an experimental prototype. At the time of this documentation
review:

- No benchmark demonstrates that its agents represent a specified population.
- No prospective backtest demonstrates forecast accuracy.
- No calibration curve maps output scores to real-world likelihoods.
- No causal identification strategy is implemented.
- No end-to-end seed and model-version manifest guarantees reproducibility.
- Internal graph metrics validate computation inside a run, not external truth.
- Persona generation may add details absent from the source and can reproduce
  model stereotypes.
- Outputs can change with model, provider, prompt, temperature, source parsing,
  concurrency, dependency, and external-service changes.

The detailed claim boundary and pipeline are in
[Methodology](docs/METHODOLOGY.md).

## Minimum disclosure for shared output

Do not share a screenshot, report, export, or presentation without keeping this
disclosure adjacent to it:

```text
ASKTHEPEOPLE synthetic scenario exploration
Human respondents: 0
Evidence: model-generated scenario data
Interpretation: possible paths, not a forecast or measure of public opinion
External human validation: none unless separately documented
```

If real-human work has been completed, do not merge it silently with synthetic
output. Report the human study separately, including its sample, recruitment,
instrument, dates, limitations, and consent/privacy procedures.

## How the system is organized

```text
Source material + scenario question
                |
                v
        Entity/relationship graph
                |
                v
       Synthetic persona generation
                |
                v
     OASIS social-environment runs
                |
                v
 Generated actions + internal run metrics
                |
                v
   Scenario report and assumption register
                |
                v
     Separate validation with real people
```

Core implementation:

- `backend/app/api/`: Flask HTTP and WebSocket routes
- `backend/app/services/`: graph, persona, simulation, evidence, and reporting
  modules
- `backend/scripts/`: Twitter-like, Reddit-like, and parallel simulation runners
- `frontend/src/`: Vue application
- `backend/tests/` and `frontend/src/__tests__/`: automated checks

Technology includes Flask, Vue, OASIS/CAMEL, Zep graph memory, OpenAI-compatible
language-model endpoints, SQLite/JSONL artifacts, and NetworkX.

## Local development

### Requirements

- Python 3.11 or 3.12
- `uv`
- Node.js 24
- An OpenAI-compatible language-model endpoint
- A Zep Cloud API key

### Setup

```bash
git clone https://github.com/sergey9519546/ASKTHEPEOPLE.git
cd ASKTHEPEOPLE

# PowerShell
Copy-Item .env.example .env

# macOS/Linux
# cp .env.example .env

# Add provider and Zep credentials to .env, then:
npm run setup:all
npm run dev
```

The development command starts the Flask backend and Vite frontend together.
Use the local URL printed by Vite.

Never commit `.env`. Source material, generated profiles, and prompts may be sent
to configured third-party model and memory providers. Do not upload personal,
confidential, regulated, or copyrighted material unless you have authority to
process it and have evaluated those providers’ data practices.

### Verification

```bash
npm run verify
```

### Container

This path requires Docker Compose 2.24 or newer so a missing runtime env file
fails closed through the long-form `env_file.required` contract.

```bash
set -euo pipefail
umask 077
test ! -e .env.transition
test ! -e .env.transition.build
install -m 600 .env.transition.example .env.transition
install -m 600 .env.transition.build.example .env.transition.build
printf 'BUILD_REVISION=%s\n' "$(git rev-parse HEAD)" > .env.transition.build
# Fill required blanks with newly issued credentials and strong secrets;
# boost/search keys are optional.
python3 backend/scripts/validate_transition_build_identity.py \
  --build-env .env.transition.build
python3 backend/scripts/prepare_transition_storage.py
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build config --quiet
env -u BUILD_REVISION docker compose \
  --env-file .env.transition.build up --build -d
```

This is a **TRANSITION single-host demo topology**: web, worker, beat, and Redis
share one host and one uploads mount. Compose interpolation uses only the
ignored `.env.transition.build`; containers receive secrets only from the
separate mode-0600 `.env.transition`. Neither path uses the developer `.env`.
The identity preflight also refuses staged, tracked, or untracked worktree
changes so the image cannot claim a clean commit while containing different
source. A separate storage preflight claims only the dedicated ignored
`.transition-data/uploads` store; it never mounts normal development uploads.
A zero-recurring-bill host does not guarantee zero end-to-end cost:
model, memory, and search provider tiers must be checked before every connected
demo. This is not production or canonical-persistence evidence. For its
restrictions, required secrets, cost boundary, verification, and release
process, see the [release runbook](docs/release/RUNBOOK.md).

## Documentation

**Start here:** the production documentation system is at
[`docs/README.md`](docs/README.md). It is the normative authority for the
product, methodology, security, privacy, and architecture. 12 ADRs, 48
modular docs, validated by [`tools/validate_docs.py`](tools/validate_docs.py).

For agents and CI, the operational contract is at
[`AGENTS.md`](AGENTS.md).

- [Product Truth Contract](docs/product/PRODUCT_TRUTH_CONTRACT.md) — non-negotiable claim boundary
- [Methodology](docs/product/METHODOLOGY.md) — canonical scenario method
- [Use Policy](docs/product/USE_POLICY.md) — allowed, elevated, and prohibited uses
- [Architecture overview](docs/architecture/index.md) — project-specific, with `file:line` references
- [Data model](docs/architecture/data-model.md) and [state machines](docs/architecture/state-machines.md)
- [ADRs](docs/architecture/adr/README.md) — 12 accepted architecture decisions
- [Threat model](docs/security/THREAT_MODEL.md), [secure source ingestion](docs/security/SOURCE_INGESTION.md), [incident response](docs/security/INCIDENT_RESPONSE.md)
- [Privacy: data map](docs/privacy/DATA_MAP.md), [retention](docs/privacy/RETENTION.md), [subprocessors](docs/privacy/SUBPROCESSORS.md)
- [AI: prompt registry](docs/ai/PROMPT_REGISTRY.md), [evals](docs/ai/EVALS.md), [model releases](docs/ai/MODEL_RELEASES.md), [failure modes](docs/ai/FAILURE_MODES.md)
- [Design Direction C — Civic Wayfinding](docs/design/DIRECTION_C.md), [route grammar](docs/design/ROUTE_GRAMMAR.md), [accessibility](docs/design/ACCESSIBILITY.md), [content system](docs/design/CONTENT_SYSTEM.md)
- [Execution plans](docs/exec-plans/README.md) (8 plans, dependency-ordered)
- [Release acceptance](docs/release/ACCEPTANCE.md) and [runbook](docs/release/RUNBOOK.md)
- [Source register](docs/SOURCES.md) — research and standards backing the docs

Project-specific lineage and license attributions live at the repo root:

- [Project provenance and lineage](PROVENANCE.md)
- [Third-party software and media notices](THIRD_PARTY_NOTICES.md)

The full integration audit is at
[`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](ASKTHEPEOPLE_GODMODE_BUILDPLAN.md).
The integration procedure is at
[`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md). Pre-authority legacy
documents are archived at
[`docs/archive/legacy-2026-07-29/`](docs/archive/legacy-2026-07-29/README.md)
with a per-file reconciliation map.

## Research basis for the caution

The product framing follows the
[AAPOR 2026 guidance on responsible AI in survey research](https://aapor.org/wp-content/uploads/2026/05/Responsible-AI-Integration-In-Survey-Research.pdf),
which identifies serious validity and disclosure risks when synthetic responses
are used beyond clearly labeled pretesting, pilot work, or exploratory
diagnostics. AAPOR’s minimum disclosures include how AI was used, the number of
human respondents, and the validation and human oversight performed.

Recent evaluations also show why behavioral realism must be demonstrated rather
than assumed:

- [Can LLM Agents Simulate Multi-Turn Human Behavior? (ACL 2026)](https://aclanthology.org/2026.acl-long.2034/)
  reports a large gap between believable behavior and action-level accuracy in
  its evaluated shopping setting.
- [LLM Agents Predict Social Media Reactions but Do Not Outperform Text
  Classifiers (2026 preprint)](https://arxiv.org/abs/2604.19787) finds some
  predictive signal in its benchmark, but conventional supervised text
  classifiers perform better on the reported chance-corrected metric.
- [Too human to model (npj Complexity, 2026)](https://www.nature.com/articles/s44260-026-00075-1)
  explains tensions between expressive LLM behavior and the abstraction,
  interpretability, and intervention logic expected of useful models.

These studies do not directly validate or invalidate every ASKTHEPEOPLE use.
They demonstrate that performance is task-specific and that fluent behavior is
not sufficient evidence of human fidelity.

## Provenance, acknowledgments, and license

ASKTHEPEOPLE is an adaptation of
[MiroFish by 666ghj and contributors](https://github.com/666ghj/MiroFish). The
shared Git history begins with upstream commit
`38e3d05b1d33d13fcbadc83ec0c4bf84c878e828`; subsequent ASKTHEPEOPLE work
modifies the application, runtime, interface, testing, operations, and product
framing. See the auditable [provenance record](docs/PROVENANCE.md).

The social-environment simulation is powered by
[OASIS from CAMEL-AI](https://github.com/camel-ai/oasis); its design is described
in the [OASIS paper](https://arxiv.org/abs/2411.11581).

This repository is distributed under the
[GNU Affero General Public License v3.0](LICENSE). Dependency and upstream
licenses continue to apply to their respective components. This notice is not a
substitute for reviewing the license text.
