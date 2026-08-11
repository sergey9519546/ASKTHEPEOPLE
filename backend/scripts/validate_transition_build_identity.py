"""Fail closed unless a clean checkout is built as its exact HEAD revision."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_SUCCESS = "transition_build_identity_ok"
_FAILURE = "transition_build_identity_invalid"


def _read_build_revision(path: Path) -> str:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return ""
    assignments: list[str] = []
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if not candidate.startswith("BUILD_REVISION="):
            return ""
        assignments.append(candidate.removeprefix("BUILD_REVISION=").strip())
    if len(assignments) != 1 or not _REVISION.fullmatch(assignments[0]):
        return ""
    return assignments[0].lower()


def _git_output(repository: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def validate(build_env: Path, repository: Path) -> bool:
    """Require exact HEAD identity and no tracked, staged, or untracked dirt."""
    configured = _read_build_revision(build_env)
    raw_head = _git_output(repository, "rev-parse", "HEAD")
    head = raw_head.lower() if raw_head is not None else ""
    status = _git_output(
        repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    return bool(
        configured
        and head
        and configured == head
        and _REVISION.fullmatch(head)
        and status is not None
        and not status
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--build-env", type=Path, required=True)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    arguments = parser.parse_args(argv)
    if not validate(arguments.build_env, arguments.repository.resolve()):
        print(_FAILURE, file=sys.stderr)
        return 78
    print(_SUCCESS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
