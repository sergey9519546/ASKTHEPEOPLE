# Task 3a Checkpoint 3A-1 domain implementation report

Date: 2026-08-08

Status: Checkpoint 3A-1 code is landed **disabled / review required**; broader
Task 3a remains **TRANSITION** and is not production-enabled. No integration
or Checkpoint 3A-2+ rollout is accepted until the named authority approvals
are recorded.

## Authority and correction

- Normative authority commit:
  `ce132a58e38c5d05ac7d9f76823cfc001ff0c7a9`
  (`docs: lock decision workspace authority packet`).
- Supporting-contract hardening commit:
  `0170aaa6ceac0b1a53f53e5f1dbf9494c46e8a86`
  (`docs: harden authority packet contracts`).
- The authority packet describes physical UUIDv7 identity and a separate,
  immutable, server-issued public alias. The binding implementation correction
  is applied: a new alias uses an independently generated UUIDv7 and must
  differ from—and therefore must not encode or reveal—the physical UUID. A
  generated equality collision is retried with a strict bound.
- The repository authority report still records named Architecture, Security,
  Privacy, Persistence, and Release owner approvals as outstanding. This
  checkpoint was executed by explicit orchestrator instruction, but this code
  landing is not authority approval, integration acceptance, or permission to
  begin Checkpoint 3A-2 or any later rollout.

## Files and behavior

- `backend/app/domain/identifiers.py:28-100` implements the RFC 9562 UUIDv7 bit
  layout, independent UUIDv7-backed public aliases, and exact preservation of
  accepted legacy project aliases.
- `backend/app/domain/authorization.py:10-139` defines the closed six-role,
  thirteen-capability `foundation-policy/v1` matrix and derives organization
  and workspace grants separately before unioning them.
- `backend/app/domain/actor_context.py:19-82` defines the closed actor and
  authentication enums plus a frozen, strict, extra-forbidden context. It
  enforces UUIDv7 physical scope, aware authentication time, user identity,
  organization-role, and exact policy-derived capability invariants.
- `backend/app/domain/__init__.py:3-55` exposes only the new public domain seam
  alongside the existing decision-lens exports.
- `backend/tests/domain/test_identifiers.py:7-146`,
  `backend/tests/domain/test_authorization.py:6-124`, and
  `backend/tests/domain/test_actor_context.py:8-83` cover the checkpoint.

No database, Flask, route, migration, authentication adapter, repository,
configuration, deployment, frontend, source, run, path, or brief code was
added. Domain modules import neither Flask nor database infrastructure.

## TDD evidence ledger

The disconnected predecessor left the UUIDv7 and legacy-alias tests together
with their implementation, but left no command output or durable RED artifact.
Those two cases are therefore recorded only as inherited implementation plus
fresh GREEN verification; this report does not invent or claim missing RED
evidence.

1. Inherited UUIDv7 case, fresh GREEN:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_uuid7_has_rfc9562_version_variant_and_time_window -q --basetemp=.pytest-tmp-task3a-domain-uuid7-green
   1 passed in 0.48s
   ```

2. The inherited public-alias test contradicted the authority contract and was
   replaced before implementation. RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_new_public_alias_uses_kind_and_independent_uuid7_hex -q --basetemp=.pytest-tmp-task3a-domain-alias-red
   TypeError: new_public_id() got an unexpected keyword argument 'uuid7_factory'
   1 failed in 0.70s
   ```

   GREEN after issuing a separate UUIDv7 alias. The initial implementation
   rejected physical/alias equality; the review-fix cycles below replace that
   one-shot behavior with bounded retry:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-domain-alias-green
   1 passed in 0.43s
   ```

3. Inherited legacy-project-alias case, fresh GREEN:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_legacy_project_alias_is_preserved_but_invalid_alias_is_rejected -q --basetemp=.pytest-tmp-task3a-domain-legacy-green
   1 passed in 0.47s
   ```

4. Role/capability matrix RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_authorization.py::test_role_policy_cartesian_matrix_is_closed -q --basetemp=.pytest-tmp-task3a-domain-auth-red
   ModuleNotFoundError: No module named 'app.domain.authorization'
   1 failed in 0.61s
   ```

   GREEN:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-domain-auth-green
   1 passed in 0.43s
   ```

5. Actor-context RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_actor_context.py::test_actor_context_is_frozen_strict_and_server_scoped -q --basetemp=.pytest-tmp-task3a-domain-actor-red
   ModuleNotFoundError: No module named 'app.domain.actor_context'
   1 failed in 0.66s
   ```

   GREEN:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-domain-actor-green
   1 passed in 0.50s
   ```

