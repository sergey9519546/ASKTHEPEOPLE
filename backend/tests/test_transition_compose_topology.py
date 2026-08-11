"""Locks for the single-host TRANSITION deployment topology."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"
WEB_DOCKERFILE = REPO_ROOT / "Dockerfile"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TRANSITION_ENV_EXAMPLE = REPO_ROOT / ".env.transition.example"
TRANSITION_BUILD_ENV_EXAMPLE = REPO_ROOT / ".env.transition.build.example"
RAILWAY_CONFIG = REPO_ROOT / "railway.toml"
RAILWAY_BLOCKER = REPO_ROOT / "backend" / "scripts" / "block_legacy_railway_deploy.py"
TRANSITION_BUILD_VALIDATOR = (
    REPO_ROOT / "backend" / "scripts" / "validate_transition_build_identity.py"
)
TRANSITION_STORAGE_PREPARER = (
    REPO_ROOT / "backend" / "scripts" / "prepare_transition_storage.py"
)
SHARED_UPLOAD_TARGET = "/app/backend/uploads"
SHARED_UPLOAD_SOURCE = "./.transition-data/uploads"
REDIS_IMAGE = (
    "redis:7.4.2-alpine@"
    "sha256:02419de7eddf55aa5bcf49efb74e88fa8d931b4d77c07eff8a6b2144472b6952"
)


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def _volume_targets(service: dict) -> set[str]:
    targets: set[str] = set()
    for volume in service.get("volumes", []):
        if isinstance(volume, str):
            targets.add(volume.rsplit(":", 1)[-1])
        elif isinstance(volume, dict) and isinstance(volume.get("target"), str):
            targets.add(volume["target"])
    return targets


def _volume_sources(service: dict) -> set[str]:
    sources: set[str] = set()
    for volume in service.get("volumes", []):
        if isinstance(volume, str):
            sources.add(volume.rsplit(":", 1)[0])
        elif isinstance(volume, dict) and isinstance(volume.get("source"), str):
            sources.add(volume["source"])
    return sources


def test_transition_compose_has_all_required_single_host_services() -> None:
    services = _compose()["services"]

    assert {"askthepeople", "worker", "beat", "redis"} <= set(services)
    assert services["askthepeople"]["build"]["dockerfile"] == "Dockerfile"
    assert services["worker"]["build"]["dockerfile"] == "Dockerfile.worker"
    assert services["beat"]["build"]["dockerfile"] == "Dockerfile.worker"


def test_transition_processes_share_inputs_and_artifacts_on_one_host() -> None:
    services = _compose()["services"]

    for service_name in ("askthepeople", "worker", "beat"):
        assert SHARED_UPLOAD_TARGET in _volume_targets(services[service_name])
        assert SHARED_UPLOAD_SOURCE in _volume_sources(services[service_name])
        assert "./backend/uploads" not in _volume_sources(services[service_name])
        assert (
            services[service_name]["environment"][
                "TRANSITION_STORAGE_MARKER_REQUIRED"
            ]
            == "true"
        )
        assert (
            services[service_name]["labels"]["com.askthepeople.deployment-mode"]
            == "transition-single-host"
        )

    entrypoint = (REPO_ROOT / "backend" / "docker-entrypoint.sh").read_text(
        encoding="utf-8"
    )
    assert "TRANSITION_STORAGE_MARKER_REQUIRED" in entrypoint
    assert "prepare_transition_storage.py" in entrypoint
    verifier = TRANSITION_STORAGE_PREPARER.read_text(encoding="utf-8")
    assert ".transition-store-v1" in verifier
    assert "transition-storage/v1" in verifier


def test_transition_processes_use_the_compose_redis_broker() -> None:
    services = _compose()["services"]
    expected_redis_url = "redis://redis:6379/0"

    for service_name in ("askthepeople", "worker", "beat"):
        environment = services[service_name]["environment"]
        assert environment["REDIS_URL"] == expected_redis_url
        assert environment["CELERY_BROKER_URL"] == expected_redis_url
        assert environment["CELERY_RESULT_BACKEND"] == expected_redis_url
        assert services[service_name]["depends_on"]["redis"]["condition"] == "service_healthy"

    assert services["redis"]["healthcheck"]["test"] == ["CMD", "redis-cli", "ping"]
    assert services["redis"]["image"] == REDIS_IMAGE
    assert REDIS_IMAGE in CI_WORKFLOW.read_text(encoding="utf-8")


def test_transition_compose_runs_worker_and_scheduler_explicitly() -> None:
    services = _compose()["services"]
    worker_command = " ".join(services["worker"]["command"])
    beat_command = " ".join(services["beat"]["command"])

    assert "worker_wrapper.sh" in worker_command
    assert services["worker"]["working_dir"] == "/app/backend"
    assert services["beat"]["working_dir"] == "/app/backend"
    assert "cd /app/backend" in beat_command
    assert "celery" in beat_command
    assert " beat " in f" {beat_command} "
    assert services["beat"]["healthcheck"] == {"disable": True}


def test_transition_host_has_bounded_processes_memory_and_logs() -> None:
    services = _compose()["services"]

    expected_limits = {
        "redis": ("768m", 0.15, 128),
        "askthepeople": ("1536m", 0.5, 256),
        "worker": ("7g", 1.25, 512),
        "beat": ("512m", 0.1, 128),
    }
    for service_name, (memory, cpus, pids) in expected_limits.items():
        service = services[service_name]
        assert service["mem_limit"] == memory
        assert service["cpus"] == cpus
        assert service["pids_limit"] == pids
        assert service["logging"] == {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        }

    redis_command = services["redis"]["command"]
    assert ["--maxmemory", "512mb"] == redis_command[-4:-2]
    assert ["--maxmemory-policy", "noeviction"] == redis_command[-2:]
    wrapper = (REPO_ROOT / "backend" / "scripts" / "worker_wrapper.sh").read_text(
        encoding="utf-8"
    )
    assert "--concurrency=1" in wrapper
    assert "--concurrency=2" not in wrapper


def test_web_image_validation_cannot_bake_the_runtime_database() -> None:
    dockerfile = WEB_DOCKERFILE.read_text(encoding="utf-8")

    assert "DATABASE_URL': 'sqlite:////tmp/build-validation.db'" in dockerfile
    assert "rm -f /tmp/build-validation.db" in dockerfile


def test_legacy_split_service_deploy_is_disabled_by_default() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "vars.RAILWAY_PRODUCTION_DEPLOYMENT_ENABLED == 'true'" in workflow


def test_transition_topology_cannot_implicitly_load_the_local_dev_env() -> None:
    services = _compose()["services"]

    for service_name in ("askthepeople", "worker", "beat"):
        env_files = services[service_name]["env_file"]
        assert env_files == [{"path": ".env.transition", "required": True}]

    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env.transition" in gitignore


def test_transition_env_template_is_fail_closed_and_filesystem_scoped() -> None:
    template = TRANSITION_ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "FLASK_DEBUG=false" in template
    assert "REQUIRE_APP_AUTH=true" in template
    assert "ALLOW_RUNTIME_SETTINGS=false" in template
    assert "USE_SUPABASE_PERSISTENCE=false" in template
    assert "DATABASE_URL=sqlite:////app/backend/uploads/transition.db" in template
    assert "SECRET_KEY=\n" in template
    assert "APP_TOKEN=\n" in template
    assert "ZEP_API_KEY=\n" in template
    assert "LLM_API_KEY=\n" in template


def test_transition_zero_cost_claim_is_bounded_and_uses_free_tier_candidates() -> None:
    template = TRANSITION_ENV_EXAMPLE.read_text(encoding="utf-8")
    runbook = (REPO_ROOT / "docs" / "release" / "RUNBOOK.md").read_text(
        encoding="utf-8"
    )

    assert "LLM_BASE_URL=https://api.groq.com/openai/v1" in template
    assert "LLM_MODEL_NAME=llama-3.1-8b-instant" in template
    assert "LLM_BOOST_MODEL_NAME=openai/gpt-oss-120b" in template
    assert "api.openai.com" not in template
    assert "not an end-to-end zero-cost guarantee" in runbook
    assert "unverified provider/model candidate" in runbook
    assert "https://console.groq.com/docs/rate-limits" in runbook
    assert "https://www.getzep.com/pricing/" in runbook
    assert "no automatic top-up" in runbook


def test_transition_images_receive_one_build_only_revision() -> None:
    services = _compose()["services"]

    for service_name in ("askthepeople", "worker", "beat"):
        assert services[service_name]["build"]["args"] == {
            "BUILD_REVISION": (
                "${BUILD_REVISION:?Set BUILD_REVISION to the exact git commit}"
            ),
        }

    runtime_template = TRANSITION_ENV_EXAMPLE.read_text(encoding="utf-8")
    build_template = TRANSITION_BUILD_ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "BUILD_REVISION" not in runtime_template
    assert build_template == (
        "# Build interpolation only; never pass this file into a container.\n"
        "BUILD_REVISION=\n"
    )

    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env.transition.build" in gitignore


def test_images_write_and_validate_a_root_owned_revision_file() -> None:
    for relative in ("Dockerfile", "Dockerfile.worker"):
        dockerfile = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "ARG BUILD_REVISION\n" in dockerfile
        assert "ARG BUILD_REVISION=unknown" not in dockerfile
        assert "/usr/share/askthepeople/build-revision" in dockerfile
        assert "^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$" in dockerfile
        assert "BUILD_REVISION=${BUILD_REVISION}" not in dockerfile


def test_worker_image_has_truthful_healthcheck_and_ci_smoke() -> None:
    worker_dockerfile = (REPO_ROOT / "Dockerfile.worker").read_text(
        encoding="utf-8"
    )
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "HEALTHCHECK" in worker_dockerfile
    assert "127.0.0.1:8080/health" in worker_dockerfile
    assert "file: Dockerfile.worker" in workflow
    assert "askthepeople-worker-ci:${{ github.sha }}" in workflow
    assert "Verify worker availability and beat command boundary" in workflow


def test_operator_commands_use_build_only_compose_interpolation_file() -> None:
    for relative in ("README.md", "docs/release/RUNBOOK.md"):
        content = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "--env-file .env.transition.build" in content
        assert "--env-file .env.transition config" not in content
        assert "validate_transition_build_identity.py" in content
        assert "prepare_transition_storage.py" in content
        assert "env -u BUILD_REVISION docker compose" in content
        assert "Docker Compose 2.24" in content
        assert "set -euo pipefail" in content
        assert "umask 077" in content
        assert "test ! -e .env.transition" in content
        assert "install -m 600 .env.transition.example .env.transition" in content
        assert "cp .env.transition.example .env.transition" not in content

    runbook = (REPO_ROOT / "docs" / "release" / "RUNBOOK.md").read_text(
        encoding="utf-8"
    )
    assert "backup of `.transition-data/uploads`" in runbook
    assert "backup of `backend/uploads`" not in runbook
    assert "python -m scripts.assert_celery_quiescent" in runbook
    assert "python /app/backend/scripts/assert_celery_quiescent.py" not in runbook
    assert "recover_worker_after_failed_drain" in runbook
    assert "restart worker" in runbook
    assert "trap - EXIT HUP INT TERM" in runbook
    assert "recover_worker_after_failed_drain 129" in runbook
    assert "recover_worker_after_failed_drain 130" in runbook
    assert "recover_worker_after_failed_drain 143" in runbook


def test_transition_build_identity_validator_rejects_stale_or_extra_values(
    tmp_path,
) -> None:
    repository = tmp_path / "clean-repository"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "transition-test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Transition Test"],
        cwd=repository,
        check=True,
    )
    (repository / "tracked.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "test fixture"],
        cwd=repository,
        check=True,
    )
    exact_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        text=True,
    ).strip()
    build_env = tmp_path / "build.env"
    build_env.write_text(f"BUILD_REVISION={exact_revision}\n", encoding="ascii")

    accepted = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_BUILD_VALIDATOR),
            "--build-env",
            str(build_env),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert accepted.returncode == 0
    assert accepted.stdout.strip() == "transition_build_identity_ok"
    assert accepted.stderr == ""

    build_env.write_text(f"BUILD_REVISION={'f' * 40}\nEXTRA=value\n", encoding="ascii")
    rejected = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_BUILD_VALIDATOR),
            "--build-env",
            str(build_env),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert rejected.returncode == 78
    assert rejected.stdout == ""
    assert rejected.stderr.strip() == "transition_build_identity_invalid"

    build_env.write_text(f"BUILD_REVISION={exact_revision}\n", encoding="ascii")
    (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    dirty = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_BUILD_VALIDATOR),
            "--build-env",
            str(build_env),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert dirty.returncode == 78
    assert dirty.stdout == ""
    assert dirty.stderr.strip() == "transition_build_identity_invalid"


def test_transition_storage_preflight_refuses_unowned_existing_data(tmp_path) -> None:
    repository = tmp_path / "repository"
    storage = repository / ".transition-data" / "uploads"
    storage.mkdir(parents=True)
    (storage / "old-source.txt").write_text("old", encoding="utf-8")

    refused = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_STORAGE_PREPARER),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert refused.returncode == 78
    assert refused.stdout == ""
    assert refused.stderr.strip() == "transition_storage_unowned"


def test_transition_storage_preflight_claims_empty_store_and_reuses_it(tmp_path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    first = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_STORAGE_PREPARER),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    marker = repository / ".transition-data" / "uploads" / ".transition-store-v1"

    assert first.returncode == 0
    assert first.stdout.strip() == "transition_storage_ready"
    assert first.stderr == ""
    assert marker.read_text(encoding="ascii") == "transition-storage/v1\n"

    verified = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_STORAGE_PREPARER),
            "--verify-store",
            str(marker.parent),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert verified.returncode == 0
    assert verified.stdout.strip() == "transition_storage_verified"
    assert verified.stderr == ""

    (marker.parent / "state.json").write_text("{}", encoding="utf-8")
    second = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_STORAGE_PREPARER),
            "--repository",
            str(repository),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert second.returncode == 0
    assert second.stdout.strip() == "transition_storage_ready"
    assert second.stderr == ""

    marker.write_bytes(b"x" * 1024 * 1024)
    oversized = subprocess.run(
        [
            sys.executable,
            str(TRANSITION_STORAGE_PREPARER),
            "--verify-store",
            str(marker.parent),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert oversized.returncode == 78
    assert oversized.stdout == ""
    assert oversized.stderr.strip() == "transition_storage_invalid"


def test_legacy_railway_config_has_a_fail_closed_predeploy_sentinel() -> None:
    with RAILWAY_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)

    assert config["deploy"]["preDeployCommand"] == [
        "python /app/backend/scripts/block_legacy_railway_deploy.py",
    ]

    result = subprocess.run(
        [sys.executable, str(RAILWAY_BLOCKER)],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 78
    assert result.stdout == ""
    assert result.stderr.strip() == "legacy_split_service_deployment_disabled"
