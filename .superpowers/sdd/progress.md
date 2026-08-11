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
