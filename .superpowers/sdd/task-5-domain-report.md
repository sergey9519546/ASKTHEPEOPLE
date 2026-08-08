# Task 5 Checkpoint 1 — Durable Run Domain Report

Status: TRANSITION / REVIEW REQUIRED

Date: 2026-08-08

Authority: `.superpowers/sdd/task-5-brief.md` Checkpoint 1 and
`docs/architecture/state-machines.md`

## Outcome

The disabled pure-domain durable-run kernel is implemented. It has no route,
worker, database, broker, filesystem, or legacy-runner side effects. It does
not make PostgreSQL, RLS, leases, outbox delivery, reconnect, secure source
review, path persistence, or production cutover available.

The kernel now contains:

- the exact 20-state run vocabulary, nine stage codes, nine immutable
  stage-attempt states, 13 command kinds, and 12 event types;
- the complete 40-edge run graph plus a closed 20 × 20 pair validator;
- the exact ten-edge stage-attempt graph and immutable retry numbering;
- strict, frozen run snapshot, guard-fact, and transition models;
- a pure transition policy with explicit server-derived guard checks;
- the complete Task 6 path-set/review/hash/validator/brief gate;
- rerun identity validation proving rerun is not a state transition; and
- all Task 5 public-ID kinds using independent UUIDv7 aliases.

## Code evidence

- Vocabularies: `backend/app/domain/run_attempt.py:24-99`.
- Strict models: `backend/app/domain/run_attempt.py:102-214`.
- Closed run graph: `backend/app/domain/run_attempt.py:239-306`.
- Closed stage-attempt graph and retry numbering:
  `backend/app/domain/run_attempt.py:282-325`.
- Rerun identity rule: `backend/app/domain/run_attempt.py:327-331`.
- Pure guard and transition policy:
  `backend/app/domain/run_attempt.py:334-470`.
- Run public-ID kinds: `backend/app/domain/identifiers.py:15-50`.
- Public package exports: `backend/app/domain/__init__.py:25-111`.

## Test evidence

The implementation used explicit RED→GREEN cycles for the missing module,
each vocabulary group, strict models, the 40 allowed transitions, the exact
stage graph, rerun identity, package exports, and public-ID kinds. Recorded
RED examples include:

```text
ModuleNotFoundError: No module named 'app.domain.run_attempt'
40 failed: decide_run_transition missing
1 failed: StageAttemptTransitionViolation missing
1 failed: RerunIdentityViolation missing
9 failed: unsupported_public_id_kind
1 failed: RunCommandKind missing from app.domain.__all__
```

Final focused and regression results:

```text
.\.venv\Scripts\pytest tests/domain/test_run_attempt.py -q
59 passed

.\.venv\Scripts\pytest tests/domain/test_identifiers.py -q
14 passed

.\.venv\Scripts\pytest tests/domain -q
7600 passed

uvx ruff check app/domain/run_attempt.py app/domain/identifiers.py \
  app/domain/__init__.py tests/domain/test_run_attempt.py \
  tests/domain/test_identifiers.py
All checks passed
```

The exhaustive tests are at:

- `backend/tests/domain/test_run_attempt.py:9-49` — exact 40 transitions;
- `backend/tests/domain/test_run_attempt.py:318-338` — complete run-pair
  Cartesian complement;
- `backend/tests/domain/test_run_attempt.py:340-374` — exact stage graph and
  retry numbering;
- `backend/tests/domain/test_run_attempt.py:385-405` — every required Task 6
  gate fact;
- `backend/tests/domain/test_run_attempt.py:407-441` — rerun identity;
- `backend/tests/domain/test_run_attempt.py:443-464` — identity, coercion,
  extra-field, and truth override rejection; and
- `backend/tests/domain/test_identifiers.py:148-178` — all nine durable-run
  public-ID kinds.

## Explicit remaining gates

- This checkpoint remains disabled and review-required. Named Architecture,
  Security, Privacy, Persistence, and Release approvals are not recorded.
- Checkpoint 2 cannot begin canonical persistence or production integration
  until the Task 3a tenant/OIDC/RLS foundation and its actual Alembic head are
  accepted.
- The Task 5 brief still requires independent closure of its dispatcher,
  reaper, retry, feature-flag, WebSocket-ticket, claim-predicate, and closed
  worker-command findings before persistence implementation.
- `VALIDATING_OUTPUT -> GENERATING_BRIEF` remains operationally unavailable
  until Task 6 provides a canonical verifier and immutable approved path-set
  review records.
