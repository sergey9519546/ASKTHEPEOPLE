# Design Direction C — Civic Wayfinding

## Product feeling

ASKTHEPEOPLE should feel like a public-interest decision brief: direct,
legible, consequential, and useful to someone who does not speak in model,
graph, or simulation terminology.

The visual metaphor is a route map. A decision enters, assumptions branch into
possible synthetic paths, and the paths end at a separate real-human validation
handoff. The interface must never imply that generated profiles are people or
that source material validates an outcome.

## Non-negotiable truth layer

Every primary workflow screen keeps these facts visible:

- `0 human respondents`
- `Not a forecast`
- Generated actions and answers are synthetic
- Uploaded sources inform starting conditions; they are not outcome evidence
- Validation with people happens outside the synthetic run

Trace records may help inspect what happened inside one run. They are
keyword-related examples, not citations, statement lineage, or corroboration.

## Visual system

- **Canvas:** charcoal or near-black for the route field; warm paper for
  decisions, forms, and reading surfaces.
- **Signal:** safety yellow for the primary route, active step, and main action.
- **Secondary paths:** restrained teal and orange only when they distinguish
  meaningful branches.
- **Type:** a compressed display face for headings and route labels; a plain
  civic sans for instructions and reading. Monospace is not a visual theme.
- **Geometry:** sharp corners, hard rules, offset blocks, and purposeful
  asymmetry. Avoid soft floating cards, glass effects, pill-heavy controls, and
  generic SaaS gradients.
- **Information hierarchy:** one decision, one next action, and one visible
  limitation layer per screen. Diagnostics stay in a secondary disclosure.

## Journey contract

1. **The decision** — state the question in plain language and optionally add
   source material.
2. **Map the source material** — show what the system extracted without calling
   it evidence of an outcome.
3. **Set assumptions** — review generated profiles and scenario rules; block
   progress when required profiles or configuration are missing.
4. **Observe generated activity** — show synthetic channel activity as clearly
   labeled run streams, not causal paths, a terminal feed, or a prediction
   dashboard.
5. **Read the decision brief** — turn that activity into possible paths and
   questions, with findings first, limitations next, and trace details last.
6. **Ask follow-up questions** — explain the report by default; clearly label
   fictional profile and group responses as separate generated tools.
7. **Validate with people** — hand off scenarios and questions to a real research
   process without claiming the application recruited or measured anyone.

## Interaction and accessibility

- Desktop may show a source map beside the current decision step only when the
  user asks for it.
- Mobile shows one selected mode at a time; compare mode may stack both.
- All overlays trap focus, restore focus when closed, support `Escape`, and make
  the obscured page inert.
- Keyboard focus is high-contrast and never communicated by color alone.
- Motion is restrained and disabled under `prefers-reduced-motion`.
- Loading, empty, unauthorized, failure, stopped, and reconnecting states use
  plain language and an explicit next action.
- Touch targets are at least 44 by 44 CSS pixels where space permits.

## Writing rules

Prefer:

- Source material
- Assumptions
- Possible path
- Generated profile
- Synthetic action
- Related run record
- Validate with people

Do not use as outcome claims:

- Evidence from the source graph
- Respondents or participants
- Public opinion
- Confidence or probability
- Predicted behavior
- Digital twin
- Claim citation or verified lineage

## Release acceptance

A release does not satisfy Direction C merely because it uses black, yellow, and
display type. It must also preserve the product-truth layer, reduce technical
telemetry in the primary journey, remain understandable without simulation
expertise, and pass desktop, mobile, keyboard, and reduced-motion acceptance.
