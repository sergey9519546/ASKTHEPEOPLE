# Combined normative authority packet report

Date: 2026-08-08

Status: authority contract implemented; application behavior remains at its
documented CURRENT / PARTIAL / TARGET / TRANSITION state

Commit: recorded in the parent integration log from the isolated commit that
contains this report

## Scope

This change is documentation and validation only. It does not add application
routes, database models, migrations, workers, source processors, path writers,
comparison APIs, frontend features, or deployment mutations. Existing
unrelated backend/frontend work was not edited or staged.

The packet resolves the normative intersections required before the tenant,
source, durable-run, path, and brief implementation checkpoints may proceed:

1. exact `organization -> workspace -> project` ownership;
2. RFC 9562 UUIDv7 physical identity plus separate immutable server aliases;
3. organization/workspace memberships, OIDC bootstrap, immutable
   `ActorContext`, forced RLS, scoped repositories, core-schema adoption,
   shadow comparison, cutover, and canonical no-fallback behavior;
4. exact `epistemic-ledger/v2` roles, relations, and 18 ordered allowed
   triples;
5. source extraction candidate acceptance/revision semantics and the direct or
   transitive source-to-path/source-to-consideration ban;
6. the complete source transition graph, including operational `FAILED`,
   policy/review `REJECTED`, and deletion from every non-deleted state;
7. the preserved 20-state run contract, including both
   `REVIEWING_CONDITIONS` stop and retryable-failure transitions;
8. an independent immutable path-artifact review machine while the run remains
   `VALIDATING_OUTPUT`, with exact path-set/review hash binding before brief
   generation or completion;
9. exactly two later semantic-comparison inputs; and
10. changed-condition injection, advanced intervention, external evidence,
    interactive research-handoff construction, and decision-owner conclusions
    kept unavailable for later separately governed releases.

## Files

- `docs/architecture/data-model.md` — version `1.2.0`
- `docs/architecture/adr/ADR-0009-multi-tenant-isolation.md` — version `1.2.0`
- `docs/architecture/adr/ADR-0012-canonical-transactional-and-object-persistence.md` — version `1.2.0`
- `docs/product/PRODUCT_TRUTH_CONTRACT.md` — version `1.2.1`
- `docs/architecture/state-machines.md` — version `1.2.0`
- `docs/privacy/DATA_MAP.md` — version `1.2.0`
- `docs/release/RUNBOOK.md` — version `1.2.0`
- `docs/release/ACCEPTANCE.md` — version `1.2.0`
- `docs/superpowers/specs/2026-08-08-decision-chamber-experience-design.md` — version `1.0.2`, still `Proposed / Revision Required`
- `tools/validate_docs.py` — exact structural locks for the packet

## Structural enforcement

The validator now fails if any of these change without an intentional packet
revision:

- normative document version locks;
- the exact twelve-table core-foundation set;
- the exact 23-role and 14-relation v2 vocabularies;
- the ordered 18-triple v2 allowlist;
- the complete ordered 26-edge source graph;
- the exact six-edge path-artifact review graph;
- the exact ordered 20-state/40-edge run graph, as the only Mermaid graph and
  only uppercase transition-edge set in the bounded run section;
- tenant/no-fallback/privacy/deployment/acceptance anchor requirements;
- unique machine-readable comparison and first-slice policy blocks;
- third-or-more comparison authorization anywhere in the authority packet;
  and
- first-slice authorization of changed conditions, external evidence, or
  decision-owner conclusions anywhere in the authority packet.

## Verification

Executed from the repository root:

```text
python tools/validate_docs.py
Markdown files: 69
ADR files: 12
Warnings: 0
Errors: 0
RESULT: PASS
```

```text
git diff --check
exit code: 0
```

Line-ending notices from Git describe the repository's Windows checkout
normalization and are not whitespace errors.

## Self-review

- The pre-existing uncommitted run-state corrections in
  `docs/architecture/state-machines.md` were retained and incorporated into
  validator locks.
- The pre-existing canonical run-state/presentation correction in the proposed
  design spec was retained and completed with an exhaustive display-only
  mapping.
