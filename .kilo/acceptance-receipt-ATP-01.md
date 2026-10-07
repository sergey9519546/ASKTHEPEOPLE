# Acceptance Receipt — ATP-01 (lane review, real PostgreSQL proof, fingerprints, fallback truthfulness)

**Date:** 2026-10-05
**Checkpoint:** `a410c9d` on `main`. **All work uncommitted**, nothing staged, no history
rewritten. Prior dirty work preserved: the four agent lanes plus
`test_prompt_registry_default_path.py` and the 2026-10-03 settings receipt.
**Engine under test:** `postgres:17.11-bookworm@sha256:639ab7ceb…b652`, the exact digest
pinned at `.github/workflows/ci.yml`.

ATP-01 is **closed for the three items it names.** It does not close Gate 2, Gate 4 or
Gate 5, all of which stay **PARTIAL**.

## 1. Lane review — all four lanes green together

| Lane | Delivered | Verified by me |
|---|---|---|
| PostgreSQL CI gate | `migrations` job gains a `services:` postgres block, applies + rolls back on **both** engines, SQLite run retained | digest identity confirmed; see §2 |
| Zep prompt adoption | 4 of 10 inline `system_prompt` literals moved to versioned YAML with fingerprints | SHA256 equality vs `git show HEAD`; see §3 |
| SLO / cost declaration | 11 settings, both features `False` by default | defaults read back; `create_app` boots; see §4 |
| Registry divergence | 9 tests making the two-implementation split measurable | ran with the rest; see §5 |

```
163 passed — the four new agent test modules plus the two registry/settings modules together
```

Two errors in my own briefs were found and corrected by the agents, not by me:
`PromptRegistry.assemble()` **does not exist** (the real surface is `get_prompt(id)["system_prompt"]`
plus `format_user_prompt(id, **kwargs)`), and I gave `tests/` paths for suites that live
under `tests/services/`.

## 2. Real PostgreSQL up/down proof — run locally, by me, not relayed

Container started from the CI-pinned digest. Digest identity confirmed first:

```
ci.yml pin : postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652
local image: sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652   ← identical
```

**Up** — all three revisions applied with **no `SECRET_KEY`, no `APP_TOKEN`, no provider
keys in the environment**, which is the ADR-0013 property the CI job exists to protect:

```
384c98f88d53 Initial schema
a1b2c3d4e5f6 Add domain aggregate tables for durable runs and source ingestion
b2c3d4e5f6a7 Add path aggregate tables for first-class paths and path-set reviews
exit=0
```

| Assertion | Result |
|---|---|
| recorded head | `b2c3d4e5f6a7` |
| table count | **17** |
| required (`projects`, `graphs`, `simulations`, `reports`, `dw_runs`, `dw_paths`) | **none missing** |

**Down and up again** — `downgrade base` walked `b2c3d4e5f6a7 → a1b2c3d4e5f6 → 384c98f88d53 → base`;
re-applying returned to `b2c3d4e5f6a7` with 17 tables, exit 0.

### The assertion was falsified, and the first attempt was vacuous

My first falsification attempt reported `exit=1` — but that exit came from a `SyntaxError`
in an inline heredoc, **not** from the assertion detecting a missing table. I discarded it
and redid it as a script:

| Run | Required set | Result |
|---|---|---|
| A | the six real tables | `MISSING: none`, **exit 0** |
| B | the six **plus** `a_table_that_does_not_exist` | `MISSING: ['a_table_that_does_not_exist']`, **exit 1** |

So the comparison is not vacuous on the production engine.

### What this does and does not prove

It proves the current 3-revision chain applies, rolls back and re-applies on PostgreSQL
17.11, and that the canonical-table comparison discriminates. It does **not** prove the
GitHub Actions job succeeds: service healthcheck timing, runner port availability, digest
resolution on `ubuntu-latest`, and job runtime are unverified and can only be proven by CI.

**ATP-03's outbox revision will be the first genuinely new schema this gate has ever
checked on the production engine.** That is the point of adding Postgres now rather than
after T28.

## 3. Fingerprints — byte-equal to pre-migration text

Compared against the literals in `git show HEAD:backend/app/services/zep_tools.py`, not
against the adopting agent's own claim:

