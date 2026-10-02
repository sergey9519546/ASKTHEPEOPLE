"""SQLAlchemy declarative base. **No tables are declared here.**

History
-------
This module used to declare six tables — `organizations`, `projects`,
`simulations`, `agent_profiles`, `attempts`, `observations` — which formed a
second, independent source of schema truth alongside
`backend/migrations/versions/`. The two disagreed, and the disagreement was
not benign:

* The migrations declare 16 tables; this stub declared 6. Only `projects` and
  `simulations` shared a name, and they shared almost no columns.
* Those two declared incompatible primary keys — `sa.Integer()` autoincrement
  in the migration, `Uuid` here.
* The four tables unique to the stub had foreign keys onto ORM columns the
  migration does not have (`projects.organization_id`), so they could never be
  created as migrations without inventing columns first.
* `init_db()` called `Base.metadata.create_all` at application boot, which
  materialized *this* stub rather than the migrations. That produced a
  `projects` table with no `project_id` column, while the one live
  canonical-store repository queries `WHERE project_id = :project_id`
  (`services/project_repository.py:252`). The trap is closed: startup no longer
  creates schema (`tests/test_startup_no_schema_creation.py`).

The stub was also described as such in the repository's own docstring:
`backend/app/services/project_repository.py:19-26` records that the migration
"is the authoritative schema; the ORM models in `app.db.schema` are a partial
stub that does not match the migration".

Decision
--------
`backend/migrations/versions/` is the single source of truth (ADR-0013,
implementing ADR-0012). Schema is created by `alembic upgrade head` as an
explicit deploy step. The table declarations were removed on 2026-10-02 rather
than mirrored: 198 columns of hand-maintained duplication would have recreated
the second source of truth, with more places to forget than before.

`Base` is retained because two modules import it:

* `backend/app/db/__init__.py` — for `drop_db` (test cleanup; not on any
  runtime path).
* `backend/migrations/env.py` — as autogenerate's `target_metadata`.

Consequence: autogenerate now sees an empty `target_metadata` and would report
every migration table as new. That is an accepted loss, because Alembic is
invoked by no Dockerfile, no compose service, and no CI job — the autogenerate
workflow was already unused.

Known gap, deliberately not fixed here
--------------------------------------
The `dw_*` aggregates carry `organization_id` and `workspace_id` UUID columns
with **no `organizations` table in any migration and no foreign key target**.
The tenant entity is therefore undeclared. This is not resolved by restoring
the stub: tenancy is deferred by decision D2, `DEV_ACTOR_CONTEXT_ENABLED` is
refused in production, and the live tenancy design lives in the `dw_*` tables.
See ADR-0013 and ADR-0009.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

__all__ = ["Base"]