"""Static release-contract checks for Zep readiness diagnostics."""

from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _readiness_step(workflow: str) -> str:
    marker = "      - name: Verify Zep-backed production readiness"
    start = workflow.index(marker)
    next_step = workflow.find("\n      - name:", start + len(marker))
    return workflow[start:] if next_step == -1 else workflow[start:next_step]


_LOCKED_READINESS_FRAGMENTS = (
    "TESTED_SHA: ${{ inputs.tested_sha }}",
    '--arg tested_sha "$TESTED_SHA"',
    '.revision == $tested_sha',
    '.scope == "web"',
    '.components.zep == "ok"',
    '.dependencies.zep.status == "ok"',
    '.dependencies.zep.reason == "available"',
    ".dependencies.zep.stale == false",
    '.capabilities.web_graph_backed == "ready"',
)


def _has_locked_readiness_contract(workflow: str) -> bool:
    try:
        step = _readiness_step(workflow)
    except ValueError:
        return False
    return all(fragment in step for fragment in _LOCKED_READINESS_FRAGMENTS)


def test_deploy_workflow_gates_on_sanitized_zep_readiness():
    workflow = (REPOSITORY_ROOT / ".github/workflows/deploy.yml").read_text(
        encoding="utf-8"
    )

    assert _has_locked_readiness_contract(workflow)
    step = _readiness_step(workflow)
    assert "/health/readiness" in step
    assert '.status == "ready"' in step
    assert "ZEP_API_KEY: ${{" not in workflow
    assert "readiness_reason" in step
    assert (
        "available|not_configured|authentication_failed|rate_limited|timeout|"
        "unavailable|probe_failed"
    ) in step
    assert 'printf \'%s\' "$readiness"' not in step
    assert (
        "Production web readiness confirms the web graph dependency; "
        "worker reachability was not evaluated."
    ) in step


@pytest.mark.parametrize("fragment", _LOCKED_READINESS_FRAGMENTS)
def test_each_deploy_readiness_predicate_mutation_is_rejected(fragment):
    workflow = (REPOSITORY_ROOT / ".github/workflows/deploy.yml").read_text(
        encoding="utf-8"
    )
    assert _has_locked_readiness_contract(workflow)

    mutated = _readiness_step(workflow).replace(fragment, "MUTATED", 1)
    assert not _has_locked_readiness_contract(mutated)


def test_worker_startup_rejects_missing_zep_key_without_network_access():
    script_path = REPOSITORY_ROOT / "backend/scripts/check_worker_zep_config.py"
    assert script_path.is_file(), "worker Zep configuration check is missing"

    spec = importlib.util.spec_from_file_location("check_worker_zep_config", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output = io.StringIO()
    assert module.main({}, stderr=output) != 0
    assert "ZEP_API_KEY is required" in output.getvalue()

    from app.utils.worker_startup import (
        WorkerStartupConfigurationError,
        validate_worker_zep_configuration,
    )

    assert module.validate_worker_zep_configuration is validate_worker_zep_configuration
    with pytest.raises(WorkerStartupConfigurationError, match="ZEP_API_KEY is required"):
        validate_worker_zep_configuration({})
    assert validate_worker_zep_configuration({"ZEP_API_KEY": "configured"}) is None


def test_worker_wrapper_validates_before_starting_health_or_celery():
    wrapper = (REPOSITORY_ROOT / "backend/scripts/worker_wrapper.sh").read_text(
        encoding="utf-8"
    )

    validation = wrapper.index("check_worker_zep_config.py")
    health = wrapper.index("worker_health.py")
    celery = wrapper.index("celery -A app.celery_app worker")
    assert validation < celery < health


def test_procfile_process_types_are_fail_closed_for_split_platforms():
    procfile = (REPOSITORY_ROOT / "Procfile").read_text(encoding="utf-8")
    process_lines = [line for line in procfile.splitlines() if ":" in line]

    assert {line.split(":", 1)[0] for line in process_lines} == {
        "web",
        "worker",
        "beat",
    }
    assert all("block_legacy_railway_deploy.py" in line for line in process_lines)
    assert "celery" not in procfile


def test_actual_celery_worker_initialization_aborts_without_zep_key():
    environment = os.environ.copy()
    environment.update(
        {
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key",
            "LLM_API_KEY": "ci-test-key",
            "ZEP_API_KEY": "",
            "CELERY_BROKER_URL": "memory://",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "REDIS_URL": "memory://",
        }
    )
    command = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.celery_app",
        "worker",
        "--pool=solo",
        "--concurrency=1",
        "--loglevel=WARNING",
        "--without-gossip",
        "--without-mingle",
        "--without-heartbeat",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT / "backend",
            env=environment,
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Celery worker did not fail fast on missing ZEP_API_KEY")

    rendered = f"{completed.stdout}\n{completed.stderr}"
    assert completed.returncode != 0
    assert "ZEP_API_KEY is required" in rendered
    assert "ready" not in rendered.lower()
