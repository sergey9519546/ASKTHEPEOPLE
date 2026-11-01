"""Preparation and preflight must not erase each other's provenance."""

from app.services import simulation_preflight as preflight_module
from app.services.simulation_artifacts import (
    read_json,
    run_manifest_path,
    write_run_manifest,
)


def test_preflight_preserves_prompt_call_records(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight_module, "resolve_deployed_revision", lambda: "fixture-revision")
    records = [{"prompt_id": "fixture", "prompt_sha256": "a" * 64}]
    write_run_manifest(str(tmp_path), records)

    payload = preflight_module._write_run_manifest(
        str(tmp_path),
        {"simulation_id": "sim_fixture"},
        {"actor": {"model": "fixture-model"}},
        {"status": "failed"},
        None,
    )

    assert payload["prompt_calls"] == records
    assert payload["prompt_call_count"] == len(records)
    assert payload["preflight_status"] == "failed"
    assert payload["code_revision"] == "fixture-revision"
    assert payload["reproducibility"]["deterministic"] is False
    assert read_json(run_manifest_path(str(tmp_path))) == payload


def test_prompt_writer_preserves_preflight_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight_module, "resolve_deployed_revision", lambda: "fixture-revision")
    initial = preflight_module._write_run_manifest(
        str(tmp_path),
        {"simulation_id": "sim_fixture"},
        {"actor": {"model": "fixture-model"}},
        {"status": "failed"},
        None,
    )
    records = [{"prompt_id": "fixture", "output_sha256": "b" * 64}]

    assert write_run_manifest(str(tmp_path), records)["written"] is True
    updated = read_json(run_manifest_path(str(tmp_path)))

    for key, value in initial.items():
        assert updated[key] == value
    assert updated["prompt_calls"] == records
    assert updated["prompt_call_count"] == 1


def test_prompt_writer_replaces_its_previous_records_without_duplicates(tmp_path):
    previous = [{"prompt_id": "previous"}]
    current = [{"prompt_id": "current"}]
    write_run_manifest(str(tmp_path), previous)
    write_run_manifest(str(tmp_path), current)
    written = read_json(run_manifest_path(str(tmp_path)))

    assert written["prompt_calls"] == current
    assert written["prompt_call_count"] == 1
