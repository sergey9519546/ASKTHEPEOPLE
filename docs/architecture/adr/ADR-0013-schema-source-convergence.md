---
title: "ADR-0013: Schema Source Convergence"
status: "Accepted"
version: "1.0.0"
owner: "Architecture Council + Data Platform"
last_reviewed: "2026-10-02"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
baseline_commit: "0c1c44a"
implements_gate: "3"
implements: "ADR-0012"
applies_to: "backend/app/db/schema.py, backend/migrations/versions/"
audit_relevance: "P0 dual schema definitions; P0 primary-key type conflict on shared tables"
---

# ADR-0013: Schema Source Convergence

## Context

[ADR-0012](ADR-0012-canonical-transactional-and-object-persistence.md) already
decided the normative answer:

> The canonical foundation lives in an explicitly qualified PostgreSQL `core`
> schema. **Schema changes are Alembic-only; web and worker startup never call
> `create_all`**, stamp, migrate, provision, or backfill it.

The repository does not match that decision, and nothing recorded the gap. Two
schema definitions coexist, and a third mechanism silently wins at boot.

### Measured state (2026-10-02, commit `0c1c44a`)

| Source | Tables | Primary keys |
|---|---:|---|
| `backend/app/db/schema.py` (ORM) | 6 | `Uuid` |
| `backend/migrations/versions/` | 16 | `Integer` autoincrement |

- **In both:** `projects`, `simulations` — and these declare **incompatible
  primary keys**. `backend/migrations/versions/384c98f88d53_initial_schema.py:25`
  declares `sa.Column('id', sa.Integer(), autoincrement=True, nullable=False)`;
  `backend/app/db/schema.py:11` and `backend/app/db/schema.py:18` declare
  `Column(Uuid, primary_key=True, default=uuid.uuid4)`.
- **ORM only (4):** `organizations`, `agent_profiles`, `attempts`,
  `observations`. No migration creates them.
- **Migration only (14):** `graphs`, `ontologies`, `reports`, `sources`, and the
  `dw_*` aggregates (`dw_runs`, `dw_run_stages`, `dw_run_events`, `dw_sources`,
  `dw_source_versions`, `dw_source_candidates`, `dw_source_segments`,
  `dw_paths`, `dw_path_sets`, `dw_path_set_reviews`).

The primary-key conflict is the more dangerous of the two. A missing table fails
loudly at first query; a `Uuid` written into an `Integer` column fails at the
database engine, below the application.

### The shared tables are not the same tables

The key-type conflict is not the real problem. `projects` and `simulations`
share a **name** across the two sources and almost nothing else:

| Table | ORM columns | Migration columns | Overlap |
|---|---:|---:|---:|
| `projects` | 6 | 16 | `id`, `name`, `status`, `created_at` (4) |
| `simulations` | 6 | 11 | `id`, `project_id`, `status`, `config`, `created_at` (5) |

- `projects`: ORM-only `organization_id`, `version`; migration-only
  `project_id`, `decision_text`, `updated_at`, `user_id`,
  `total_text_length`, `chunk_size`, `chunk_overlap`, `analysis_summary`,
  `simulation_requirement`, `graph_id`, `graph_build_task_id`, `error`.
- `simulations`: ORM-only `version`; migration-only `simulation_id`,
  `result_json`, `error`, `updated_at`, `started_at`, `completed_at`.

So this is not a key conversion. It is two different tables that happen to be
called the same thing, and **the live code targets the migration.** The
canonical-store repository queries the migration's shape —
`backend/app/services/project_repository.py:252` issues
`SELECT id FROM projects WHERE project_id = :project_id`, and `project_id` is a
column that exists **only** in the migration. The ORM's `organization_id` is
referenced by no query.

`backend/app/services/project_repository.py:19-26` already records this:
the migration "is the authoritative schema; the ORM models in `app.db.schema`
are a partial stub that does not match the migration ... Resolving the drift
is a follow-up PR."

### Consequence for exec-plan T2 and T3

Exec-plan T2 as originally written — "add the four ORM-only tables as
migrations, after which the migration set is a strict superset of the ORM set"
— is **not executable**, and this ADR rejects it. Two reasons:

1. The four ORM-only tables have foreign keys onto ORM columns that do not
   exist in the migration. `projects.organization_id` has no migration
   counterpart, so `agent_profiles` and `attempts` cannot be given valid
   foreign keys until `projects` itself is reconciled.
2. Making the migration set a superset of a stub would enshrine an unused
   shape as canonical, against the only repository that actually runs.