- No retired provenance relation is accepted as an alias on new writes.
- `REVISED_AS` is traceability only and never source evidence.
- No source transition is missing its deletion path.
- No new run state was invented for path review.
- Brief eligibility and finalization bind exact immutable hashes.
- No comparison implementation or placeholder is authorized.
- No implementation status was promoted to CURRENT by this docs change.

## Remaining gates, not contract conflicts

The normative ambiguity is resolved in the packet, but named Architecture,
Security, Privacy, Persistence, and Release owner approval must still be
recorded before the affected production checkpoints. Application evidence is
also still required: PostgreSQL migration/restore, database roles and forced
RLS, OIDC/membership bootstrap, operator adoption/backfill, secure TXT source
processing and deletion, durable leases/fences/outbox/reconnect, first-class
path persistence and semantic lineage, worker-kill recovery, accessibility,
and release drills. None is claimed by this report.

## Independent-review addendum

An independent review of `ce132a5` found three supporting-contract defects.
They are corrected in the isolated follow-up commit recorded by the parent
integration log; no normative document from `ce132a5` was changed.

1. The Task 3a brief no longer derives a public alias from the physical UUID.
   `new_public_id(kind)` generates and encodes an independent UUIDv7; physical
   ID and public-alias UUID are produced by separate calls and cannot be
   reversed into one another. Preserved legacy aliases remain the explicit
   adoption exception.
2. The docs validator now parses and locks the ordered 20-value `RunState`
   union, the complete ordered 40-edge durable-run graph, and the fact that the
   graph contains exactly those 20 states. It also parses bounded comparison,
   included-scope, deferred-scope, and release-boundary sections so exact-two
   and later-capability rules cannot be satisfied by an unrelated substring.
3. The Task 6 brief now follows the complete repository authority hierarchy
   and records that `ce132a5` resolved provenance lineage, path-review/run-state
   interpretation, and exact-two comparison normatively. Named owner approval,
   TRANSITION domain updates, semantic-identity evidence, and all persistence
   and release gates remain open.

Follow-up verification:

```text
python tools/validate_docs.py
Markdown files: 69
ADR files: 12
Warnings: 0
Errors: 0
RESULT: PASS
```

The follow-up commit contains only the two supporting briefs, the structural
validator, and this report addendum. It does not touch the concurrently edited
Task 5 brief or any normative, backend, frontend, migration, deployment, or
design asset file.

## Second independent-review addendum

The review of `0170aaa` identified two remaining validator bypasses and stale
Task 3a checkpoint language. This isolated follow-up corrects them without
editing application code or the concurrently active Task 3a implementation
report.

1. State-machine validation is now bounded from `## Run state machine` to
   `## Run-stage state machine`. The bounded section must contain exactly one
   Mermaid fence, that graph must contain the exact ordered 40-edge set, and
   every uppercase state edge anywhere in the section must be that same set.
   A second diagram or an edge after the canonical fence therefore fails.
2. Product Truth Contract version `1.2.1` contains exactly one JSON block for
   `decision-workspace-comparison/v1` and exactly one for
   `decision-workspace-first-slice/v1`. The validator parses their exact typed
   values and scans every authority-packet document for affirmative
   third-or-more comparison language or affirmative first-slice authorization
   of changed-condition injection, external-human-evidence import, or
   decision-owner-conclusion workflows.
3. The Task 3a brief now records the tenancy relationship as normatively
   resolved by `ce132a5`. Named Architecture, Security, Privacy, Persistence,
   and Release approvals and implementation evidence remain open. A disabled,
   dependency-free 3A-1 domain kernel may land for review, but no canonical
   persistence/integration, 3A-2-or-later rollout, or production acceptance is
   authorized before those approvals are recorded.

Reviewer-attack mutation probes cover a second run Mermaid graph, an uppercase
edge outside the canonical fence, third-input authorization in another
authority document, first-slice deferred-capability authorization outside the
scope section, and duplicate or altered machine-policy blocks. The verification
result for the clean packet remains:

```text
python tools/validate_docs.py
Markdown files: 69
ADR files: 12
Warnings: 0
Errors: 0
RESULT: PASS
```
