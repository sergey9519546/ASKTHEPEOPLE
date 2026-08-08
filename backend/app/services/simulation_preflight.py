"""
Simulation preflight validation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..config import Config
from ..utils.input_policy import PREPARED_PROFILE_MAX
from .camel_model_factory import (
    validate_camel_runtime_imports,
    validate_required_model_env,
    write_model_resolution,
)
from .decision_lens_repository import (
    DecisionLensAdmissionError,
    DecisionLensRepository,
    DecisionLensRepositoryError,
)
from .decision_lens_runtime_adapter import (
    DecisionLensRuntimeAdapterError,
    DecisionLensRuntimeAdapterV1,
    build_runtime_adapters,
)
from .simulation_artifacts import (
    canonical_agents_path,
    preflight_path,
    read_json,
    run_manifest_path,
    validate_reddit_profiles,
    validate_twitter_rows,
)
from .simulation_config_generator import (
    DECISION_LENS_CONFIG_CONSUMPTION,
    DECISION_LENS_CONFIG_CONSUMPTION_REGISTRY,
    DECISION_LENS_CONFIG_CONSUMPTION_REGISTRY_VERSION,
    SimulationConfigGenerator,
)

DECISION_LENS_ADMISSION_VALIDATOR_VERSION = "decision-lens-admission/v1"
DECISION_LENS_RUNTIME_FILENAME = "decision_lens_runtime.v1.json"
_PROHIBITED_IDENTITY_KEYS = frozenset(
    {
        "age",
        "bio",
        "biography",
        "gender",
        "mbti",
        "persona",
        "profession",
    }
)


def _read_twitter_rows(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _validate_config_schema(config: dict[str, Any]) -> list[str]:
    errors = []
    required_top_level = [
        "simulation_id",
        "project_id",
        "graph_id",
        "time_config",
        "agent_configs",
        "context_profile",
        "network_bootstrap",
        "event_schedule",
        "bootstrap_posts",
        "platform_profiles",
    ]
    for field in required_top_level:
        if field not in config:
            errors.append(f"missing config field: {field}")

    for index, agent in enumerate(config.get("agent_configs", [])):
        for field in (
            "agent_id",
            "entity_uuid",
            "entity_name",
            "entity_type",
            "normalized_role",
            "reaction_style",
            "conflict_tolerance",
            "authority_sensitivity",
            "novelty_seeking",
            "platform_preference",
        ):
            if field not in agent:
                errors.append(f"agent_configs[{index}] missing {field}")

    return errors


def _artifact_digest(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _contains_prohibited_identity_key(value: Any) -> bool:
    if isinstance(value, dict):
        key_tokens = {
            token
            for key in value
            for token in str(key).lower().replace("-", "_").split("_")
        }
        if _PROHIBITED_IDENTITY_KEYS.intersection(key_tokens):
            return True
        return any(_contains_prohibited_identity_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_prohibited_identity_key(item) for item in value)
    return False


def _atomic_write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(200):
            try:
                os.replace(temp_name, destination)
                break
            except PermissionError:
                if attempt == 199:
                    raise
                time.sleep(0.005)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _runtime_admission_error(
    code: str = "decision_lens_runtime_invalid",
    remediation: str = "finalize_current_decision_lens_review",
) -> DecisionLensAdmissionError:
    return DecisionLensAdmissionError(code, remediation)


def assert_decision_lens_execution_admission(
    simulation_dir: str,
    *,
    production: bool | None = None,
) -> dict[str, Any]:
    """Verify approval and every derived runtime identity before execution."""

    repository = DecisionLensRepository(
        simulation_dir,
        production=not Config.DEBUG if production is None else production,
    )
    try:
        repository.assert_execution_approved()
        artifact = repository.get_current_artifact()
        review = repository.get_current_review()
    except DecisionLensAdmissionError:
        raise
    except DecisionLensRepositoryError as exc:
        raise DecisionLensAdmissionError(
            "decision_lens_review_required",
            "regenerate_decision_lenses",
        ) from exc
    if artifact is None or review is None:
        raise DecisionLensAdmissionError(
            "decision_lens_review_required",
            "regenerate_decision_lenses",
        )

    runtime_path = os.path.join(simulation_dir, DECISION_LENS_RUNTIME_FILENAME)
    config_path = os.path.join(simulation_dir, "simulation_config.json")
    try:
        runtime_payload = read_json(runtime_path, default=None)
        config = read_json(config_path, default=None)
        if not isinstance(runtime_payload, dict) or not isinstance(config, dict):
            raise _runtime_admission_error()
        if set(runtime_payload) != {
            "schema_version",
            "source_artifact_sha256",
            "source_review_sha256",
            "adapters",
        }:
            raise _runtime_admission_error()
        if runtime_payload["schema_version"] != "decision-lens-runtime/v1":
            raise _runtime_admission_error()
        if (
            runtime_payload["source_artifact_sha256"] != artifact.artifact_sha256
            or runtime_payload["source_review_sha256"] != review.review_sha256
        ):
            raise _runtime_admission_error()
        persisted_adapters = tuple(
            DecisionLensRuntimeAdapterV1.model_validate(item)
            for item in runtime_payload["adapters"]
        )
        expected_adapters = build_runtime_adapters(artifact, review)
        if persisted_adapters != expected_adapters:
            raise _runtime_admission_error()
        if _contains_prohibited_identity_key(runtime_payload):
            raise _runtime_admission_error()

        context = config.get("context_profile")
        agent_configs = config.get("agent_configs")
        if not isinstance(context, dict) or not isinstance(agent_configs, list):
            raise _runtime_admission_error()
        if context.get("adapter_version") != "decision-lens-runtime/v1":
            raise _runtime_admission_error()
        if context.get("source_artifact_sha256s") != [artifact.artifact_sha256]:
            raise _runtime_admission_error()
        if context.get("source_review_sha256s") != [review.review_sha256]:
            raise _runtime_admission_error()
        if (
            context.get("runtime_control_registry_version")
            != DECISION_LENS_CONFIG_CONSUMPTION_REGISTRY_VERSION
        ):
            raise _runtime_admission_error()
        consumed_controls = context.get("consumed_runtime_controls")
        if not isinstance(consumed_controls, dict) or not set(
            consumed_controls
        ).issubset(DECISION_LENS_CONFIG_CONSUMPTION):
            raise _runtime_admission_error("inert_runtime_control")

        platform_profiles = config.get("platform_profiles")
        if not isinstance(platform_profiles, dict):
            raise _runtime_admission_error()
        twitter_profile = platform_profiles.get("twitter")
        reddit_profile = platform_profiles.get("reddit")
        if not isinstance(twitter_profile, dict) or not isinstance(
            reddit_profile, dict
        ):
            raise _runtime_admission_error()
        enable_twitter = twitter_profile.get("enabled")
        enable_reddit = reddit_profile.get("enabled")
        if type(enable_twitter) is not bool or type(enable_reddit) is not bool:
            raise _runtime_admission_error()

        expected_config = SimulationConfigGenerator.generate_from_decision_lenses(
            simulation_id=config.get("simulation_id"),
            project_id=config.get("project_id"),
            graph_id=config.get("graph_id"),
            simulation_requirement=config.get("simulation_requirement"),
            adapters=persisted_adapters,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            runtime_controls=consumed_controls,
        ).to_dict()
        comparable_config = dict(config)
        comparable_config.pop("generated_at", None)
        expected_config.pop("generated_at", None)
        if comparable_config != expected_config:
            raise _runtime_admission_error()

        expected_agent_contract = [
            (
                adapter.agent_id,
                adapter.lens_id,
                adapter.platform_name,
                "decision_lens",
                "decision_lens",
            )
            for adapter in persisted_adapters
        ]
        actual_agent_contract = [
            (
                item.get("agent_id"),
                item.get("entity_uuid"),
                item.get("entity_name"),
                item.get("entity_type"),
                item.get("normalized_role"),
            )
            for item in agent_configs
            if isinstance(item, dict)
        ]
        if actual_agent_contract != expected_agent_contract:
            raise _runtime_admission_error()
        if _contains_prohibited_identity_key(config):
            raise _runtime_admission_error()
    except DecisionLensAdmissionError:
        raise
    except (
        DecisionLensRuntimeAdapterError,
        KeyError,
        OSError,
        TypeError,
        ValidationError,
        ValueError,
    ) as exc:
        raise _runtime_admission_error() from exc

    runtime_digest = _artifact_digest(runtime_path)
    if runtime_digest is None:
        raise _runtime_admission_error()
    semantic_prompt_hashes = {
        str(adapter.agent_id): hashlib.sha256(
            adapter.semantic_prompt.encode("utf-8")
        ).hexdigest()
        for adapter in persisted_adapters
    }
    prompt_record = artifact.prompt_record.model_dump(mode="json")
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_sha256": artifact.artifact_sha256,
        "review_id": review.review_id,
        "review_sha256": review.review_sha256,
        "authentication_strength": review.authentication_strength,
        "prompt": prompt_record,
        "schema": {"id": "decision-lens", "version": "v1"},
        "validator": {
            "id": "decision-lens-admission",
            "version": DECISION_LENS_ADMISSION_VALIDATOR_VERSION,
        },
        "runtime_adapter": {
            "id": DECISION_LENS_RUNTIME_FILENAME,
            "version": "decision-lens-runtime/v1",
            **runtime_digest,
            "agent_count": len(persisted_adapters),
            "semantic_prompt_sha256_by_agent_id": semantic_prompt_hashes,
        },
        "control_consumption_registry": {
            "version": DECISION_LENS_CONFIG_CONSUMPTION_REGISTRY_VERSION,
            "entries": DECISION_LENS_CONFIG_CONSUMPTION_REGISTRY,
        },
        "deprecated_neutral_omitted": context.get("omitted_deprecated_controls", []),
    }


def _write_run_manifest(
    simulation_dir: str,
    config: dict[str, Any],
    model_matrix: dict[str, Any],
    preflight: dict[str, Any],
    admission: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact_names = (
        "agent_profiles.canonical.json",
        "twitter_profiles.csv",
        "reddit_profiles.json",
        DECISION_LENS_RUNTIME_FILENAME,
        "simulation_config.json",
        "model_resolution.json",
        "preflight.json",
    )
    artifacts = {
        name: digest
        for name in artifact_names
        if (digest := _artifact_digest(os.path.join(simulation_dir, name))) is not None
    }
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "code_revision": (
            os.environ.get("RAILWAY_GIT_COMMIT_SHA")
            or os.environ.get("BUILD_REVISION")
            or "unknown"
        ),
        "simulation": {
            "simulation_id": config.get("simulation_id"),
            "project_id": config.get("project_id"),
            "graph_id": config.get("graph_id"),
        },
        "truth_status": {
            "human_respondents": 0,
            "external_validation": False,
            "calibration": "not_calibrated",
            "interpretation": "synthetic_scenario_exploration",
        },
        "reproducibility": {
            "deterministic": False,
            "random_seed_controlled": False,
            "replicate_count": 1,
            "limitation": (
                "Model sampling, provider behavior, and runtime scheduling can "
                "change outcomes; compare multiple runs before drawing conclusions."
            ),
        },
        "model_resolution": model_matrix,
        "preflight_status": preflight.get("status"),
        "artifacts": artifacts,
    }
    if admission is not None:
        payload["decision_lens"] = {
            "artifact_id": admission["artifact_id"],
            "artifact_sha256": admission["artifact_sha256"],
            "review_id": admission["review_id"],
            "review_sha256": admission["review_sha256"],
            "authentication_strength": admission["authentication_strength"],
            "prompt": admission["prompt"],
            "schema": admission["schema"],
            "validator": admission["validator"],
            "runtime_adapter": admission["runtime_adapter"],
            "control_consumption_registry": admission["control_consumption_registry"],
            "deprecated_neutral_omitted": admission["deprecated_neutral_omitted"],
        }
    _atomic_write_json(run_manifest_path(simulation_dir), payload)
    return payload


def run_preflight(simulation_dir: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, details: Any = None):
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "failed",
                "details": details,
            }
        )

    admission: dict[str, Any] | None = None
    try:
        admission = assert_decision_lens_execution_admission(simulation_dir)
        add_check(
            "decision_lens_execution_admission",
            True,
            {
                "artifact_id": admission["artifact_id"],
                "artifact_sha256": admission["artifact_sha256"],
                "review_id": admission["review_id"],
                "review_sha256": admission["review_sha256"],
                "runtime_adapter_sha256": admission["runtime_adapter"]["sha256"],
            },
        )
    except DecisionLensAdmissionError as exc:
        add_check(
            "decision_lens_execution_admission",
            False,
            {"code": exc.code, "remediation": exc.remediation},
        )

    canonical_agents: list[dict[str, Any]] = []
    twitter_rows: list[dict[str, Any]] = []
    reddit_profiles: list[dict[str, Any]] = []
    if admission is None:
        canonical_agents = read_json(canonical_agents_path(simulation_dir), default=[])
        canonical_errors = []
        expected_ids = list(range(len(canonical_agents)))
        actual_ids = [agent.get("agent_id") for agent in canonical_agents]
        if actual_ids != expected_ids:
            canonical_errors.append(
                "canonical agent ids must be contiguous "
                f"{expected_ids}, got {actual_ids}"
            )
        add_check(
            "canonical_agent_integrity",
            not canonical_errors,
            canonical_errors or {"count": len(canonical_agents)},
        )

        twitter_rows = _read_twitter_rows(
            os.path.join(simulation_dir, "twitter_profiles.csv")
        )
        twitter_errors = (
            validate_twitter_rows(twitter_rows)
            if twitter_rows
            else ["twitter export missing"]
        )
        add_check(
            "twitter_export_contract",
            not twitter_errors,
            twitter_errors or {"count": len(twitter_rows)},
        )

        reddit_profiles = read_json(
            os.path.join(simulation_dir, "reddit_profiles.json"), default=[]
        )
        reddit_errors = (
            validate_reddit_profiles(reddit_profiles)
            if reddit_profiles
            else ["reddit export missing"]
        )
        add_check(
            "reddit_export_contract",
            not reddit_errors,
            reddit_errors or {"count": len(reddit_profiles)},
        )

    config = read_json(
        os.path.join(simulation_dir, "simulation_config.json"), default={}
    )
    config_errors = (
        _validate_config_schema(config)
        if config
        else ["simulation_config.json missing"]
    )
    add_check(
        "config_schema",
        not config_errors,
        config_errors or {"agents": len(config.get("agent_configs", []))},
    )

    if admission is not None:
        profile_counts = {
            "decision_lens_runtime_adapters": admission["runtime_adapter"][
                "agent_count"
            ],
            "agent_configs": len(config.get("agent_configs", [])),
        }
    else:
        profile_counts = {
            "canonical_agents": len(canonical_agents),
            "twitter_profiles": len(twitter_rows),
            "reddit_profiles": len(reddit_profiles),
            "agent_configs": len(config.get("agent_configs", [])),
        }
    over_capacity = {
        name: count
        for name, count in profile_counts.items()
        if count > PREPARED_PROFILE_MAX
    }
    add_check(
        "profile_capacity",
        not over_capacity,
        (
            {
                "maximum": PREPARED_PROFILE_MAX,
                "counts": profile_counts,
                "over_capacity": over_capacity,
            }
            if over_capacity
            else {"maximum": PREPARED_PROFILE_MAX, "counts": profile_counts}
        ),
    )

    poster_errors = []
    valid_agent_ids = {
        item.get("agent_id")
        for item in config.get("agent_configs", [])
        if admission is not None and isinstance(item, dict)
    }
    if admission is None:
        valid_agent_ids = set(range(len(canonical_agents)))
    for index, post in enumerate(config.get("bootstrap_posts", [])):
        if post.get("poster_agent_id") not in valid_agent_ids:
            poster_errors.append(
                f"bootstrap_posts[{index}] has invalid poster_agent_id"
            )
    add_check(
        "poster_assignment",
        not poster_errors,
        poster_errors or {"count": len(config.get("bootstrap_posts", []))},
    )

    prefer_boost_for_actor = bool(os.environ.get("LLM_BOOST_API_KEY"))
    model_matrix = write_model_resolution(
        simulation_dir,
        prefer_boost_for_actor=prefer_boost_for_actor,
    )
    model_errors = []
    for role in ("actor", "interview", "curator", "report"):
        model_errors.extend(
            validate_required_model_env(
                role,
                prefer_boost=prefer_boost_for_actor and role == "actor",
            )
        )
    add_check(
        "model_adapter_resolution", not model_errors, model_errors or model_matrix
    )

    env_errors = Config.validate()
    add_check("required_env", not env_errors, env_errors or {"validated": True})

    import_errors = validate_camel_runtime_imports()
    add_check("oasis_imports", not import_errors, import_errors or {"validated": True})

    failed_checks = [check["name"] for check in checks if check["status"] != "passed"]
    payload = {
        "status": "passed" if not failed_checks else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "failed_checks": failed_checks,
    }
    if admission is not None:
        payload["admission"] = admission
    _atomic_write_json(preflight_path(simulation_dir), payload)
    _write_run_manifest(
        simulation_dir,
        config,
        model_matrix,
        payload,
        admission,
    )
    return payload
