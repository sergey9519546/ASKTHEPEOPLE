# Enabling the hosted-platform deploy paths

The Railway, Render, and Vercel deploy paths stay switched off. They are
fail-closed in the repository on purpose, not by neglect.

## Why this is out of scope

Every hosted deploy path in this repository runs a blocker that exits non-zero,
and the production job in CI stays dark unless a repository variable is set that
is deliberately left unset. Turning one on would deploy the web service while
worker, beat, and the canonical record store are not revision-atomic with it —
so a simulation could be running against one revision while the UI that starts
and watches it comes from another.

The blocking condition is canonical shared persistence. Project, simulation,
report, task, and artifact records must be canonical across processes before
web and worker can be deployed independently at one immutable revision. That is
ADR-0012, and it is still open: the object-storage cutover, the outbox, and
soft-delete are unfinished, and the `dw_*` aggregates still carry a tenant
entity that no migration declares.

Two further operators-only conditions are documented in `AGENTS.md`: provider
credentials that were exposed must be rotated and revoked, and every connected
provider dashboard must have autodeploy disabled — a provider's own GitHub
integration can deploy independently of this repository's configuration, so
leaving one connected defeats the sentinels entirely.

The only supported topology is a single-host transition Compose stack run from a
local-disk clone with a mode-0600 environment file and an explicit build
revision. The runbook forbids running it from a sync mount, because SQLite
locking and atomic file updates are not deployment evidence on one.

This entry is not an argument against hosted deployment forever. It records what
must be true first. ADR-0012 closing is the trigger to reconsider.

## Prior requests

- #172 — "close deployment-readiness blockers". Triaged `ready-for-human`: every
  code-side blocker is closed and the remainder needs provider access.