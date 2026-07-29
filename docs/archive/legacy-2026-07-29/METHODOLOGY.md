# Methodology and Claim Boundary

## Purpose

ASKTHEPEOPLE is a synthetic scenario-exploration system. Its purpose is to help
a team discover possible paths, inspect assumptions, and design questions to
take to real people.

It does not measure a population and does not estimate what will happen. A run
is best understood as a structured thought experiment executed by generative
models inside a configured social-media-like environment.

## Non-negotiable disclosure

Every unaugmented ASKTHEPEOPLE run has:

- **Human respondents:** 0
- **Evidence type:** synthetic
- **Population represented:** none established
- **Forecast status:** not a forecast
- **Public-opinion status:** not a measure of public opinion
- **External validation:** none unless a separate human study is documented

Calling a generated actor an “agent,” “persona,” or “interviewee” does not make
it a person. Asking a simulated agent a question produces another model output,
not human testimony.

## Intended question

The system can address:

> Given these sources, assumptions, generated personas, platform rules, model
> choices, and prompts, what internally coherent scenario paths might this
> particular synthetic system produce?

It cannot, without fit-for-purpose external evidence, address:

> What do people believe? What will people do? Which path is most likely? What
> caused an outcome? What will this policy, campaign, product, or event do in the
> real world?

## Pipeline

### 1. Source ingestion

The application parses uploaded PDF, Markdown, or plain-text material. The
quality and scope of the source constrain the scenario but do not fully
determine it. Parsing can omit structure, and downstream language models can add
unsupported details.

**Result:** a machine-readable representation of submitted material, not a
verified factual record.

### 2. Ontology and graph construction

A language model proposes entity types, relationships, and extracted entities.
Zep is used for graph storage and retrieval.

**Important limitations:**

- Extracted relationships can be incomplete, ambiguous, or invented.
- Salience in a source document is not the same as real-world importance.
- A graph edge is not a demonstrated causal relationship.
- Retrieval from the graph does not independently verify source truth.

### 3. Synthetic profile generation

The application turns graph entities into detailed model-generated social-media
profiles. Optional archetype expansion can create variants; optional followers
use lighter-weight rules.

Profiles may contain demographic, personality, behavioral, or biographical
details that were not present in the source. Such details are hypotheses created
by a model. They can encode cultural stereotypes or training-data bias.

Population size is a computational setting, not sample size. More synthetic
agents do not make a run statistically representative. Rule-based followers and
language-model actors must be counted separately when reporting a run.

### 4. OASIS social-environment simulation