The correct direction is the reverse of T2: reconcile `backend/app/db/schema.py`
**to** the migrations, per decision 1 below. The ORM classes become a
compatibility view of the authoritative definitions, or are deleted once
nothing materializes from `Base.metadata`. Exec-plan T2 and T3 must be
resequenced before either is attempted.

### A third mechanism wins at boot

**Alembic is invoked by no Dockerfile, no compose service, and no CI job.** The
migrations exist only as files. At boot, `create_app` imports `init_db` and
calls it:

- `backend/app/__init__.py:164` — `from .db import get_engine, init_db`
- `backend/app/__init__.py:167` — `init_db(engine)`
- `backend/app/db/__init__.py:25-27` — `init_db` calls
  `Base.metadata.create_all(bind=engine)`

`Base.metadata` is the ORM's six tables. So a deployment materializes six
tables, never the `dw_*` aggregates, and the migrations in the repository have
no effect on any running system. This is the direct contradiction of ADR-0012's
"web and worker startup never call `create_all`".

### Reachability, verified rather than assumed

A module can be substantial, tested, and unreachable. Before recording this
decision, each repository was checked for a production importer. The result
materially changes the risk assessment:

| Repository | Reached from | Status |
|---|---|---|
| `ProjectRepository` | `backend/app/models/project.py:198` (`_delegate_to_canonical`), gated on `USE_SUPABASE_PERSISTENCE` (`backend/app/models/project.py:195`) | live when the flag is set |
| `SourceRepository` | `backend/app/api/routes/source_routes.py:161`, `:232`, `:308` (function-local imports), gated on `SOURCE_INGESTION_V1_ENABLED` (`backend/app/api/routes/source_routes.py:38`) | live when both flags are set |
| `DecisionLensRepository` | live, **filesystem-backed** — constructed with a simulation directory, imports no SQL engine | always on |
| `RunRepository` | **nothing.** Only its own definition (`backend/app/services/run_repository.py:63`) and a docstring mention (`backend/app/services/simulation_manager.py:205`) | unreachable |
| `PathRepository` | **nothing.** Only its own definition (`backend/app/services/path_repository.py:29`) | unreachable |

Both flags default off (`backend/app/config.py:321-322` for
`USE_SUPABASE_PERSISTENCE`; `backend/app/config.py:232-233` for
`SOURCE_INGESTION_V1_ENABLED`), so no deployment is currently on the canonical
store.

**Consequence: the divergence is a trap, not an active data-corruption risk.**
Nothing is corrupting data today because the code paths that would collide are
unreachable or flag-gated. The moment someone sets
`USE_SUPABASE_PERSISTENCE=true` against a `create_all` database, the schema
they get is the ORM's six tables, and `SourceRepository` and
`ProjectRepository` will issue SQL against tables that do not exist.

## Decision

**Migrations are canonical. The ORM schema is a compatibility view of them, not
an independent source of truth.** This implements ADR-0012 rather than
re-deciding it.

1. `backend/migrations/versions/` is the only place a table is declared.
2. The migration set becomes a **strict superset** of the ORM set: the four
   ORM-only tables gain migrations (exec-plan T2).
3. `projects` and `simulations` converge on `Uuid` primary keys to match ADR-0012's
   RFC 9562 UUIDv7 requirement (exec-plan T3). A new head revision performs the
   conversion; the base revision is rewritten only if no deployment depends on
   it, which the flag default says is true today.
4. `Base.metadata.create_all` is removed from the boot path. `alembic upgrade
   head` becomes an explicit, tested deploy step (exec-plan T4).
5. Startup fails loudly and immediately when a feature flag is on but the
   expected tables are absent, naming the missing table and the migration step
   (exec-plan T6). The existing shape is at
   `backend/app/services/source_repository.py:42`, which raises
   `canonical_store_not_configured` when no URL is configured; that check is
   extended to verify table presence, not just configuration.

### Decision 4, applied on 2026-10-02

Exec-plan T4 is done. `create_app` no longer materializes schema:

- `backend/app/__init__.py` imports `get_engine` only. It creates the engine
  and opens a connection — a genuine connectivity probe that still drives the
  existing fail-closed branch for an unreachable `DATABASE_URL` in production
  — but it calls no DDL.
- `backend/app/db/__init__.py` `init_db()` now **raises**. It previously called
  `Base.metadata.create_all`; leaving it callable would let any surviving caller
  silently reinstate the behaviour, so the function refuses and names the
  remedy.

