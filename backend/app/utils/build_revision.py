"""Resolve deployed code identity from an image-owned immutable revision."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path


IMAGE_BUILD_REVISION_PATH = Path("/usr/share/askthepeople/build-revision")
_IMMUTABLE_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_MAX_REVISION_FILE_BYTES = 66


def _normalize(candidate: object) -> str:
    value = str(candidate or "").strip()
    return value.lower() if _IMMUTABLE_REVISION.fullmatch(value) else ""


def _read_image_revision(path: Path) -> tuple[bool, str]:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return False, ""
    except OSError:
        return True, ""
    if not payload or len(payload) > _MAX_REVISION_FILE_BYTES:
        return True, ""
    try:
        candidate = payload.decode("ascii").strip()
    except UnicodeDecodeError:
        return True, ""
    return True, _normalize(candidate)


def resolve_deployed_revision(
    environment: Mapping[str, object] | None = None,
    *,
    image_revision_path: Path = IMAGE_BUILD_REVISION_PATH,
) -> str:
    """Return one verified revision, or empty when any identity conflicts.

    Container images own the revision file. Platform/runtime revision variables
    may corroborate that value, but they can never replace it. The environment
    fallback exists only for local/test execution where no image file exists.
    """
    env = os.environ if environment is None else environment
    supplied: list[str] = []
    for name in ("RAILWAY_GIT_COMMIT_SHA", "BUILD_REVISION"):
        raw = str(env.get(name) or "").strip()
        if not raw:
            continue
        normalized = _normalize(raw)
        if not normalized:
            return ""
        supplied.append(normalized)

    if len(set(supplied)) > 1:
        return ""

    image_exists, image_revision = _read_image_revision(image_revision_path)
    if image_exists:
        if not image_revision:
            return ""
        if supplied and supplied[0] != image_revision:
            return ""
        return image_revision

    return supplied[0] if supplied else ""

