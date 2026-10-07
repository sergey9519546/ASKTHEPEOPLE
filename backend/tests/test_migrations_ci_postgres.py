"""Gate 3 must exercise the engine production actually uses.

The `migrations` job in `.github/workflows/ci.yml` proved the Alembic chain
against SQLite only. That is not a weaker version of the real gate, it is a
different one: the application engine is PostgreSQL, and SQLite accepts type and
constraint behaviour PostgreSQL rejects. A revision could therefore pass the
gate and fail against a real database, which is the exact failure mode the gate
exists to catch, and the next revision to land would be the first thing to
discover it.

These are **static guards over the workflow file, not a substitute for the job.**
They cannot start a service container, cannot run `alembic`, and cannot observe
a table. What they can do -- and what would otherwise silently rot -- is assert
that the job still declares the PostgreSQL run at all, that the image is pinned,
that both engines run the *same* canonical-table assertion, and that the job
carries no credentials. A deleted PostgreSQL block fails here in seconds instead
of after someone deploys.

Each check is falsified by an inline mutated fixture (see `_CLEAN_WORKFLOW`), so
none of them can pass by construction: the clean fixture must produce zero
problems, and every problem code must be produced by a fixture that is wrong in
exactly that one way.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
JOB = "migrations"

# An exact tag plus a digest, the way every other image reference in this
# repository is pinned (`docker-compose.yml`, `Dockerfile.worker`, the redis
# container in this same workflow). A floating tag lets the engine under test
# change without a commit.
PINNED_POSTGRES_RE = re.compile(
    r"^postgres:(?P<tag>[A-Za-z0-9][A-Za-z0-9._-]*)@sha256:(?P<digest>[0-9a-f]{64})$"
)

# SQLAlchemy resolves a bare `postgresql://` scheme to psycopg2. This project
# declares `psycopg[binary]` (psycopg 3) and does not install psycopg2, and
# `migrations/env.py` passes a bare scheme through untouched, so an unqualified
# URL aborts the step with ModuleNotFoundError. Measured against PostgreSQL
# 17.11 before this pin was written.
DRIVER_QUALIFIED_RE = re.compile(r"^postgresql\+psycopg://")

# Compared structurally against parsed env keys. A text search over the file
# reports a false positive: this job's own comment names these variables in
# prose to explain why they are absent.
CREDENTIAL_ENV_KEYS = (
    "SECRET_KEY",
    "APP_TOKEN",
    "LLM_API_KEY",
    "LLM_BOOST_API_KEY",
    "ZEP_API_KEY",
    "SUPABASE_KEY",
)

CREDENTIAL_EXPORT_RE = re.compile(
    r"^\s*(?:export\s+|env\s+)(?:SECRET_KEY|APP_TOKEN|LLM_API_KEY|LLM_BOOST_API_KEY|ZEP_API_KEY)\s*=",
    re.MULTILINE,
)

# The subset the workflow asserts. `test_schema_parity.py` already enumerates
# all sixteen canonical tables; duplicating that list into YAML would create a
# second place to forget.
CANONICAL_TABLES = ("projects", "graphs", "simulations", "reports", "dw_runs", "dw_paths")

SQLITE_APPLY = "empty SQLite database"
POSTGRES_APPLY = "empty PostgreSQL database"
SQLITE_ROLLBACK = "SQLite migrations back and forward"
POSTGRES_ROLLBACK = "PostgreSQL migrations back and forward"

# Problem codes. Named so a test asserts a specific detection rather than "some
# failure happened", which would pass on an unrelated defect.
SERVICE_MISSING = "postgres-service-missing"
IMAGE_FLOATING = "postgres-image-floating"
SQLITE_RUN_MISSING = "sqlite-run-missing"
POSTGRES_RUN_MISSING = "postgres-run-missing"
POSTGRES_ROLLBACK_MISSING = "postgres-rollback-missing"
POSTGRES_ASSERTION_MISSING = "postgres-assertion-missing"
ASSERTIONS_DIVERGE = "assertions-diverge"
ASSERTION_NAMED_NO_TABLES = "assertion-names-no-canonical-table"
POSTGRES_URL_NOT_QUALIFIED = "postgres-url-not-driver-qualified"
CREDENTIAL_IN_ENV = "credential-in-job-env"
CREDENTIAL_EXPORTED = "credential-exported-in-run"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _job(document: dict) -> dict:
    jobs = document.get("jobs") or {}
    assert JOB in jobs, f"ci.yml no longer defines a {JOB!r} job"
    return jobs[JOB]


def _steps(job: dict) -> list[dict]:
    return [step for step in (job.get("steps") or []) if isinstance(step, dict)]


def _step_ending(job: dict, suffix: str) -> dict | None:
    return next(
        (s for s in _steps(job) if str(s.get("name") or "").endswith(suffix)), None
    )


def _database_url(step: dict | None) -> str | None:
    if not step:
        return None
    env = step.get("env") or {}
    url = env.get("DATABASE_URL")
    return url if isinstance(url, str) else None


def _assertion_body(step: dict | None) -> str | None:
    """The Python heredoc CI actually executes, or None if the step has none.

    Extracted from the parsed `run:` scalar rather than the file text, so
    indentation and comment differences do not produce phantom mismatches.
    """
    run = (step or {}).get("run")
    if not isinstance(run, str) or "<<'PY'\n" not in run:
        return None
    return run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def workflow_problems(document: dict) -> list[str]:
    """Every defect found in the gate 3 migration job. Empty means clean.

    Returns codes rather than raising so one pass can report all of them, and
    so a test can assert a specific code is produced by a specific defect.
    """
    job = _job(document)
    problems: list[str] = []

    services = job.get("services") or {}
    postgres = services.get("postgres")
    if not isinstance(postgres, dict) or not postgres.get("image"):
        problems.append(SERVICE_MISSING)
    else:
        image = postgres["image"]
        match = PINNED_POSTGRES_RE.match(image) if isinstance(image, str) else None
        if match is None:
            problems.append(IMAGE_FLOATING)
        elif match.group("tag") == "latest" or "." not in match.group("tag"):
            # Digest-pinned to a floating or major-only tag still lets the engine
            # under test change, so it is the same defect as no pin at all.
            problems.append(IMAGE_FLOATING)

    sqlite_step = _step_ending(job, SQLITE_APPLY)
    postgres_step = _step_ending(job, POSTGRES_APPLY)
    sqlite_url = _database_url(sqlite_step)
    postgres_url = _database_url(postgres_step)

    # The SQLite run is retained. Replacing it with the PostgreSQL run would
    # satisfy a naive "both engines" check while losing coverage.
    if sqlite_step is None or not (sqlite_url or "").startswith("sqlite:///"):
        problems.append(SQLITE_RUN_MISSING)
    if postgres_step is None or not (postgres_url or "").startswith("postgresql"):
        problems.append(POSTGRES_RUN_MISSING)
    if _step_ending(job, POSTGRES_ROLLBACK) is None:
        problems.append(POSTGRES_ROLLBACK_MISSING)

    sqlite_assertion = _assertion_body(sqlite_step)
    postgres_assertion = _assertion_body(postgres_step)
    if not postgres_assertion:
        problems.append(POSTGRES_ASSERTION_MISSING)
    if not sqlite_assertion:
        problems.append(POSTGRES_ASSERTION_MISSING)
    elif postgres_assertion and postgres_assertion != sqlite_assertion:
        # Divergence here is the whole defect: two engines asserted by two
        # different snippets is the SQLite-only gate wearing a second hat.
        problems.append(ASSERTIONS_DIVERGE)
    if postgres_assertion and not all(
        table in postgres_assertion for table in CANONICAL_TABLES
    ):
        problems.append(ASSERTION_NAMED_NO_TABLES)

    if postgres_url and not DRIVER_QUALIFIED_RE.match(postgres_url):
        problems.append(POSTGRES_URL_NOT_QUALIFIED)

    for env in _env_maps(job):
        for key in env:
            if key in CREDENTIAL_ENV_KEYS:
                problems.append(CREDENTIAL_IN_ENV)
    for step in _steps(job):
        run = step.get("run")
        if isinstance(run, str) and CREDENTIAL_EXPORT_RE.search(run):
            problems.append(CREDENTIAL_EXPORTED)

    return sorted(set(problems))


def _env_maps(job: dict) -> list[dict]:
    maps = []
    if isinstance(job.get("env"), dict):
        maps.append(job["env"])
    for service in (job.get("services") or {}).values():
        if isinstance(service, dict) and isinstance(service.get("env"), dict):
            maps.append(service["env"])
    for step in _steps(job):
        if isinstance(step.get("env"), dict):
            maps.append(step["env"])
    return maps


_CLEAN_WORKFLOW = """
name: CI
jobs:
  migrations:
    name: Schema migrations (gate 3)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652
        env:
          POSTGRES_USER: gate3
          POSTGRES_DB: gate3
          POSTGRES_HOST_AUTH_METHOD: trust
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U gate3 -d gate3"
    steps:
      - name: Checkout
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
      - name: Apply every migration to an empty SQLite database
        env:
          DATABASE_URL: sqlite:///${RUNNER_TEMP}/gate3.db
        run: |
          set -euo pipefail
          uv run --frozen python - <<'PY'
          import os
          required = {"projects", "graphs", "simulations", "reports",
                      "dw_runs", "dw_paths"}
          PY
      - name: Apply every migration to an empty PostgreSQL database
        env:
          DATABASE_URL: postgresql+psycopg://gate3@127.0.0.1:5432/gate3
        run: |
          set -euo pipefail
          uv run --frozen python - <<'PY'
          import os
          required = {"projects", "graphs", "simulations", "reports",
                      "dw_runs", "dw_paths"}
          PY
      - name: Roll the SQLite migrations back and forward
        env:
          DATABASE_URL: sqlite:///${RUNNER_TEMP}/gate3.db
        run: uv run --frozen alembic downgrade base
      - name: Roll the PostgreSQL migrations back and forward
        env:
          DATABASE_URL: postgresql+psycopg://gate3@127.0.0.1:5432/gate3
        run: uv run --frozen alembic downgrade base
