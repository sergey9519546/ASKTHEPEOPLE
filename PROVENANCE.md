# Project Provenance and Lineage

## Summary

ASKTHEPEOPLE is an adaptation of
[MiroFish](https://github.com/666ghj/MiroFish), created by 666ghj and its
contributors. It is not an independently created codebase.

The repository’s shared Git history begins with:

```text
38e3d05b1d33d13fcbadc83ec0c4bf84c878e828
Author: 666ghj
Subject: Initial commit
```

That commit hash and the following upstream history are present in the MiroFish
repository. Later commits in this repository adapt, extend, rebrand, test, and
operate the system as ASKTHEPEOPLE.

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

