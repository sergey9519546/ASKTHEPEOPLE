# Predictive and forecasting outputs

This product does not produce forecasts, predictions, probability scores,
confidence intervals, or any claim about what people will actually do.

## Why this is out of scope

The product category is settled. ADR-0001 classifies ASKTHEPEOPLE as a
**Synthetic Decision Explorer** and fixes the truth boundary in the same
decision: outputs are generated, human respondents are zero, the run is not a
forecast, sources inform starting conditions rather than validating an outcome,
and human validation happens outside the generated run.

That is not a naming preference layered on top of the product. It is the thing
the product is. Every generated path is one equal-weight exploration of "what
could happen given these stated assumptions", not an estimate of what will
happen. Adding a confidence score would not make the output more useful — it
would make it say something the system cannot know, in the one domain where
being wrong is most expensive and least detectable.

The prohibition is enforced, not merely documented. Roughly thirty-three
forbidden terms are linted out of user-facing copy in both the frontend and the
backend, and a permanent disclosure block is rendered on every primary surface.
Suppressing the linter, or adding an exception for a single surface, would
reopen a settled product-claim decision and would require the named-reviewer
process that ADR-0001 already demands.

Requests that sound adjacent but are not this concept, and are legitimate:
showing how a result changes under different assumptions, reporting how stable
an output is when an input is perturbed, or exporting a brief that a person
takes to real stakeholders. Those describe sensitivity and provenance, which the
product does support. What is refused is any claim about the world outside the
run.

A prior rejection of the optimization and backtest island — code that computed
predictive fit and calibration without a consumer — is recorded separately in
ADR-0014. That removal was the same boundary enforced in code.

## Prior requests

None yet. This file was seeded so that the first request of this shape is
answered with the existing decision rather than re-argued.