Actors interact in Twitter-like and/or Reddit-like environments implemented with
[OASIS](https://github.com/camel-ai/oasis). The simulation records actions such
as posting, commenting, reacting, and following. Optional follow-up questions
produce additional generated answers; they are not interviews with people.

These environments are abstractions. They do not reproduce every platform rule,
recommendation system, culture, moderation action, offline influence, or
historical condition of a real community.

The [OASIS paper](https://arxiv.org/abs/2411.11581) describes the underlying
simulator. OASIS’s scalability and platform mechanics do not by themselves
establish that a specific ASKTHEPEOPLE configuration predicts a target
population.

Generated activity is stored in a per-run observation database, separate from
the Zep graph built from supplied material. Runs cannot write actions into any
graph. This prevents generated behavior from silently returning later as
apparent source evidence, including through an arbitrary graph that belongs to
another project.

### 5. Internal run metrics

The application can compute action counts, engagement inequality, community
structure, weighted within-community interaction share, cascade summaries, and
round summaries.
These are descriptive calculations over generated actions.

The current `polarization_index` is based on network modularity. Modularity is a
community-structure statistic; it is not, by itself, a validated measure of
ideological or affective polarization. The current metrics have no population
sampling error, confidence interval, or demonstrated mapping to real-world
values.

### 6. Scenario report

A report agent retrieves generated actions, posts, comments, graph information,
and optional generated follow-up answers, then produces a narrative report.

Generated actions are retrieved from the observation store and labeled as
synthetic observations. Graph retrieval is treated as record-level
provenance-unverified because a pre-existing or legacy graph may contain mixed
material; a graph record is not promoted to a supplied-source fact without a
separate source trace. CSV graph exports preserve the same conservative label.

The report view includes post-hoc trace examples that can answer:

> Which generated records share keywords with this report section and may help
> me inspect the run?

They do not answer either of these questions:

> Is this statement true outside the simulation?

> Which record caused, proves, supports, or is an exact citation for this
> statement?

The pipeline is circular: models create the personas and actions, and a model
interprets those actions. Keyword-related trace examples can make the run easier
to inspect, but they are not citations or independent corroboration.

### 7. Real-human validation handoff

The output should become an assumption register and research plan. Human
interviews, surveys, workshops, pilots, observational data, domain expertise, or
other fit-for-purpose methods are then used to test the important paths.

The current application does not recruit respondents or create a representative
human sample. See [Validate with People](VALIDATE_WITH_PEOPLE.md).

## Evidence classes

Keep these classes separate in every report:

| Class | Example | Permitted interpretation |
| --- | --- | --- |
| Source material | A policy draft uploaded by the user | The document says this; factual status may still require verification |
| Configuration assumption | “Weekend riders adapt to weekday-only service” | The run assumes this |
| Synthetic observation | A generated agent posts an objection | This occurred inside this run |
| Internal metric | 60% of generated edges are within communities | This describes this generated graph |
| Model interpretation | Report agent identifies a “pushback” path | The model summarized a synthetic pattern |
| External human evidence | Consented interviews with documented recruitment | These participants reported this |
| External behavioral evidence | Observed outcomes from a defined population and period | This occurred in the measured setting |

Do not combine synthetic and external counts into one percentage. Do not label a
synthetic observation as a respondent answer.

## Numeric scores and calibration

The current evidence package assigns fixed heuristic scores based on generated
record type. Those values are not learned from outcome data and have not been
calibrated. They must not be presented as confidence, probability, forecast
accuracy, or strength of evidence.

Before any future score can be interpreted probabilistically, the project would
need a declared target event, reference class, timestamped prospective
predictions, representative ground truth, held-out evaluation, calibration
curves, drift monitoring, and uncertainty reporting.

## Reproducibility

Exact reruns are not currently guaranteed. Sources of variation include:

- Model and provider version changes
- Prompt and code changes
- Model sampling parameters and nondeterminism
- Source parsing and graph extraction
- Asynchronous execution and action ordering
- OASIS, CAMEL, Zep, and other dependency changes
- External search or memory-service state
- Retries, timeouts, and partial failures
- Archetype expansion and rule-based follower behavior

For an auditable run, preserve at least:

- Application Git commit
- Date and time
- Source-file hashes and a record of authorized use
- Model/provider identifiers for each stage
- Prompts and relevant parameters
- Ontology and extracted graph snapshot
- Agent construction method and counts by actor type
- Platform configuration, events, and round limits
- All generated action logs and report inputs
- Failed, retried, excluded, or manually edited outputs
- Number of repeated runs and supported random seeds
- Human reviewer decisions

The application now creates a per-run manifest with the application revision,
artifact hashes, resolved model configuration, preflight result, and explicit
reproducibility limitations. That file is stored beside the run artifacts; it is
not yet durable, append-only, independently signed, or a complete capture of
every prompt and provider-side version. “Reproducible” therefore must not be
claimed.

## Validity requirements

Validity is use-case-specific. A successful smoke test, plausible prose, internal
consistency, or attractive visualization does not demonstrate behavioral
validity.

Before using a model for a real-world inference, define:

1. The target population and context.
2. The target behavior or outcome.
3. The time horizon.
4. A meaningful baseline.
5. A held-out human or behavioral reference dataset.
6. Accuracy, reliability, sensitivity, and calibration criteria.
7. Expected failure costs and stop conditions.
8. Ongoing drift and revalidation procedures.

The [AAPOR 2026 Responsible AI Integration in Survey Research
report](https://aapor.org/wp-content/uploads/2026/05/Responsible-AI-Integration-In-Survey-Research.pdf)
emphasizes task-specific validity, performance, sensitivity, reliability, human
involvement, documentation, and disclosure. It identifies particularly serious
risks when synthetic responses replace human respondents outside clearly
labeled pretesting, pilot work, or exploratory diagnostics.

## What current research supports

Current research supports caution, not a universal conclusion about all agent
systems:

- [Can LLM Agents Simulate Multi-Turn Human Behavior? (ACL
  2026)](https://aclanthology.org/2026.acl-long.2034/) quantitatively evaluates
  action-level imitation in online shopping and reports a substantial gap
  between believable and accurate behavior in that setting.
- [LLM Agents Predict Social Media Reactions but Do Not Outperform Text
  Classifiers (2026 preprint)](https://arxiv.org/abs/2604.19787) reports signal
  above chance in one social-reaction benchmark while showing better performance
  from a conventional text classifier on the paper’s chance-corrected metric.
- [Too human to model (npj Complexity,
  2026)](https://www.nature.com/articles/s44260-026-00075-1) discusses why
  expressive, human-like agent behavior can conflict with model abstraction and
  interpretability.

These sources are not an evaluation of this repository. ASKTHEPEOPLE requires
its own use-case-specific external validation.

## Required wording

Preferred:

- “possible scenario path”
- “synthetic actor”
- “generated action”
- “within-run trace”
- “descriptive run metric”
- “hypothesis to validate”
- “0 human respondents”

Avoid unless supported by a separately documented human study or calibration:

- “people think”
- “public opinion”
- “respondents”
- “the public will”
- “high fidelity”
- “realistic population”
- “digital twin”
- “prediction”
- “forecast”
- “likely outcome”
- “precise trajectory”
- “evidence-based recommendation”
- “confidence”

## Change-control rule

Any future claim that the product represents, measures, predicts, or replaces
people requires a documented validation package reviewed by qualified research,
legal/ethics, product, and domain owners. A marketing copy change is not enough.
