"""Claim the dedicated single-host TRANSITION store without exposing old data."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path


_RELATIVE_STORE = Path(".transition-data") / "uploads"
_MARKER_NAME = ".transition-store-v1"
_MARKER_VALUE = "transition-storage/v1\n"


def _fail(code: str) -> int:
    print(code, file=sys.stderr)
    return 78


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        attributes = 0
    return (
        path.is_symlink()
        or bool(is_junction and is_junction())
        or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    )


def _tree_has_linklike(root: Path) -> bool:
    pending = [root]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                if _is_linklike(path):
                    return True
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
    return False


def verify_store(store: Path) -> bool:
    try:
        if _is_linklike(store):
            return False
        resolved_store = store.resolve(strict=True)
        marker = resolved_store / _MARKER_NAME
        return (
            resolved_store.is_dir()
            and marker.is_file()
            and not _is_linklike(marker)
            and marker.stat().st_size == len(_MARKER_VALUE.encode("ascii"))
            and marker.read_bytes() == _MARKER_VALUE.encode("ascii")
            and not _tree_has_linklike(resolved_store)
        )
    except OSError:
        return False


def prepare(repository: Path) -> int:
    try:
        root = repository.resolve(strict=True)
    except OSError:
        return _fail("transition_storage_invalid")
    if not root.is_dir():
        return _fail("transition_storage_invalid")

    transition_root = root / _RELATIVE_STORE.parent
    store = root / _RELATIVE_STORE
    if (transition_root.exists() and _is_linklike(transition_root)) or (
        store.exists() and _is_linklike(store)
    ):
        return _fail("transition_storage_invalid")
    try:
        store.mkdir(parents=True, exist_ok=True)
        resolved_store = store.resolve(strict=True)
    except OSError:
        return _fail("transition_storage_invalid")
    expected_store = Path(os.path.abspath(store))
    if (
        not resolved_store.is_dir()
        or not _is_within(resolved_store, root)
        or os.path.normcase(str(resolved_store))
        != os.path.normcase(str(expected_store))
    ):
        return _fail("transition_storage_invalid")

    marker = resolved_store / _MARKER_NAME
    if marker.exists():
        if not verify_store(resolved_store):
            return _fail("transition_storage_invalid")
        print("transition_storage_ready")
        return 0

    try:
        if any(resolved_store.iterdir()):
            return _fail("transition_storage_unowned")
        descriptor = os.open(
            marker,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            # The marker contains no secret. Containers chown the bind mount
            # to UID 10001, so it must remain host-readable on later preflights.
            0o644,
        )
        with os.fdopen(descriptor, "w", encoding="ascii", newline="") as handle:
            handle.write(_MARKER_VALUE)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return prepare(root)
    except OSError:
        return _fail("transition_storage_invalid")

    print("transition_storage_ready")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--repository", default=".")
    group.add_argument("--verify-store")
    args = parser.parse_args()
    if args.verify_store is not None:
        if not verify_store(Path(args.verify_store)):
            return _fail("transition_storage_invalid")
        print("transition_storage_verified")
        return 0
    return prepare(Path(args.repository))


if __name__ == "__main__":
    raise SystemExit(main())
