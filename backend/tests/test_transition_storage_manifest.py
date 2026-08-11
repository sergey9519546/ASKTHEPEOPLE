"""Integrity manifest for the bounded single-host transition store."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.transition_storage_manifest import verify_manifest, write_manifest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "transition_storage_manifest.py"


def test_manifest_round_trip_detects_content_and_inventory_changes(tmp_path) -> None:
    store = tmp_path / "uploads"
    (store / "reports").mkdir(parents=True)
    (store / ".transition-store-v1").write_bytes(b"transition-storage/v1\n")
    artifact = store / "reports" / "report.json"
    artifact.write_text('{"ok":true}\n', encoding="utf-8")

    write_manifest(store)

    assert verify_manifest(store) is True

    artifact.write_text('{"ok":false}\n', encoding="utf-8")
    assert verify_manifest(store) is False

    artifact.write_text('{"ok":true}\n', encoding="utf-8")
    assert verify_manifest(store) is True

    (store / "unexpected.txt").write_text("extra", encoding="utf-8")
    assert verify_manifest(store) is False


def test_manifest_refuses_missing_or_oversized_manifest(tmp_path) -> None:
    store = tmp_path / "uploads"
    store.mkdir()

    assert verify_manifest(store) is False

    (store / ".transition-manifest-v1.json").write_bytes(b"x" * (1024 * 1024 + 1))
    assert verify_manifest(store) is False


def test_manifest_cli_runs_directly_from_repository_root(tmp_path) -> None:
    store = tmp_path / "uploads"
    store.mkdir()
    (store / ".transition-store-v1").write_bytes(b"transition-storage/v1\n")
    (store / "fixture.txt").write_text("fictional\n", encoding="utf-8")

    written = subprocess.run(
        [
            sys.executable,
            "-S",
            str(SCRIPT),
            "--root",
            str(store),
            "--write",
        ],
        cwd=SCRIPT.parents[2],
        capture_output=True,
        check=False,
        text=True,
    )

    assert written.returncode == 0
    assert written.stdout.strip() == "transition_manifest_written"
    assert written.stderr == ""