This was safe to do before the T2/T3 reconciliation because of what `create_all`
actually built. It was not merely redundant — it was **actively harmful**: it
materialized the ORM stub's `projects` table, which has no `project_id` column,
while `services/project_repository.py:252` queries
`WHERE project_id = :project_id`. A database created that way could not serve
the one repository that targets the canonical store. Removing it deletes a
trap rather than a capability.

`backend/tests/test_startup_no_schema_creation.py` (4 tests) pins the removal.
It records calls to `Base.metadata.create_all` while booting the real
application factory and asserts none occurred. Two implementation notes, both
found by testing the guard rather than trusting it:

- The guard originally raised an `AssertionError` from inside `create_all`.
  That silently passed even with `create_all` restored, because `create_app`
  wraps the database block in `except Exception` and falls back to filesystem
  storage. The call has to be **recorded**, not signalled by exception.
- An earlier version inspected the SQLite file after boot. That was unreliable:
  `create_app` reads `Config.DATABASE_URL`, resolved when `app.config` is first
  imported, so a test that sets the URL afterwards watches a file the app never
  wrote to.

With `create_all` reinstated, the suite fails with `startup called
Base.metadata.create_all, which ADR-0012 forbids`.

`app/db/schema.py` was **stripped on 2026-10-02**. It retains only
`Base = declarative_base()` and no table declarations. The six stub classes
were removed rather than mirrored, because 198 columns of hand-maintained
duplication would have recreated the second source of truth with more places to
forget than the six tables it replaced.

`Base` is still required by two modules: `backend/app/db/__init__.py:4` for
`drop_db` (test cleanup, not on any runtime path) and
`backend/migrations/env.py:19-20` for autogenerate's `target_metadata`. Both
keep working against an empty metadata.

Accepted consequence: **autogenerate is no longer usable.** With an empty
`target_metadata` it would report all 16 migration tables as new. This costs a
capability that was already unused — Alembic is invoked by no Dockerfile, no
compose service, and no CI job.

### Known gap: the tenant entity is undeclared

The `dw_*` aggregates carry `organization_id` and `workspace_id` UUID columns —
`backend/migrations/versions/a1b2c3d4e5f6_domain_aggregates.py:36-37` — and
**no migration creates an `organizations` table, so those columns have no
foreign-key target.** The stub's `organizations` class was the only
declaration of the tenant entity anywhere in the codebase.

Deleting it does not lose the concept, and restoring it would be worse:

- Multi-tenancy is deferred by decision D2. `DEV_ACTOR_CONTEXT_ENABLED` is
  refused in production (`backend/app/config.py`), so no tenant row is written
  today.
- The live tenancy design lives in the `dw_*` aggregates per
  [ADR-0009](ADR-0009-multi-tenant-isolation.md), not in the stub. The stub's
  `projects.organization_id` has no counterpart in the migration at all.

This gap is therefore recorded here rather than fixed. It must be closed when
tenancy is: a migration will need to create the tenant table, and every `dw_*`
column needs a foreign key to it. Tracked under ADR-0009, not here.

### Decision 5, applied on 2026-10-02

Exec-plan T6 is done. A feature flag enabled against a database that exists,
is reachable, and was never migrated now fails with a named error instead of a
driver-level `UndefinedTable` at first query.

- `app/db/require_tables(engine, expected)` raises
  `CanonicalSchemaMissing`, naming each missing table and the remediation:
  run `alembic upgrade head`, or unset the flag. `app/db/missing_tables` reads
  `information_schema` via `sqlalchemy.inspect`, so it works against the
  SQLite databases used by tests without pretending to be a migration check.
- `services/project_repository.py` requires `{projects, sources, ontologies}`
  and `services/source_repository.py` requires
  `{dw_sources, dw_source_versions}`, each verified on engine acquisition.
  Those sets were **read from each repository's SQL**, not guessed: a first
  draft named `source_versions`, `source_segments`, `source_candidates`,
  `source_ingestion_audit` and `project_files` for `ProjectRepository`, none of
  which that file queries.

The check runs **once, on acquisition**, not per query. Re-inspecting the
schema on every call would be wasteful, and the schema cannot change under a
running process without a restart.

`backend/tests/test_canonical_store_schema_guard.py` (5 tests) covers it, and
asserts each repository's declared set contains only tables a migration
actually creates — so the guard cannot drift into naming something that does not
exist. Verified by neutering `require_tables`: two tests fail.