"""

# Inline so the falsification does not depend on the file under test staying
# broken in the same way.
CLEAN_DOCUMENT = yaml.safe_load(_CLEAN_WORKFLOW)


def _mutated() -> dict:
    """A fresh deep copy, so no mutation leaks into the next case."""
    return copy.deepcopy(CLEAN_DOCUMENT)


def test_workflow_file_is_valid_yaml_and_parses_to_the_expected_shape():
    """`yaml.safe_load` raising here means the gate file itself is malformed,
    and every other assertion in this module would be reading a stub."""
    document = _load(CI_WORKFLOW)

    assert isinstance(document, dict)
    assert "jobs" in document
    assert isinstance(document["jobs"], dict)


def test_gate3_job_has_no_problems():
    """The real workflow must satisfy every check at once."""
    assert workflow_problems(_load(CI_WORKFLOW)) == []


def test_the_clean_inline_fixture_also_has_no_problems():
    """The checker is not a universal rejection.

    Without this, a checker that flagged everything would satisfy
    `test_gate3_job_has_no_problems` only by the real file being unparseable.
    """
    assert workflow_problems(CLEAN_DOCUMENT) == []


@pytest.mark.parametrize(
    "code",
    [
        SERVICE_MISSING,
        IMAGE_FLOATING,
        SQLITE_RUN_MISSING,
        POSTGRES_RUN_MISSING,
        POSTGRES_ROLLBACK_MISSING,
        POSTGRES_ASSERTION_MISSING,
        ASSERTIONS_DIVERGE,
        ASSERTION_NAMED_NO_TABLES,
        POSTGRES_URL_NOT_QUALIFIED,
        CREDENTIAL_IN_ENV,
        CREDENTIAL_EXPORTED,
    ],
)
def test_each_check_detects_its_own_defect(code: str):
    """Falsification: every code must be reachable, or it is dead.

    Each mutation breaks exactly one property of the clean fixture. If a
    mutation stops producing its code, either the checker went blind or the
    fixture stopped describing the defect it claims to.
    """
    document = _mutated()
    job = document["jobs"][JOB]

    if code == SERVICE_MISSING:
        del job["services"]
    elif code == IMAGE_FLOATING:
        job["services"]["postgres"]["image"] = "postgres:latest"
    elif code == SQLITE_RUN_MISSING:
        # The trap: dropping SQLite while keeping PostgreSQL still satisfies a
        # naive "both engines referenced" check.
        job["steps"] = [
            s
            for s in job["steps"]
            if not str(s["name"]).endswith("empty SQLite database")
        ]
        job["steps"] = [
            s for s in job["steps"] if not str(s["name"]).endswith("SQLite migrations back and forward")
        ]
    elif code == POSTGRES_RUN_MISSING:
        job["steps"] = [
            s
            for s in job["steps"]
            if not str(s["name"]).endswith("empty PostgreSQL database")
        ]
        job["steps"] = [
            s for s in job["steps"] if not str(s["name"]).endswith("PostgreSQL migrations back and forward")
        ]
    elif code == POSTGRES_ROLLBACK_MISSING:
        job["steps"] = [
            s
            for s in job["steps"]
            if not str(s["name"]).endswith("PostgreSQL migrations back and forward")
        ]
    elif code == POSTGRES_ASSERTION_MISSING:
        # The exact regression this module exists for: a PostgreSQL step that
        # migrates but asserts nothing.
        target = _step_ending(job, POSTGRES_APPLY)
        target["run"] = "set -euo pipefail\nuv run --frozen alembic upgrade head\n"
    elif code == ASSERTIONS_DIVERGE:
        target = _step_ending(job, POSTGRES_APPLY)
        target["run"] = re.sub(r"dw_paths", "dw_path_sets", target["run"])
    elif code == ASSERTION_NAMED_NO_TABLES:
        # Structural substitution, not a literal block match: the heredoc is
        # re-indented by whoever edits the workflow, and a literal match here
        # would silently stop mutating anything.
        target = _step_ending(job, POSTGRES_APPLY)
        target["run"] = re.sub(r"required = \{[^}]*\}", "required = set()", target["run"])
        # Keep the two bodies identical so this is the only defect reported.
        _step_ending(job, SQLITE_APPLY)["run"] = target["run"]
    elif code == POSTGRES_URL_NOT_QUALIFIED:
        target = _step_ending(job, POSTGRES_APPLY)
        target["env"]["DATABASE_URL"] = "postgresql://gate3@127.0.0.1:5432/gate3"
    elif code == CREDENTIAL_IN_ENV:
        job["env"] = {"SECRET_KEY": "gate3-only"}
    elif code == CREDENTIAL_EXPORTED:
        target = _step_ending(job, POSTGRES_APPLY)
        target["run"] += '\nexport SECRET_KEY="gate3-only"\n'
    else:  # pragma: no cover - a new code with no mutation is itself a bug
        raise AssertionError(f"no falsification mutation for {code}")

    assert code in workflow_problems(document), (
        f"{code} is unreachable: the mutation that should trigger it did not. "
        "Either the check cannot fail or the fixture no longer describes it."
    )


def test_service_image_is_pinned_by_digest_to_an_exact_tag():
    """Named separately from the code-level sweep: the pin is the part a reader
    will want to see, and the tag must be exact, not `latest` and not `17`."""
    job = _job(_load(CI_WORKFLOW))
    image = (job.get("services") or {}).get("postgres", {}).get("image", "")

    match = PINNED_POSTGRES_RE.match(image)
    assert match, f"postgres service image is not tag@sha256 pinned: {image!r}"
    assert match.group("tag") == "17.11-bookworm"
    assert match.group("digest") != "0" * 64


def test_gate3_job_runs_both_engines_and_keeps_the_sqlite_run():
    """Quoted rather than only aggregated: these are the two URLs CI uses."""
    job = _job(_load(CI_WORKFLOW))

    assert _database_url(_step_ending(job, SQLITE_APPLY)).startswith("sqlite:///")
    assert _database_url(_step_ending(job, POSTGRES_APPLY)).startswith(
        "postgresql+psycopg://"
    )
    # Rollback is proven on both engines: a downgrade that only ever ran on
    # SQLite is not a rollback.
    assert _database_url(_step_ending(job, SQLITE_ROLLBACK)).startswith("sqlite:///")
    assert _database_url(_step_ending(job, POSTGRES_ROLLBACK)).startswith(
        "postgresql+psycopg://"
    )


def test_both_engines_run_the_same_canonical_table_assertion():
    """Byte-identical, and naming the canonical tables.

    An empty or table-free body satisfies "both engines assert" while proving
    nothing, which is why the table names are asserted too.
    """
    job = _job(_load(CI_WORKFLOW))
    sqlite_assertion = _assertion_body(_step_ending(job, SQLITE_APPLY))
    postgres_assertion = _assertion_body(_step_ending(job, POSTGRES_APPLY))

    assert sqlite_assertion is not None, "the SQLite step lost its assertion"
    assert postgres_assertion is not None, "the PostgreSQL step has no assertion"
    assert postgres_assertion == sqlite_assertion, (
        "the two engines no longer run the same assertion; the PostgreSQL run "
        "would drift into a weaker check than the SQLite one"
    )
    for table in CANONICAL_TABLES:
        assert table in postgres_assertion, f"{table} is not asserted"


def test_gate3_job_carries_no_credentials():
    """Structural, over parsed env keys -- the job's own comment names these
    variables in prose, so a text search over the file would false-positive."""
    job = _job(_load(CI_WORKFLOW))

    for env in _env_maps(job):
        assert not (set(env) & set(CREDENTIAL_ENV_KEYS)), (
            f"the migrations job gained credential env {sorted(set(env) & set(CREDENTIAL_ENV_KEYS))}. "
            "`migrations/env.py` must stay independent of the web app's secrets "
            "or the credential gate returns to the migration path."
        )

    # The only permitted step-level variable is the throwaway database URL.
    # EXPECTED_HEAD is derived inside the run body and checked below, not passed
    # through env, so an env key of that name would mean something was changed.
    for step in _steps(job):
        env = step.get("env") or {}
        assert set(env) <= {"DATABASE_URL"}, (
            f"unexpected env on step {step.get('name')!r}: {sorted(env)}"
        )
        run = step.get("run") or ""
        assert not CREDENTIAL_EXPORT_RE.search(run), (
            f"step {step.get('name')!r} exports a credential into the migration "
            "environment"
        )


def test_the_workflow_keeps_its_single_linear_head_and_autogenerate_refusal():
    """The engine change must not have displaced the two pre-existing
    assertions that have nothing to do with which engine is under test."""
    job = _job(_load(CI_WORKFLOW))
    names = [str(s.get("name") or "") for s in _steps(job)]

    assert any("one linear migration head" in name for name in names), names
    assert any("autogenerate" in name for name in names), names