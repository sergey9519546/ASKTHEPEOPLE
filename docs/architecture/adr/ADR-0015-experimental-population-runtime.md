---
title: "ADR-0015: Reviewed experimental synthetic populations"
status: "Proposed"
version: "0.2.0"
owner: "Architecture, Product, Research"
last_reviewed: "2026-10-31"
review_cycle: "On acceptance or material change"
research_cutoff: "2026-10-31"
implements_gate: "none (proposal; does not alter release gates)"
---

# ADR-0015: Reviewed experimental synthetic populations

## Context

The user requested a stronger population simulator and comparison with
[MiroFish](https://github.com/666ghj/MiroFish/tree/7657031ac01184afe2cb220f5ee3545573b5e843).
The pinned upstream preparation path feeds entity-derived profiles to OASIS.
Local default preparation returns reviewed functional lenses instead
([`SimulationManager.prepare_simulation`](../../../backend/app/services/simulation_manager.py)),
and local execution admission reconstructs the approved lens configuration
([`assert_decision_lens_execution_admission`](../../../backend/app/services/simulation_preflight.py)).
Prepared population-profile artifacts cannot substitute for that approval.

[ADR-0001](ADR-0001-product-category-and-truth-contract.md) defines generated
scenario exploration, zero human respondents, and a nonforecast boundary.
The build plan additionally constrains profiles to functional lenses.
[ADR-0014](ADR-0014-removal-of-optimization-backtest-island.md) forbids
resurrecting the removed predictive-fit code without a new accepted decision.
These constraints remain in force while this ADR is proposed.

## Decision proposed

Add a separately reviewed, bounded, experimental population runtime alongside
the existing decision-lens runtime. This proposal changes the permitted
mechanism, not the product's evidence claims.

- **CURRENT:** default runs require approved decision-lens adapters. The
  preparation and admission functions above remain authoritative.
- **PARTIAL:** population preparation exists, but those artifacts do not meet
  the decision-lens execution contract. Declared character composition does
  not establish the number of registered or interacting runtime agents.
- **TARGET:** a versioned synthetic-population artifact, explicit review,
  canonical actor identity, reviewed behavioral controls, local seeded engine
  mechanics, and mode-specific admission connect preparation to execution.
- **TRANSITION:** isolated artifact and actor adapters, software regression
  tests, provenance fixes, and evaluation-artifact freshness may be developed
  without routing production requests through the new mode.

Production routing, default configuration changes, and conflicting methodology
changes remain blocked until this ADR is explicitly accepted through the
[change-control process](../../README.md#change-control-rule). A plan approval
or a green software test does not constitute methodological acceptance.

## Required contracts

### Runtime admission and review

Use an explicit runtime-mode discriminator separate from population scale.
Preserve the current lens validator unchanged. Population admission must bind
simulation identity, artifact digest, review digest, adapter version, controls,
platforms, seed, and configuration. Unknown versions, unreviewed artifacts,
cross-mode substitution, stale approvals, and unsupported controls fail closed.
A review acknowledgement is not measured human evidence and must not imply an
authenticated reviewer when none is established.

Actor identity must survive canonical and platform projection. If the pinned
OASIS graph requires contiguous actor IDs, reject incompatible identifiers
rather than silently renumbering them. Source identities remain explicit
metadata; graph context is not automatically a simulated social connection.

### Population and information boundaries

Distinguish actor records from non-actor context. Preserve source-supported
fields, reviewed scenario assumptions, generated elaboration, unknown values,
and engine-only placeholders as different origins. Never infer demographics,
psychometrics, or behavior from a role label alone. Structured-field omission
does not guarantee biography text contains no such claims; review still applies.

Agent differences must reach observable runtime inputs: activity eligibility,
information exposure, goals/constraints, and available actions. Every declared
control needs a consumer and a mutation test. Agents must not receive future
or unavailable information. Preserve observable actions, explicit references,
and delivered context; do not retain hidden chain of thought.

Follower reactions remain observational until a reviewed integration feeds
explicit effects back through actual platform mechanisms. Prepared,
registered, activated, acted, and observational follower counts are distinct.

### Reproducibility and evidence

Use namespaced local random streams for composition, scheduling, topology,
and followers. Controlled engine randomness is not deterministic model output.
Record provider/model identity as resolved or unresolved, prompt hashes,
artifact hashes, dependencies, attempted runs, and stochastic limitations.

Evaluation artifacts must contain current-session measurements only, identify
producers and fixtures/data, separate historical baselines, and expose partial
or failed runs. Offline fixture checks are not OASIS behavior benchmarks.

A subsequent empirical protocol must distinguish population composition fit,
individual behavior, interactions, and aggregate outcomes. Calibration and
held-out validation must remain separate. Counts or agreement among generated
agents are not customer samples, public-opinion measurements, likelihoods, or
purchasing evidence. Human-data fitting and predictive claims are outside this
proposal and require their own accepted methodology.

## Review requirements

Acceptance requires named product and engineering reviewers, research review
of population interpretation, and security/privacy review before any new
personal-data processing. No reviewers or approvals are asserted by this
proposal. Tests must establish bounded runtime integration, tamper rejection,
control consumption, identity preservation, information boundaries, and
failure/retry behavior. Paid-provider experiments require an explicit budget
and permitted data scope.

## Impact and compatibility

The existing product descriptor and permanent Truth Rail remain unchanged.
Existing reviewed-lens artifacts keep their admission rules. New population
artifacts are versioned and cannot be substituted into existing runs.
No new collection, retention, deployment, or provider permission is granted.
No deleted optimization/backtest module is restored.

The isolated adapters are experiments, not evidence that production population
runs work. Full population routing, network-exposure integration, source-grounded
composition, paired-run orchestration, scale testing, and behavioral validation
remain **TARGET** until implemented and verified.

**TRANSITION:** the isolated adapter separates generated profile/observation data
from static system instructions, constrains manual actions to the bound tool
allowlist, and includes a required system-protocol SHA-256 in each adapter
([`PopulationRuntimeAdapterV1.require_exact_prompt`](../../../backend/app/services/population_runtime_adapter.py),
[`create_population_social_agent`](../../../backend/app/services/population_oasis_agent.py)).
That field participates in the artifact digest and therefore its review binding.
A missing or changed protocol digest rejects admission; earlier experimental
artifacts must be rebuilt and reviewed, not silently upgraded. Fake-interface
regressions verify these local boundaries, not model obedience or complete CAMEL
memory/streaming retention. Those integration checks remain required before any
production rollout.

## Migration and rollback

There is no production migration while this decision is proposed. Any later
accepted rollout must be explicit and default-off, with separate artifact
versions. Rollback disables population admission and leaves immutable artifacts
available for inspection. Existing lens routes and artifacts must remain usable.
Never reinterpret population artifacts as reviewed lenses during rollback.

## Verification

Run focused preparation, provenance, random-stream, artifact/admission, actor,
and evaluation-harness tests. Use fake models for offline software contracts.
Run the documentation validator with zero errors and warnings, then the
repository verification entry point. Record actual failures and unavailable
checks; compilation or mocked tests do not establish behavioral fidelity.

## Alternatives considered

A wholesale upstream merge would import unrelated runtime assumptions and
bypass local admission. Increasing profile counts without connecting actors to
execution would change a declaration rather than a capability. Replacing
reviewed lenses globally would erase the recoverable baseline. The separate,
versioned runtime is preferred because it makes the methodological change
explicit and independently testable.
