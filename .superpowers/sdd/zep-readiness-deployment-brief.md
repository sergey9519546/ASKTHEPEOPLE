# ZEP readiness and deployment diagnostic brief

Date: 2026-08-08

Status: implementation authorized; live provider mutation prohibited

## Objective

Add a bounded, cached, read-only ZEP dependency signal to web readiness and
release diagnostics while preserving provider-independent liveness. ZEP is
mandatory for enabled graph-backed capabilities but remains a derived index;
canonical records must remain available outside ZEP.

## Locked behavior

- `/health` performs no ZEP operation and remains the Railway/container
  liveness path.
- `/health/readiness` declares `scope: web` and gates only
  `web_graph_backed` availability on a process-local, thread-safe ZEP status
  cache. It does not claim worker-provider reachability.
- The only provider operation is
  `Zep(api_key=..., timeout=2.0).project.get()`. Its response is discarded.
- Success is cached for 30 seconds and failure for 10 seconds. Key changes
  invalidate cache identity through a salted, nonlogged in-memory digest.
- Stale success never qualifies readiness.
- Public and logged failure reasons are limited to `available`,
  `not_configured`, `authentication_failed`, `rate_limited`, `timeout`,
  `unavailable`, and `probe_failed`.
- No graph API, provider body, provider project data, endpoint, exception text,
  key fragment, or raw key is returned or logged.
- A context-bound filter suppresses `httpx` and `httpcore` endpoint records only
  during the readiness provider call; application diagnostics remain enabled.
- ZEP failure returns readiness 503 and `web_graph_backed: unavailable`; it
  does not alter canonical state or fabricate a fallback graph.
- A pure validator is enforced by a Celery worker bootstep, and both the direct
  Procfile worker and wrapper invoke it before Celery. It validates credential
  presence without network I/O.
- Deployment gates separately on `/health/readiness`, binds the response
  revision to `TESTED_SHA`, requires the available/nonstale web capability
  predicates, and prints only the stable reason. The key remains in the
  deployed service environment, not CI.

## Files in scope

- `backend/app/services/zep_dependency_status.py`
- `backend/app/api/health.py`
- `backend/app/__init__.py`
- `backend/app/celery_app.py`
- `backend/app/utils/worker_startup.py`
- `backend/scripts/check_worker_zep_config.py`
- `backend/scripts/worker_wrapper.sh`
- `Procfile`
- `.github/workflows/deploy.yml`
- focused backend tests
- bounded architecture, security, product-truth, and release documentation

Graph builders, graph tasks, report tasks, provider connection-setting routes,
and live ZEP state are out of scope. The public web readiness probe does not
prove provider reachability from a separately configured worker service.
