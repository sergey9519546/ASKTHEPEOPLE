"""Celery and CLI guards for the protected Zep live canary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


RUN_ID = "11111111-1111-4111-8111-111111111111"


def valid_evidence(**changes):
    evidence = {
        "schema_version": "zep-rotation-evidence/v1",
        "incident_id": "public-historical-provider-credentials-2026-07-29",
        "provider": "zep-cloud",
        "old_credentials_revoked": True,
        "old_credentials_revoked_at": "2026-08-08T08:00:00Z",
        "replacement_issued": True,
        "replacement_issued_at": "2026-08-08T08:05:00Z",
        "web_updated": True,
        "web_updated_at": "2026-08-08T08:10:00Z",
        "worker_updated": True,
        "worker_updated_at": "2026-08-08T08:11:00Z",
        "web_restarted": True,
        "web_restarted_at": "2026-08-08T08:12:00Z",
        "worker_restarted": True,
        "worker_restarted_at": "2026-08-08T08:13:00Z",
        "provider_usage_reviewed_through": "2026-08-08T08:14:00Z",
        "rotated_by": "release-operator",
        "independently_verified_by": "security-reviewer",
        "verified_at": "2026-08-08T08:15:00Z",
        "deployment_revision": "a" * 40,
        "restricted_evidence_ref": "incident://security/2026-07-29/rotation",
    }
    evidence.update(changes)
    return evidence


def _load_cli_module():
    script = Path(__file__).parents[1] / "scripts" / "zep_live_canary.py"
    if not script.exists():
        pytest.fail("protected canary CLI is not implemented", pytrace=False)
    spec = importlib.util.spec_from_file_location("zep_live_canary_cli", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_celery_task_is_worker_owned_late_acked_and_accepts_no_provider_input():
    from app.tasks.zep_canary_tasks import run_zep_live_canary_task

    assert run_zep_live_canary_task.name == "tasks.run_zep_live_canary"
    assert run_zep_live_canary_task.acks_late is True
    assert run_zep_live_canary_task.reject_on_worker_lost is True
    assert "api_key" not in run_zep_live_canary_task.run.__code__.co_varnames
    assert "fixture" not in run_zep_live_canary_task.run.__code__.co_varnames
    assert "graph_id" not in run_zep_live_canary_task.run.__code__.co_varnames


def test_task_delegates_to_protected_service_and_returns_only_sanitized_result(
    monkeypatch,
):
    from app.tasks import zep_canary_tasks

    expected = {
        "exit_code": 0,
        "state": "CLEAN",
        "reason": "canary_passed",
        "graph_id": "atp_canary_v1_20260808t120000z_aaaaaaaaaaaaaaaaaaaaaaaa",
    }
    calls = []
    monkeypatch.setattr(
        zep_canary_tasks,
        "run_protected_zep_canary",
        lambda **kwargs: calls.append(kwargs) or expected,
    )

    task = zep_canary_tasks.run_zep_live_canary_task
    task.push_request(id=RUN_ID)
    try:
        result = task.run(evidence=valid_evidence())
    finally:
        task.pop_request()

    assert result == expected
    assert calls == [{"evidence": valid_evidence(), "execute": True, "run_id": RUN_ID}]


def test_cli_has_no_api_key_option_and_defaults_to_non_dispatching_dry_run(tmp_path):
    cli = _load_cli_module()
    parser = cli.build_parser()
    option_strings = {
        option for action in parser._actions for option in action.option_strings
    }
    assert "--api-key" not in option_strings
    assert "--execute" in option_strings

    evidence_path = tmp_path / "rotation.json"
    evidence_path.write_text(cli.json.dumps(valid_evidence()), encoding="utf-8")
    dispatches = []

    exit_code = cli.main(
        ["--evidence-file", str(evidence_path)],
        dispatch=lambda **kwargs: dispatches.append(kwargs),
    )

    assert exit_code == 5
    assert dispatches == []


def test_cli_execute_dispatches_only_closed_evidence_and_uses_task_exit_code(tmp_path):
    cli = _load_cli_module()
    evidence = valid_evidence()
    evidence_path = tmp_path / "rotation.json"
    evidence_path.write_text(cli.json.dumps(evidence), encoding="utf-8")
    dispatches = []

    def dispatch(**kwargs):
        dispatches.append(kwargs)
        return {
            "exit_code": 3,
            "state": "CLEANUP_PENDING",
            "reason": "cleanup_not_confirmed",
            "graph_id": "atp_canary_v1_20260808t120000z_aaaaaaaaaaaaaaaaaaaaaaaa",
        }

    exit_code = cli.main(
        ["--evidence-file", str(evidence_path), "--execute"],
        dispatch=dispatch,
    )

    assert exit_code == 3
    assert dispatches == [{"evidence": evidence}]


def test_cli_rejects_unknown_evidence_without_dispatch(tmp_path):
    cli = _load_cli_module()
    evidence = valid_evidence(unexpected_secret="must-not-pass")
    evidence_path = tmp_path / "rotation.json"
    evidence_path.write_text(cli.json.dumps(evidence), encoding="utf-8")
    dispatches = []

    exit_code = cli.main(
        ["--evidence-file", str(evidence_path), "--execute"],
        dispatch=lambda **kwargs: dispatches.append(kwargs),
    )

    assert exit_code == 4
    assert dispatches == []


def test_cli_rejects_a_malformed_task_result_instead_of_printing_it(tmp_path, capsys):
    cli = _load_cli_module()
    evidence_path = tmp_path / "rotation.json"
    evidence_path.write_text(cli.json.dumps(valid_evidence()), encoding="utf-8")

    exit_code = cli.main(
        ["--evidence-file", str(evidence_path), "--execute"],
        dispatch=lambda **_kwargs: {
            "exit_code": 0,
            "state": "CLEAN",
            "reason": "canary_passed",
            "graph_id": "raw-provider-body-must-not-print",
        },
    )

    assert exit_code == 5
    assert "raw-provider-body" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "payload",
    [
        {
            "exit_code": 2,
            "state": "CLEAN",
            "reason": "canary_passed",
            "graph_id": "atp_canary_v1_20260808t120000z_aaaaaaaaaaaaaaaaaaaaaaaa",
        },
        {
            "exit_code": 3,
            "state": "CLEANUP_PENDING",
            "reason": "rotation_evidence_invalid",
            "graph_id": "atp_canary_v1_20260808t120000z_aaaaaaaaaaaaaaaaaaaaaaaa",
        },
        {
            "exit_code": 4,
            "state": "BLOCKED",
            "reason": "rotation_evidence_invalid",
            "graph_id": "atp_canary_v1_20260808t120000z_aaaaaaaaaaaaaaaaaaaaaaaa",
        },
        {
            "exit_code": 5,
            "state": "BLOCKED",
            "reason": "canary_passed",
        },
    ],
)
def test_cli_rejects_contradictory_closed_result_combinations(payload):
    cli = _load_cli_module()

    assert cli._task_result_is_safe(payload) is False