| prompt_id | len | SHA256 (first 16) | matches HEAD line |
|---|---|---|---|
| `zep_subquery_generation` | 635 | `9e50d06b2e578f71` | 1308 |
| `zep_profile_selection` | 721 | `3b02113834fdfb54` | 1837 |
| `zep_probe_prompt_generation` | 679 | `bab5d5bb0fa0d4ca` | 1918 |
| `zep_probe_summary` | 824 | `5e9012e4ca8cf295` | 1988 |

All four definitions still contain the disclosure language (`fictional`, `synthetic`,
`generated`). Zero inline `system_prompt = """…"""` literals remain in `zep_tools.py`;
they are now `_registered_system_prompt("…")` lookups.

The 6 remaining prompts stay inline **by design**: they are `f`-strings using slicing,
`json.dumps`, `str.join` and conditional expressions that `str.format()` cannot express.
Templating them would have required rewording, which is the prohibited outcome. They also
use YAML `|-` rather than `|`, because none of the four literals ended in a newline and
`|` would append one — a difference the adopting agent caught by falsification.

## 4. Truthful fallback semantics — reviewed, and the `warn`-only default is correct

`COST_BUDGET_BREACH_ACTION` accepts `warn` only. Verified basis: `llm_client.py` sets
`max_tokens` on requests but **never reads `response.usage`**, and no price table exists.
There is no meter, so offering `refuse` would let an operator read "runs over budget are
refused" and receive an unbudgeted run. A boot failure is the cheaper wrong outcome.
`degrade` is excluded because silently substituting a lower-fidelity run changes what the
output claims to be (ADR-0001).

Inertness confirmed by reading the defaults back with no environment set:

```
SLO_ENABLED=False   COST_BUDGET_ENABLED=False
COST_BUDGET_BREACH_ACTION='warn'   COST_BUDGET_MAX_USD_PER_RUN=0.0
create_app() → OK, 111 routes
```

Refusals live in `Config._slo_and_cost_budget_errors` and are called from **both**
`validate_production_gates` (`config.py:628`) and `validate` (`:706`), so they cannot
drift — the §7 failure mode where `validate()` had one non-test caller and so stopped
nothing.

**Declared is not enforced.** An SLO with no alerting and a budget with no meter are
configuration, not control. Both stay PARTIAL under ATP-07.

## 5. Registry divergence — measured, and one defect found in my own test

`test_prompt_registry_default_path.py` asserted `len(prompts) == 5`. The legitimate
adoption of four prompts made that **9** and turned my test red. Rewritten to derive the
expectation from the definition files on disk, asserting "every file loaded and
fingerprinted" rather than a count — a hardcoded count turns each future adoption into a
failure, which is how a guard gets deleted instead of updated.

The two-implementation split is now executable: YAML registry has real consumers
(`llm_client.py`, `zep_tools.py`), the markdown parser yields `{}` because
`docs/ai/PROMPT_REGISTRY.md` contains **zero** `### Prompt:` blocks. Recommendation from
the divergence work: **retire the markdown parser rather than reformat the document**,
because `_parse_registry` upper-cases ids, so a reformatted document would register
`ONTOLOGY_GENERATION` alongside `ontology_generation`. That is an ADR-0004 decision and is
**not** taken here. `ADR-0004:62-66` still claims the registry has no consumer, which is
now false — correcting a normative ADR is an owner action.

## Gates after ATP-01

**All six remain PARTIAL.** Nothing in ATP-01 moved a gate, and the queue is explicit that
they stay PARTIAL until their actual workflows pass.

## Blockers and owner gates carried forward

1. **Disk.** `C:` fell to **0 bytes free** during this work and recovered to ~1.9 GiB
   unprompted. Repo-local debris is only ~147 MB (`.pyc`), so the consumer is elsewhere on
   `C:` and was not hunted — that is outside this remit. Heavy lanes ahead (ATP-02/03 need a
   PostgreSQL instance; ATP-08 needs repeated full suites and browser runs) are constrained
   by this, not by code.
2. **A bare `postgresql://` URL cannot run these migrations.** SQLAlchemy resolves it to
   psycopg2, which this project does not install. `backend/migrations/env.py:89-91` says
   "For migrations, use psycopg2 (sync)", which is wrong for the shipped `psycopg[binary]`.
   Any operator doc instructing `DATABASE_URL=postgresql://…` is broken today. `env.py` was
   not touched.
3. **CI-only unknowns** listed in §2.
4. **Operator actions, no code change:** credential rotation and usage review; operator
   secrets/CORS; legacy autodeploy stays disabled. `OneDrive` remains unsupported for
   deployment.