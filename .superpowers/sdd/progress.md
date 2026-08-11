# Decision Workspace SDD Progress

- Task 1: complete (commit dcc59e7, review clean).
- Task 2: complete (commits 27254e9..edd24b5, review clean; 1379 focused/API tests pass).
- Task 3: complete (commits 9800e68..0eae7bd, review clean; 21 focused and
  1379 contract regression tests pass).
- Task 4: Checkpoint 4A complete (domain kernel, commit 54ade9c, 81 focused
  tests). Checkpoint 4B complete (config flags + gated API routes +
  capability endpoint + 14 route tests; every mutating endpoint returns 503
  UNAVAILABLE while SOURCE_INGESTION_V1_ENABLED=false; production gate
  refuses the flag when DEBUG=false). Remaining: §5 production blockers
  (PostgreSQL source aggregate, object storage, isolated scanner/parser
  worker, transactional outbox, deletion ledger/worker, tenant auth).
- Task 5: not started.
- Task 5: not started.
- Task 6: not started.
- Task 7: not started.
- Task 8: not started.
- Task 9: not started.
- Task 5: PARTIAL. Bounded fixes landed: /api/jobs get_instance crash fixed
  (used TaskManager() singleton); report generation now requires a terminal
  run (rejects RUNNING/PREPARING/etc with 409 report_run_not_terminal, with
  getattr defense for legacy/mock states without a status attribute). 7
  regression tests. The full 20-state durable run control plane, PostgreSQL
  run/stage/event/lease tables, fencing tokens, heartbeats, and stalled-lease
  recovery remain TARGET (require PostgreSQL infra).

## Infrastructure checkpoint — migration + repository adapters (2026-08-11)

- New Alembic migration `a1b2c3d4e5f6` (child of `384c98f88d53`) creates 7
  domain-aggregate tables: runs, run_stages, run_events, sources,
  source_versions, source_segments, source_candidates. All carry
  organization_id/workspace_id (tenant isolation), version (optimistic
  concurrency), and UUID primary keys.
- RunRepository (services/run_repository.py): connects run_attempt.py domain
  to the runs/run_events tables. create_run, get_run, get_run_by_public_id,
  list_runs, apply_transition (optimistic-concurrency CAS + domain policy +
  event recording in one transaction), get_run_events (cursor-based).
- SourceRepository (services/source_repository.py): connects
  source_ingestion.py domain to sources/source_versions tables. create_source,
  get_source, list_sources, create_source_version, get_source_version,
  update_source_version_state (CAS update with optimistic concurrency).
- Both repositories follow the project_repository.py raw-SQL pattern and are
  opt-in via USE_SUPABASE_PERSISTENCE.
- Caught and fixed a mistake: initial run_repository guessed the domain API
  (command names, target_state parameter, event-type mapping) instead of
  reading the actual signatures. Fixed to use decide_run_transition's real
  return type (RunTransition) which provides to_state + event_type directly.
