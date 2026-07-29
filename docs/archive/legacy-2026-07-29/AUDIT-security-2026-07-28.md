# Security & Dependency Audit — ASKTHEPEOPLE

> **SUPERSEDED BASELINE — DO NOT USE AS CURRENT RELEASE STATUS.** This file
> records the state observed before the 2026-07-28 hardening work. Its path,
> authentication, CORS, secret-response, traceback, container-user, CI-audit,
> and related findings have since been remediated in the worktree. Credential
> fragments from the original notes have been removed. Use
> [the current full audit](AUDIT-2026-07-28.md) for fixed items, verification,
> and residual blockers.

> **CRITICAL CORRECTION — 2026-07-29:** A later redacted full-history review
> proved that public commit `65403183ba37` contained real provider credentials
> in `.env.example`. Its Zep and Brave values still matched current local and
> Railway production configuration at discovery time. The “no committed
> secrets” conclusions below are false. See
> [the incident record](SECURITY-INCIDENT-2026-07-29.md). Values are
> intentionally omitted.

- **Date:** 2026-07-28
- **Scope:** READ-ONLY audit. No source, configs, or dependencies were modified.
- **Auditor:** ZCode security review (static review only — no network scanners run)
- **Repo:** `C:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE`
- **Commit baseline:** `main` as of audit date

> **Note on methodology:** Dependency versions were read from the committed lock files only; no vulnerability database was queried. "Vulnerable/outdated" statements below should be confirmed against an advisory DB (pip-audit / npm audit / GitHub Dependabot) by the CI/dependency owner before acting.

---

## Summary

This baseline incorrectly concluded that no real secrets had been committed.
The current `.env` is gitignored, but a public historical `.env.example`
revision exposed provider credentials. See the correction above before reading
the pre-hardening findings below.

---

## CRITICAL

### C1. Path traversal via unsanitized ID path parameters (report_id / simulation_id)

**Where:**
- `backend/app/services/report_agent.py:1999-2043` — `ReportManager._get_report_folder(report_id)` → `os.path.join(cls.REPORTS_DIR, report_id)` and every method that builds on it (`_get_section_path`, `_get_report_markdown_path`, `_get_agent_log_path`, etc., lines 2011-2043).
- `backend/app/services/simulation_runner.py:216-225` — `RUN_STATE_DIR` joined directly with `simulation_id` (e.g. `os.path.join(cls.RUN_STATE_DIR, simulation_id, "run_state.json")`, line 267/329/371/544...).
- `backend/app/api/report.py:833-842` — `get_single_section` reads a file via `_get_section_path(report_id, section_index)` where `report_id` is a raw URL path param.
- `backend/app/api/simulation.py:1097,1200,1372` — `sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)` with `simulation_id` from the URL.
- `backend/app/api/report.py:318,471,515,540,571,601,818` — multiple report endpoints feed `report_id` straight into filesystem reads/`send_file`.

**What's wrong:** `report_id` and `simulation_id` arrive as Flask `<path:...>`-style URL path parameters and are passed unmodified into `os.path.join(base, id)`. A request such as
`GET /api/report/report_x/../../etc/passwd/../../config.py` (or an ID containing `..`/absolute prefixes) can escape the intended base directory and **read arbitrary files** the process can access. There is a `validate_safe_path()` helper defined at `backend/app/api/simulation.py:30` that wraps `secure_filename` and does a prefix check — **but it is never called anywhere** (`grep` confirms only the definition exists, no call sites).

**Exploitability:** High. IDs are not validated server-side; nothing rewrites or rejects traversal sequences before they reach `os.path.join` / `open` / `send_file`. Whether an absolute path or `..` escapes depends on the host OS, but on Linux (production target) `os.path.join(base, "/etc/passwd")` collapses to the absolute path entirely — trivially exploitable.

