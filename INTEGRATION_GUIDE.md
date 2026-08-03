# Integration guide

## Objective

Adopt the documentation system without pretending that target-state components
already exist and without losing the current repository's provenance.

## 1. Create a documentation branch

```bash
git switch -c docs/production-authority
mkdir -p docs
```

Copy the contents of this package's `docs/` directory into the repository's
`docs/` directory. Do not delete historical audits or upstream provenance. Move
superseded documents to a clearly marked archive when required.

## 2. Record the actual baseline

The package used commit
`c33a6a9127fa0705cfff426053f54815f58b4755`. Before merge:

```bash
git rev-parse HEAD
git status --short
git log -1 --oneline
```

Run [`docs/exec-plans/00-repository-census-and-governance.md`](docs/exec-plans/00-repository-census-and-governance.md).
Record divergences in the pull request. Do not edit the docs to hide an
implementation gap; mark current and target states explicitly.

## 3. Reconcile legacy documentation

For every legacy product or architecture claim, classify it as:

- **preserved** — still accurate and compatible;
- **modified** — retained with a narrower or more accurate claim;
- **superseded** — replaced by a named new document;
- **rejected** — unsafe, misleading, or no longer part of the product;
- **unverified** — requires repository or operational evidence.

At minimum reconcile:

- root README;
- existing methodology, design, use, validation, provenance, deployment, and
  audit files;
- API descriptions and screenshots;
- environment templates and provider setup;
- marketing/site copy;
- export templates and sample reports.

## 4. Establish documentation ownership

Map document roles to named people or teams:

| Domain | Required owner |
|---|---|
| Product truth and claims | Product Truth Lead |
| Methodology | Research Lead |
| Architecture and data | Principal Engineer |
| AI prompts and evals | AI Evaluation Lead |
| Security | Security Lead |
| Privacy and subprocessors | Privacy Lead |
| Accessibility | Accessibility Lead |
| Releases and rollback | Release Manager / SRE |

Replace role-only ownership with named accountability in the internal governance
system while keeping public documents free of unnecessary personal data.

## 5. Add documentation checks to CI

CI should fail on:

- broken relative links or missing assets;
- malformed YAML front matter;
- duplicate document IDs or ADR numbers;
- unresolved `TODO`, `TBD`, `FIXME`, or placeholder tokens;
- naked `ASKTHEPEOPLE` wordmark in user-facing approved-copy fixtures;
- prohibited outcome language in UI, API descriptions, exports, and marketing;
- source-to-outcome provenance edges;
- stale prompt/model/provider/subprocessor records;
- acceptance or runbook references to nonexistent commands.

Store the linter configuration and approved exceptions in version control.

## 6. Merge in dependency order

Recommended merge sequence:

1. docs authority, claim contract, terminology, and use policy;
2. domain schemas and truth invariants;
3. tenancy, authorization, and canonical persistence;
4. secure source ingestion;
5. reviewed assumptions, uncertainties, and decision lenses;
6. durable orchestration and structured possible paths;
7. decision brief, research handoff, exports, and provenance;
8. security, privacy, observability, and operations;
9. evaluations, accessibility, comprehension testing, and release gates.

Use the execution plans for detailed exit evidence. Do not run broad feature
work in parallel when it depends on unresolved domain or truth contracts.

## 7. Preserve target/current-state honesty

Every pull request must identify:

- what is currently implemented;
- what the documentation requires;
- the exact gap closed;
- migrations and compatibility impact;
- tests/evals performed;
- rollback method;
- remaining known gaps.

A screenshot, prototype, fixture, or generated route is not proof of a complete
backend workflow.

## 8. Final adoption gate

The documentation branch is ready to become the repository authority when:

- all links and assets resolve;
- historical documents point to the new authority or are marked superseded;
- owners and review cycles are accepted;
- the Product Truth Contract is approved;
- CI enforces the most critical language and structure rules;
- open implementation gaps are recorded rather than hidden;
- the first execution plan has an assigned owner and evidence location.
