# ZEP readiness and deployment diagnostic report

Date: 2026-08-08

Status: implemented and locally verified; live provider canary not run

## Outcome

The web process now exposes a cached, sanitized ZEP dependency signal through
`/health/readiness` while `/health` remains provider-independent liveness. The
readiness response declares `scope: web`. ZEP unavailability returns readiness
503 and marks `web_graph_backed` unavailable; it does not change canonical
records or invent a fallback graph. Railway and the container continue probing
`/health`.

The only provider operation in the monitor is
`Zep(api_key=..., timeout=2.0).project.get()`. The response is discarded. The
monitor uses a single refresh lock, a salted nonlogged key digest, a 30-second
success TTL, a 10-second failure TTL, and no stale-success grace. Responses and
application logs carry only stable status metadata. A context-bound filter
suppresses `httpx` and `httpcore` endpoint records during only the readiness
call; it does not suppress application diagnostics or other request contexts.

A pure startup validator is enforced by the real Celery worker bootstep. The
direct Procfile worker and wrapper also invoke it before Celery, so supported
entry points refuse a missing `ZEP_API_KEY` without making a network call. The
production workflow separately polls ZEP-aware web readiness, binds its
reported revision to `TESTED_SHA`, enforces every available/nonstale capability
predicate, and allowlists the reason before logging it; no provider key was
added to CI and no response body is printed.

## TDD evidence

Initial RED command from `backend/`:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_dependency_status.py tests\test_zep_health_readiness.py tests\test_zep_deployment_diagnostics.py -q --basetemp=.pytest-zep-readiness-red
```

Observed: 29 collected, 28 failed, 1 passed. Failures were the missing monitor,
missing ZEP readiness fields/gating, missing no-store header on readiness,
missing worker startup check, and missing deployment predicate.

Initial GREEN used the same three focused files and observed `29 passed`.
Self-review then found that the deployment log trusted the returned reason
without enforcing the stable allowlist. A new focused test was added and
observed RED (`1 failed`); the workflow `case` allowlist made it GREEN.

Strict review added executable and mutation coverage for the revision-bound
deployment predicate, web-only scope, context-bound transport filtering, and
an actual Celery worker process with a missing key. The fresh targeted RED
observed `15 failed, 1 passed`; after implementation the same 16 tests observed
`16 passed in 3.65s`. The Celery subprocess exits nonzero with the stable
configuration error before broker connection; no provider call is made.
Final wording review then locked the deploy success message to state that worker
reachability was not evaluated. The new assertion observed RED (`1 failed`),
then the complete deployment-diagnostic file observed `14 passed in 2.24s`.

Final strict regression command:

```text
.\.venv\Scripts\pytest.exe tests\test_zep_dependency_status.py tests\test_zep_health_readiness.py tests\test_zep_deployment_diagnostics.py tests\test_health.py tests\test_app_hardening.py tests\test_hardening_config.py tests\test_settings.py tests\test_logging_policy.py -q --basetemp=.pytest-zep-strict-final
```

Observed: `93 passed in 61.66s`. This includes cache/classification,
no-graph/no-leak, web readiness, deployment predicate mutations, the executable
Celery missing-key process, health, hardening, configuration, settings, and
logging-policy coverage.

## Regression and static verification

- The final 93-test command includes `test_app_hardening.py`,
  `test_hardening_config.py`, `test_settings.py`, and `test_logging_policy.py`.
  An earlier attempt timed out after 180 seconds with seven tests passed and no
  failure because the rate-limit test made sixty real Redis/Celery liveness
  checks. That test is now dependency-isolated and fully offline.
- A focused Ruff check passed before strict review. The final strict-review
  rerun could not initialize the existing Windows `uv` cache inside the
  workspace sandbox; the requested offline escalation was rejected by the
  host's usage limit. This is an environment verification limitation, not a
  claimed pass for the final diff.
- `.github/workflows/deploy.yml` safe YAML parse: `PASS`.
- `python tools/validate_docs.py`: 69 Markdown files, 12 ADR files, zero
  warnings, zero errors, `RESULT: PASS`.
- `git diff --check`: `PASS` (line-ending notices only).
- A POSIX `sh` executable is unavailable in this Windows environment, so
  `sh -n` was not run. Worker command ordering has static mutation coverage,
  and the real Celery CLI is exercised as an executable subprocess.

## Safety evidence

- Tests use injected fake clients whose `graph` property raises if accessed.
- Secret-bearing project payloads and provider exception bodies are asserted
  absent from returned status and captured log calls.
- Liveness is asserted not to invoke the ZEP monitor.
- No live ZEP request, graph creation, ontology registration, ingestion,
  verification, or deletion was performed in this slice.
- Graph-worker and report-worker implementation files were not edited.

## Limitation

The public readiness endpoint proves the web service's provider environment.
The production workflow currently deploys and checks one Railway service ID,
so it does not prove provider reachability from a separately configured Celery
worker. Worker startup now proves key presence only. A worker-private readiness
probe or separately wired worker deployment diagnostic remains required before
claiming end-to-end worker provider readiness.

Celery also remains a displayed but non-gating web readiness component in the
pre-existing health contract. That broader operations defect is outside this
bounded ZEP slice.
