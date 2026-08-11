"""Immutable image-revision identity locks for every deployed process."""

from __future__ import annotations

from pathlib import Path


REVISION = "a" * 40
OTHER_REVISION = "b" * 40


def _write_revision(path: Path, revision: str = REVISION) -> None:
    path.write_text(f"{revision}\n", encoding="ascii")


def test_image_revision_is_authoritative_when_runtime_values_match(tmp_path):
    from app.utils.build_revision import resolve_deployed_revision

    revision_path = tmp_path / "build-revision"
    _write_revision(revision_path)

    assert (
        resolve_deployed_revision(
            {
                "BUILD_REVISION": REVISION,
                "RAILWAY_GIT_COMMIT_SHA": REVISION.upper(),
            },
            image_revision_path=revision_path,
        )
        == REVISION
    )


def test_runtime_revision_cannot_override_the_image_identity(tmp_path):
    from app.utils.build_revision import resolve_deployed_revision

    revision_path = tmp_path / "build-revision"
    _write_revision(revision_path)

    assert (
        resolve_deployed_revision(
            {"BUILD_REVISION": OTHER_REVISION},
            image_revision_path=revision_path,
        )
        == ""
    )
    assert (
        resolve_deployed_revision(
            {"RAILWAY_GIT_COMMIT_SHA": OTHER_REVISION},
            image_revision_path=revision_path,
        )
        == ""
    )


def test_malformed_image_identity_fails_closed_even_with_valid_runtime_value(tmp_path):
    from app.utils.build_revision import resolve_deployed_revision

    revision_path = tmp_path / "build-revision"
    _write_revision(revision_path, "main")

    assert (
        resolve_deployed_revision(
            {"BUILD_REVISION": REVISION},
            image_revision_path=revision_path,
        )
        == ""
    )


def test_local_non_image_execution_accepts_one_consistent_exact_revision(tmp_path):
    from app.utils.build_revision import resolve_deployed_revision

    absent_path = tmp_path / "absent-build-revision"
    assert (
        resolve_deployed_revision(
            {"BUILD_REVISION": REVISION},
            image_revision_path=absent_path,
        )
        == REVISION
    )
    assert (
        resolve_deployed_revision(
            {
                "BUILD_REVISION": REVISION,
                "RAILWAY_GIT_COMMIT_SHA": OTHER_REVISION,
            },
            image_revision_path=absent_path,
        )
        == ""
    )

