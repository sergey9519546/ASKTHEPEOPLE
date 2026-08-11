"""Create and verify a bounded SHA-256 inventory for transition backups."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath

if __package__:
    from .prepare_transition_storage import verify_store
else:
    from prepare_transition_storage import verify_store


_MANIFEST_NAME = ".transition-manifest-v1.json"
_SCHEMA = "transition-storage-manifest/v1"
_MAX_MANIFEST_BYTES = 1024 * 1024


def _digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _inventory(root: Path) -> list[dict[str, object]]:
    resolved = root.resolve(strict=True)
    if not verify_store(resolved):
        raise ValueError("transition_storage_invalid")
    inventory: list[dict[str, object]] = []
    for path in sorted(resolved.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir() or path.name == _MANIFEST_NAME:
            continue
        if not path.is_file():
            raise ValueError("transition_storage_invalid")
        size, sha256 = _digest(path)
        inventory.append(
            {
                "path": path.relative_to(resolved).as_posix(),
                "size": size,
                "sha256": sha256,
            }
        )
    return inventory


def write_manifest(root: Path) -> Path:
    resolved = root.resolve(strict=True)
    payload = {
        "schema": _SCHEMA,
        "files": _inventory(resolved),
    }
    encoded = (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("ascii")
    if len(encoded) > _MAX_MANIFEST_BYTES:
        raise ValueError("transition_manifest_too_large")

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{_MANIFEST_NAME}.",
        dir=resolved,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        destination = resolved / _MANIFEST_NAME
        os.replace(temp_name, destination)
        return destination
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _valid_manifest_files(value: object) -> bool:
    if not isinstance(value, list):
        return False
    previous = ""
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            return False
        relative = item["path"]
        size = item["size"]
        sha256 = item["sha256"]
        if not isinstance(relative, str) or not relative or relative in seen:
            return False
        parsed = PurePosixPath(relative)
        if parsed.is_absolute() or ".." in parsed.parts or relative <= previous:
            return False
        if type(size) is not int or size < 0:
            return False
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            return False
        previous = relative
        seen.add(relative)
    return True


def verify_manifest(root: Path) -> bool:
    try:
        resolved = root.resolve(strict=True)
        manifest = resolved / _MANIFEST_NAME
        if (
            not manifest.is_file()
            or manifest.is_symlink()
            or manifest.stat().st_size > _MAX_MANIFEST_BYTES
        ):
            return False
        payload = json.loads(manifest.read_text(encoding="ascii"))
        if (
            not isinstance(payload, dict)
            or set(payload) != {"schema", "files"}
            or payload["schema"] != _SCHEMA
            or not _valid_manifest_files(payload["files"])
        ):
            return False
        return payload["files"] == _inventory(resolved)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    try:
        if args.write:
            write_manifest(root)
            message = "transition_manifest_written"
        elif verify_manifest(root):
            message = "transition_manifest_verified"
        else:
            raise ValueError("transition_manifest_invalid")
    except (OSError, UnicodeError, ValueError):
        print("transition_manifest_invalid", file=sys.stderr)
        return 78
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
