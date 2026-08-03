# Project Provenance and Lineage

## Summary

ASKTHEPEOPLE is an adaptation of
[MiroFish](https://github.com/666ghj/MiroFish), created by 666ghj and its
contributors. It is not an independently created codebase.

The repository's shared Git history begins with:

```text
38e3d05b1d33d13fcbadc83ec0c4bf84c878e828
Author: 666ghj
Subject: Initial commit
```

That commit hash and the following upstream history are present in the MiroFish
repository. Later commits in this repository adapt, extend, rebrand, test, and
operate the system as ASKTHEPEOPLE.

## Current baseline

The current implementation baseline is
**`8b616dc7fa02eeed5ada8c51998d8b197be28f8d`** on the `main` branch,
last reviewed 2026-07-29. The production documentation system under
[`docs/`](docs/README.md) is the normative authority. The
[`AGENTS.md`](AGENTS.md) is the operational contract for any AI agent
working on this project, including the Mavis specialist team and any
external runner.

The baseline diverges from the doc-system baseline
(`c33a6a9127fa0705cfff426053f54815f58b4755`) by 30+ commits. The
divergence is recorded in
[`docs/archive/legacy-2026-07-29/README.md`](docs/archive/legacy-2026-07-29/README.md)
and must be expanded to a full per-aggregate census per
[`docs/exec-plans/00-repository-census-and-governance.md`](docs/exec-plans/00-repository-census-and-governance.md)
before any release claim cites the new authority docs as
already-live.

## Relationship to MiroFish

Substantial parts of the backend, frontend, prompts, simulation workflow,
documentation history, and original assets descend from MiroFish. This document
is the explicit attribution that earlier ASKTHEPEOPLE documentation lacked.

The upstream project describes itself as a general multi-agent simulation
engine. ASKTHEPEOPLE intentionally does **not** inherit upstream prediction,
high-fidelity, precise-trajectory, or digital-world marketing claims. The
current product boundary is synthetic scenario exploration and pretesting. See
[Methodology](METHODOLOGY.md).

Repository hosting metadata may not label ASKTHEPEOPLE as a GitHub “fork.”
Platform metadata does not change the code lineage or attribution obligation.

## Material ASKTHEPEOPLE changes

The complete record is in Git. Broad areas of later work include:

- ASKTHEPEOPLE naming and product framing
- Vue interface and workflow changes
- Simulation runtime, follower, archetype, evidence, and WebSocket changes
- Settings and provider configuration
- Tests and runtime repairs
- Security and data-handling hardening
- Container, CI/CD, Railway, Render, and Vercel configuration
- Documentation and operating guidance
- Production documentation system under `docs/` (12 ADRs, 48 modular
  documents, validator, CI, archive) — see
  [`docs/README.md`](docs/README.md)
- Three P0 release-blocker fixes in
  [`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](ASKTHEPEOPLE_GODMODE_BUILDPLAN.md):
  P0 path-escape in the posts endpoint, P0 daemon-thread in the
  prepare route, and P0 prompt-prefixing in profile generation.
  Recorded in [`docs/release/GATE_0_RELEASE_NOTES.md`](docs/release/GATE_0_RELEASE_NOTES.md)

This list is a summary, not a substitute for commit history or a software bill
of materials.

## OASIS and CAMEL-AI

The social-media-like simulation environments use
[OASIS](https://github.com/camel-ai/oasis), developed by CAMEL-AI contributors.
OASIS is separately licensed under Apache-2.0 according to its upstream
repository. The associated research is:

> Ziyi Yang et al. “OASIS: Open Agent Social Interaction Simulations with One
> Million Agents.” [arXiv:2411.11581](https://arxiv.org/abs/2411.11581).

OASIS supplies simulation mechanics. Its use does not establish the external
validity of a particular ASKTHEPEOPLE scenario.

## License

The repository contains the
[GNU Affero General Public License version 3](../LICENSE). MiroFish is also
published under AGPL-3.0 in its upstream repository. Dependency and embedded
component licenses remain applicable to their respective materials.

Keep:

- The `LICENSE` file
- Upstream copyright and license notices
- This provenance record or an equally prominent successor
- Source availability and notices required by AGPL-3.0 when conveying or
  providing the modified program over a network
- License records for dependencies, copied assets, fonts, and generated
  distribution artifacts

This is a factual project record, not legal advice. A release owner should
perform a dependency and asset-license review before distribution.

## Assets and copied material

Legacy MiroFish files and assets may remain in the repository. Before a public
release:

1. Inventory images, fonts, sample data, videos, and copied documentation.
2. Identify the source and license for each item.
3. Remove materials without a clear right to use.
4. Preserve notices and attribution where required.
5. Record replacements and modifications.

Generated artwork should also have its creation method and usage rights recorded.

## How to audit lineage

Useful local commands:

```bash
git log --reverse --format="%H %an <%ae> %s"
git show 38e3d05b1d33d13fcbadc83ec0c4bf84c878e828
git log --follow -- path/to/file
git blame path/to/file
```

Compare with the upstream history:

```bash
git remote add mirofish-upstream https://github.com/666ghj/MiroFish.git
git fetch mirofish-upstream
git log --left-right --cherry-pick --oneline mirofish-upstream/main...main
```

Adding the remote is optional. Do not rewrite shared history merely to make the
hosting platform display a fork relationship.

## Maintenance

Update this record when:

- Syncing or copying additional upstream work
- Adding another substantial upstream codebase
- Changing the project license
- Adding assets with attribution requirements
- Publishing a release or hosted service
- Changing the product claim boundary

Release notes should distinguish upstream-derived changes from
ASKTHEPEOPLE-specific modifications.