**Fix:**
- Apply `validate_safe_path()` (or `werkzeug.utils.secure_filename` + an abspath-prefix check) to **every** `report_id` / `simulation_id` / `graph_id` / `script_name` / `project_id` before joining it into a path. Enforce a strict ID format via regex (`^[A-Za-z0-9_]+$` / `^(report|sim|proj|atp)_[a-f0-9]+$`).
- Reject IDs containing `/`, `\`, `..`, or a leading `.`.
- In `report.py` and `simulation.py`, wrap the ID at the top of each handler: `safe = validate_safe_path(base, id)` and use `safe` everywhere downstream.

---

## HIGH

### H1. Plaintext secrets returned by `POST /api/settings`

**Where:** `backend/app/api/settings.py:122-135` (`update_settings` response body).

**What's wrong:** After persisting settings, the endpoint returns the raw, unmasked values in the JSON response:
```python
"data": {
    "LLM_API_KEY": Config.LLM_API_KEY,          # plaintext
    ...
    "ZEP_API_KEY": Config.ZEP_API_KEY,          # plaintext
    "BRAVE_SEARCH_API_KEY": os.environ.get('BRAVE_SEARCH_API_KEY', ''),  # plaintext
    "LLM_BOOST_API_KEY": os.environ.get('LLM_BOOST_API_KEY', ''),        # plaintext
    ...
}
```
The GET endpoint (`get_settings`, lines 22-39) correctly masks via `_mask_secret()`, but the POST endpoint does not. Any client (or a man-in-the-middle / leaked response log) that can call `POST /api/settings` receives all configured API keys in cleartext.

**Fix:** Return `_mask_secret(...)` for every secret field in the POST response, identical to the GET handler. Never echo submitted secrets back.

---

### H2. No authentication or authorization on any API endpoint

**Where:** entire `backend/app/api/` (`graph.py`, `simulation.py`, `report.py`, `settings.py`, `ws.py`).

**What's wrong:** There is **no auth whatsoever** — no `flask-login`, no JWT, no API token, no `@login_required`-style decorator, no `before_request` auth check (`grep` for `Authorization`, `bearer`, `g.user`, `require_auth` returns nothing). Every endpoint is world-callable:
- `POST /api/settings` lets anyone **read and overwrite all LLM/Zep/Brave API keys** (writing them to `.env` on disk — `settings.py:97`).
- `POST /api/simulation/start` / `/stop` spawns/kills subprocesses (and injects `LLM_API_KEY`/`ZEP_API_KEY` into child env, `simulation_runner.py:490-497`).
- `POST /api/report/tools/search` exposes raw Zep graph search (debug endpoint, `report.py:1092`).
- `DELETE /api/report/<id>`, `/api/graph/delete/<graph_id>`, `/api/graph/project/<id>` allow destructive operations with no auth.
- The settings API is the worst case: an attacker can point the backend at a malicious LLM endpoint and exfiltrate the real keys.

**Combined with CORS `*`** (see H3), any website a user visits can drive the backend.

**Fix:** Add authentication (at minimum a shared API token / bearer header) before any rate limiting is useful. The hardening plan's rate limiting mitigates brute-force/cost abuse but **does not replace auth** — flag explicitly that rate-limited endpoints are still fully unauthenticated. At minimum, gate `/api/settings/*` and all write/DELETE endpoints behind a token.

---

### H3. Wildcard CORS by default (`CORS_ORIGINS=*`)

**Where:** `backend/app/__init__.py:55-57`; default in `backend/app/config.py:26` (`CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')`); `.env.example` ships `CORS_ORIGINS=*` uncommented.

**What's wrong:** With the shipped default, `Access-Control-Allow-Origin: *` is returned for all `/api/*` routes. Combined with no auth (H2), **any origin (any website) can issue cross-origin requests** to read data, trigger simulations, or read/rewrite API keys. The commented production example (`# CORS_ORIGINS=https://your-app.vercel.app`) is not enforced.

**Fix:** Default `CORS_ORIGINS` to an empty/refused list; require it to be set explicitly in production. Reject `*` when `FLASK_DEBUG=False`. The WebSocket routes (`/ws/*`, `ws.py:83,129`) are also open with no origin check — `flask-sock` does not enforce CORS, so add explicit Origin validation there.

---

## MEDIUM

### M1. Secrets passed into child-process environment (subprocess injection surface)

**Where:** `backend/app/services/simulation_runner.py:485-497`.

**What's wrong:** Before spawning the simulation subprocess, the runner copies the parent environment and then injects `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`, `ZEP_API_KEY` into `env`. These then live in the child process env and are reachable by the simulation scripts. The command itself (`cmd`, lines 470-478) is constructed from `sys.executable`, a fixed `script_path`, and a `config_path` derived from `simulation_id` (which is unvalidated — see C1). Because `simulation_id` reaches `cwd=sim_dir` and `config_path`, a traversal ID could redirect the child to load an attacker-chosen config / run in an attacker-chosen cwd — defense-in-depth reason to fix C1 first. The subprocess is launched with `start_new_session=True` (good) and the script name is chosen from a fixed allowlist (good — not an injection vector for argv), but the `--config` path is the risk.

**Fix:** Fix C1 (validate `simulation_id`) and confirm `config_path` resolves under `RUN_STATE_DIR`. Consider passing secrets via a sealed file or explicit minimal env rather than wholesale copy + key injection.

---

### M2. Default `SECRET_KEY` is random per-restart; no persisted production secret

**Where:** `backend/app/config.py:24` (`SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()`); `backend/app/__init__.py:46-52`.

**What's wrong:** `SECRET_KEY` is **not set** in the local `.env`, so it falls back to a fresh random value on every boot. The "insecure default value" warning in `__init__.py:47-52` is **dead code** — `_DEFAULT_SECRET = 'askthepeople-secret-key'` can never match, because `config.py` never assigns that literal (it uses `os.urandom` instead). Consequences: (a) all Flask sessions/signatures invalidate on every restart/deploy; (b) the `.env.example` ships `SECRET_KEY=change-me-to-a-random-secret`, so users who copy it verbatim get a publicly-known weak key.

**Fix:** Make the startup check meaningful (warn if `SECRET_KEY` is unset OR equals the `.env.example` placeholder). Document that a stable random `SECRET_KEY` must be set in production. Keep the per-restart random fallback only for local dev.

---

### M3. Error responses leak full tracebacks and exception strings

**Where:** nearly every handler in `report.py`, `graph.py`, `simulation.py`, `settings.py` (e.g. `report.py:209-213`, `graph.py:581-586`, `simulation.py:251-257`, `settings.py:42-45`).

**What's wrong:** Exceptions are returned to the client as `{"error": str(e), "traceback": traceback.format_exc()}`. The app does have an `after_request` handler (`__init__.py:79-90`, `strip_traceback_in_production`) that strips `traceback` when `DEBUG=False` — but it only runs when `response.is_json` and the dict literally contains the key `traceback`. (a) Some endpoints also echo `str(e)` which may include internal file paths or upstream error text; (b) the global 500 handler (`__init__.py:119-122`) returns `{"error": str(e)}` with no traceback stripping. Internal filesystem paths, Zep/OpenAI error bodies, and stack details can leak.

**Fix:** Always return a generic message to clients in production; log full detail server-side only. Centralize via the existing `after_request` hook and extend it to scrub `error` strings (or replace with a stable code) when `DEBUG=False`.

---

### M4. Docker container runs as root

**Where:** `Dockerfile` (Stage 3 "Runtime"). No `USER` directive, `useradd`/`adduser`, or non-root switch exists (`grep USER` returns nothing).

**What's wrong:** The gunicorn server, the simulation subprocess spawner, and all file I/O run as **root** inside the container. A path-traversal (C1), subprocess, or deserialization bug gains maximum filesystem reach. The container also bind-mounts `./backend/uploads` (`docker-compose.yml:15`), so root inside can write into the host tree.

**Fix:** Create a non-root user in the runtime stage and `USER` to it; ensure `uploads/`/`logs/` dirs are owned by that user. Drop capabilities and set `read_only: true` / `cap_drop: [ALL]` in compose.

---

## LOW / HYGIENE

### L1. No dependency-vulnerability scanning in CI
**Where:** `.github/workflows/ci.yml` — runs `pytest`, `npm run build`, `npm run test` only. No `pip-audit` / `uv audit` / `npm audit` / `gitleaks` / `trufflehog` step. Add periodic SCA + secret-scan jobs.

### L2. Dependency notes (static — confirm against an advisory DB)
Versions observed in `backend/uv.lock` (July 2026 lockfile) — flagged for the CI/dep owner to validate, not asserted as vulnerable here:
- `pillow 10.3.0` — several CVEs were fixed in 10.4.x and the 11.x line; 10.3.0 is likely behind patches. Confirm and bump if needed. (`PyMuPDF`/`fitz` and `pandas` are also heavy image/parse surfaces worth keeping current.)
- `setuptools 80.9.0`, `urllib3 2.6.2`, `certifi 2025.11.12`, `jinja2 3.1.6`, `werkzeug 3.1.4`, `flask 3.1.2`, `torch 2.9.1`, `transformers 4.57.3` — these read as recent; just keep them in the periodic bump cycle. `camel-ai 0.2.78` / `camel-oasis 0.2.5` / `zep-cloud 3.13.0` are niche — track advisories on those specifically since they're LLM/agent-sandbox surfaces.
- Frontend (`frontend/package.json`): `axios ^1.13.2`, `vue ^3.5.24`, `vite ^7.2.4`, `vitest ^3.0.0` — all on recent majors; no obvious pinned-vulnerable version, but `package-lock.json` should be run through `npm audit`.
- No `pip-audit`/`safety`/`npm audit` baseline exists today.

### L3. `.env.example` ships weak/placeholder secret defaults
`SECRET_KEY=change-me-to-a-random-secret`, plus `LLM_BOOST_API_KEY=` (empty) and `CORS_ORIGINS=*` uncommented. Tighten the template so copying it verbatim doesn't produce an insecure config.

### L4. `validate_safe_path` is dead code (already covered under C1, listed here for tracking)
Defined at `backend/app/api/simulation.py:30-39` but never invoked. Either wire it in everywhere (preferred) or remove to avoid false confidence.

### L5. Secrets in logs — NOT an issue (clean)
No `print()` of credentials and no `logger.*` calls that emit `api_key`/`secret`/`token` values were found in `backend/app/`. The `LLMClient` (`utils/llm_client.py:92`) logs only exception text on retry (which the OpenAI SDK already redacts). The settings GET endpoint masks secrets. **No remediation needed here**; only POST settings leaks (H1).

### L6. `.dockerignore` coverage is adequate
`.env`, `.git`, `node_modules`, `.venv`, `__pycache__`, `frontend/dist`, and `backend/uploads` are excluded. No secrets are baked into image layers. The only build-time `ARG` is `VITE_API_BASE_URL` (non-secret). One minor gap: `.claude/`, `.qodo/`, `.jules/`, `docs/`, and `*.md` are NOT excluded — they bloat the image (no secret risk, just hygiene).

---

## Secrets / committed-key check — superseded and incorrect

- `.env` (local) contained provider credentials. Their values and identifying
  fragments are intentionally omitted here. **They were not committed to git.**
  This was confirmed via:
  - `git ls-files --error-unmatch .env` → not tracked.
  - `git log --all -- .env` → never committed.
  - A history search for the full credential values found no historical blob.
  - Prefix searches only matched explicit test placeholders and input-help
    text, not real credentials.
- **Correction:** this conclusion was disproved by the 2026-07-29 full-history
  review. Rotation is urgent, and an operator-coordinated history rewrite is
  required after containment. See
  [the incident record](SECURITY-INCIDENT-2026-07-29.md).

---

## Top 3 findings (TL;DR for the caller)

1. **C1 — Path traversal (CRITICAL):** `report_id` / `simulation_id` from URL params flow unsanitized into `os.path.join(base, id)` and `open`/`send_file` across `report.py`, `simulation.py`, `report_agent.py`, `simulation_runner.py`. A `validate_safe_path()` helper exists but is never called. Trivially exploitable on Linux to read arbitrary files.
2. **H2 + H3 — Fully unauthenticated API + wildcard CORS (HIGH):** No auth anywhere; `POST /api/settings` reads/overwrites all API keys and `CORS_ORIGINS=*` by default. Any website can drive the backend and exfiltrate keys. Rate limiting (planned) will not fix this — auth is still missing.
3. **H1 — Plaintext secrets in `POST /api/settings` response (HIGH):** `settings.py:122-135` echoes `LLM_API_KEY`/`ZEP_API_KEY`/`BRAVE_SEARCH_API_KEY`/`LLM_BOOST_API_KEY` unmasked; the matching GET endpoint masks them. Mirror `_mask_secret()` in the POST response.

---

*End of report. This was a read-only audit; no files other than this report were created or modified.*
