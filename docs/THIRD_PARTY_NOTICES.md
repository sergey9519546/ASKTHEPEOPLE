# Third-Party Software and Media Notices

This record covers the direct, material dependencies and media used by the
current ASKTHEPEOPLE distribution. The complete resolved dependency closure is
defined by `backend/uv.lock`, `frontend/package-lock.json`, and
`package-lock.json`. Tagged container releases also publish an automated SBOM.

This summary is an attribution and release-audit aid, not legal advice. The
license files distributed with each package remain authoritative.

## Project lineage

ASKTHEPEOPLE is an AGPL-3.0 adaptation of MiroFish. See
[Project Provenance and Lineage](PROVENANCE.md) and the repository `LICENSE`.
The OASIS/CAMEL simulation libraries are separately licensed under Apache-2.0.

## Frontend runtime

| Package or asset | Resolved version | Declared license |
| --- | ---: | --- |
| Vue | 3.5.25 | MIT |
| Vue Router | 4.6.3 | MIT |
| Axios | 1.18.1 | MIT |
| D3 | 7.9.0 | ISC |
| Lucide Vue | 1.27.0 | ISC |
| Barlow font files | 5.3.0 package | SIL Open Font License 1.1 |
| Staatliches font files | 5.3.0 package | SIL Open Font License 1.1 |

The current `mark.svg` and `social-card.svg` are project artwork. The legacy
`frontend/public/icon.png`, the unreferenced legacy logo files, and the media
under `static/image` descend through the MiroFish repository history. The
current Vue source does not reference the legacy logos or `static/image`
material; they should not be reused outside the project without a separate
asset review.

## Frontend development and release tooling

| Package | Resolved version | Declared license |
| --- | ---: | --- |
| Vite | 7.3.6 | MIT |
| `@vitejs/plugin-vue` | 6.0.2 | MIT |
| Vitest | 3.2.7 | MIT |
| Vue Test Utils | 2.4.11 | MIT |
| jsdom | 26.1.0 | MIT |
| concurrently | 10.0.4 | MIT |

Development tooling is not copied into the final runtime image.

## Backend runtime

| Package | Resolved version | Declared license |
| --- | ---: | --- |
| Flask | 3.1.3 | BSD-3-Clause |
| Flask-Cors | 6.0.5 | MIT |
| Flask-Limiter | 4.1.1 | MIT |
| Flask-Sock | 0.7.0 | MIT |
| OpenAI Python | 1.109.1 | Apache-2.0 |
| Zep Cloud | 3.13.0 | Apache-2.0 |
| CAMEL OASIS | 0.2.5 | Apache-2.0 |
| CAMEL AI | 0.2.78 | Apache-2.0 |
| PyTorch CPU | 2.13.0 | Composite notices; package metadata includes Apache-2.0, BSD, Boost, MIT, and LLVM-exception terms |
| Sentence Transformers | 5.6.1 | Apache-2.0 |
| Transformers | 5.14.1 | Apache-2.0 |
| Model Context Protocol Python SDK | 1.29.0 | MIT |
| PyMuPDF | 1.28.0 | AGPL-3.0 or Artifex commercial license |
| fpdf2 | 2.8.7 | LGPL-3.0-only |
| Pillow | 12.3.0 | MIT-CMU |
| charset-normalizer | 3.4.9 | MIT |
| chardet | 7.4.3 | 0BSD |
| pandas | 2.2.2 | BSD-3-Clause |
| NetworkX | 3.6.1 | BSD-3-Clause |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| Pydantic | 2.13.4 | MIT |
| Gunicorn | 26.0.0 | MIT |

PyMuPDF's AGPL option is material to this AGPL-licensed application. A
proprietary redistribution cannot assume that this dependency becomes
permissively licensed.

## Release checks

Before a public release:

1. Regenerate the locks and review dependency-license changes.
2. Run the Python and npm advisory gates.
3. Build the container and review its generated SBOM and vulnerability scan.
4. Keep the repository AGPL license and provenance links visible.
5. Review any new copied, purchased, or generated media separately from
   package-code licenses.