6. Minimal package export seam RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_actor_context.py::test_actor_context_is_frozen_strict_and_server_scoped -q --basetemp=.pytest-tmp-task3a-domain-exports-red
   ImportError: cannot import name 'ActorContext' from 'app.domain'
   1 failed in 0.67s
   ```

   GREEN:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-domain-exports-green
   1 passed in 0.46s
   ```

7. Independent alias equality-collision retry RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_new_public_alias_retries_physical_uuid_collision -q --basetemp=.pytest-tmp-task3a-alias-retry-red
   ValueError: public_alias_must_not_reveal_physical_id
   1 failed in 0.74s
   ```

   GREEN with the candidate sequence `[physical UUID, distinct UUIDv7]`:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-alias-retry-green
   1 passed in 0.51s
   ```

8. Retry-exhaustion bound RED:

   ```text
   .\.venv\Scripts\pytest tests/domain/test_identifiers.py::test_new_public_alias_retry_is_bounded_on_physical_uuid_collisions -q --basetemp=.pytest-tmp-task3a-alias-exhaustion-red
   AssertionError: public_alias_retry_was_unbounded
   1 failed in 0.79s
   ```

   GREEN after enforcing the three-attempt bound:

   ```text
   same node with --basetemp=.pytest-tmp-task3a-alias-exhaustion-green
   1 passed in 0.46s
   ```

## Verification

Focused checkpoint suite:

```text
.\.venv\Scripts\pytest tests/domain/test_identifiers.py tests/domain/test_authorization.py tests/domain/test_actor_context.py -q --basetemp=.pytest-tmp-task3a-domain-review-fix-focused-2
7 passed in 0.45s
```

The original isolated commit's domain regressions were green:

```text
.\.venv\Scripts\pytest tests/domain -q --basetemp=.pytest-tmp-task3a-domain-final-regression
1396 passed in 1.45s
```

The post-review-fix full domain run executed against concurrent, uncommitted
run-attempt work elsewhere in the shared checkout:

```text
.\.venv\Scripts\pytest tests/domain -q --basetemp=.pytest-tmp-task3a-domain-review-fix-regression
7533 passed, 1 failed in 6.05s
Unrelated failure: tests/domain/test_run_attempt.py::test_stage_command_and_event_vocabularies_are_exact
ImportError: cannot import name 'RunCommandKind' from app.domain.run_attempt
```

The identifier/authorization/context focused suite remains fully green; this
checkpoint did not edit the concurrent run-attempt files or test.

Touched-file lint:

```text
uvx ruff check app/domain/identifiers.py app/domain/authorization.py app/domain/actor_context.py app/domain/__init__.py tests/domain/test_identifiers.py tests/domain/test_authorization.py tests/domain/test_actor_context.py
All checks passed!
```

The review-fix-only lint over `identifiers.py` and `test_identifiers.py` also
returned `All checks passed!`.

The import-boundary scan found no Flask, database, API, or infrastructure
imports in the three new domain modules.

The untouched baseline migration has identical authority-commit and working
tree SHA-256 values:

```text
ad37205fd879561a8a0f46d8916abb921e15601fae4c8e85da5c772356958c55
git diff --quiet ce132a5 -- backend/migrations/versions/384c98f88d53_initial_schema.py -> 0
```

## Self-review and remaining gates

- UUIDv7 uses exactly 48 time bits, the version-7 nibble, RFC variant bits,
  and 74 cryptographically random bits. Random ordering inside one millisecond
  is intentionally not promised.
- Public aliases use lowercase UUID hex with the exact required prefixes and
  a UUIDv7 generated independently from the validated physical UUID. Equality
  with the physical UUID is retried at most three times before stable
  `public_alias_retry_exhausted` failure.
- This helper handles only physical/alias equality. Repository unique-index
  collision retry is deliberately deferred to the reviewed persistence slice;
  no database or repository behavior was invented here.
- Policy tests enumerate every valid organization/workspace role pair and
  prove that organization OWNER does not override an explicit workspace VIEWER
  into project mutation.
- Actor contexts cannot gain or lose a capability relative to policy v1,
  accept a non-UUIDv7 physical scope, accept untyped string scope, or mutate
  after construction.
- No unrelated dirty file was intentionally edited or included.
- Independent review of `c9ecfaf` failed P1/P2/P3. This follow-up addresses
  its bounded-retry and report-authority findings; follow-up review remains
  pending orchestration.
- PostgreSQL schema, migration/adoption, OIDC, RLS, repositories, backfill,
  shadow/cutover, restore, deployment, and release evidence belong to
  Checkpoints 3A-2 through 3A-5 and are not claimed here.

Commit SHA: the isolated commit containing this report is recorded by the
orchestrator after commit creation; a commit cannot truthfully contain its own
SHA in its tree.