This closes the loop on the original failure mode. Before this work, enabling
`USE_SUPABASE_PERSISTENCE` against an unmigrated database produced a raw
`UndefinedTable` naming a SQL fragment. Now it produces an error that says
which table is missing and what to run.

### Interim guard, in force now

`backend/tests/test_schema_parity.py` (9 tests) no longer *compares* two
sources, because there is only one. It asserts the stronger end state:

- `app/db/schema.py` declares **no** tables. A `__tablename__` there is a
  regression, since migrations are canonical and the boot path no longer calls
  `create_all`.
- `Base.metadata.tables` is empty, so neither `create_all` nor `drop_all` can
  touch schema.
- `Base` is still importable, because two modules depend on it.
- The migrations still declare their 16 expected tables, and the revision chain
  is linear with exactly one head. This stops "the ORM has no tables" from
  passing vacuously if the migrations were emptied.
- `drop_db` is not referenced from any runtime module.
- `app/db/schema.py` documents why it is empty, so an empty module with no
  rationale is treated as an accident rather than an accident waiting to
  happen.

Proven by planting a `rogue_table` class in `app/db/schema.py`: five tests
fail, including `test_orm_declares_no_tables`.

The earlier recorded-divergence allowances (`KNOWN_ORM_ONLY`,
`KNOWN_PK_MISMATCH`, `KNOWN_COLUMN_DIVERGENCE`) were removed with the stub.
The divergences they documented no longer exist to be recorded.

## Consequences

- **Exec-plan T2 and T3 are closed, not deferred.** Both assumed the ORM was a
  schema to be matched. It was a stub that the live repository already
  contradicted, and it no longer exists. The reconciliation ADR-0012 requires
  is complete: one schema definition, created by Alembic, never by startup.
- Exec-plan T4 is done; see the applied-decision note above.
- **T6 is now the highest-value remaining item.** With a single definition, the
  next failure mode is a flag enabled against a database that was never
  migrated. Today that surfaces as a raw `UndefinedTable` at first query. It
  should surface as a named error naming the missing table and the migration
  step, using the shape at `backend/app/services/source_repository.py:42`.
- **Autogenerate is gone.** Accepted, because Alembic is invoked by no
  Dockerfile, compose service, or CI job. Migrations are now written by hand.
- **The tenant entity is undeclared.** The `dw_*` `organization_id` columns
  have no foreign-key target; see the known-gap note above. Tracked under
  ADR-0009.
- `RunRepository` and `PathRepository` remain unreachable and therefore
  unverified against a live database. They must not be treated as evidence that
  the `dw_*` schema works. Their disposition is a separate decision.
- A developer running `create_all` locally against a migration-managed database
  still gets the ORM's six stub tables. Local setup must migrate too, or the
  local environment will not resemble production.

## Alternatives rejected

**Make the migration set a strict superset of the ORM set (exec-plan T2 as
written).** Rejected: it treats the stub as the schema. The four ORM-only
tables cannot even be created with valid foreign keys, because their FKs point
at ORM columns (`projects.organization_id`) that the migration does not have.

**Adopt the ORM as canonical and delete the migrations.** Rejected: it discards
the `dw_*` aggregates that ADR-0012 requires, it contradicts the live
`ProjectRepository`, and it would drop 12 real columns such as `decision_text`
and `analysis_summary`.

**Leave both and rely on documentation.** Rejected: this is the state that let
the gap survive. Six documents asserted independent status claims and drifted
into contradicting each other and the code; two schema definitions that disagree
about a table's columns is the same failure with worse consequences.

**Make `create_all` authoritative and delete `migrations/`.** Rejected: ADR-0012
already forbids it, and it removes revision history, downgrade paths, and the
aggregates.

## Verification

- `backend/tests/test_schema_parity.py` — 8 tests. Three known divergences are
  recorded (four ORM-only tables, two key-type mismatches, two column-set
  divergences), and separate tests fail if any recorded entry goes stale or
  changes shape, so none can rot into an unreported conflict.
- Proven by planting, each producing exactly one failure:
  a table added to `backend/app/db/schema.py`;
  `graphs` declared with a `Uuid` key in the ORM
  (`graphs: ORM Uuid vs migration Integer`);
  and a column added to the ORM `projects` class. The last of these exposed a
  real weakness in the guard's first version — a name-level allowlist could not
  see growth — which is why the column divergence is stored as exact sets.
- `python tools/validate_docs.py` → PASS with this ADR in the index.
- `npm run verify` → all gates.

Re-verified on each review. If the table counts in the Context section no longer
match, that is the signal this ADR is stale, not that the guard is wrong.