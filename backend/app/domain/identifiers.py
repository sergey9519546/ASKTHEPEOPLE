"""Server-issued physical identifiers and public aliases."""

from __future__ import annotations

import math
import re
import secrets
import time
from collections.abc import Callable
from typing import Literal
from uuid import RFC_4122, UUID

_MAX_UUID7_UNIX_MILLISECONDS = (1 << 48) - 1
_UUID7_RANDOM_BITS = 74

PublicIdKind = Literal["org", "user", "workspace", "project"]

_PUBLIC_ID_PREFIXES = {
    "org": "org",
    "user": "user",
    "workspace": "workspace",
    "project": "proj",
}
_LEGACY_PROJECT_PUBLIC_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")


def new_uuid7(
    *,
    clock: Callable[[], float] | None = None,
    randbits: Callable[[int], int] | None = None,
) -> UUID:
    """Return an RFC 9562 UUIDv7 using injectable trusted entropy seams.

    ``clock`` follows ``time.time`` and returns Unix epoch seconds. ``randbits``
    follows ``secrets.randbits``. The seams keep boundary and layout tests
    deterministic without weakening production defaults.
    """

    clock_value = (clock or time.time)()
    if type(clock_value) not in (int, float) or not math.isfinite(clock_value):
        raise ValueError("uuid7_clock_out_of_range")
    unix_milliseconds = math.floor(clock_value * 1000)
    if not 0 <= unix_milliseconds <= _MAX_UUID7_UNIX_MILLISECONDS:
        raise ValueError("uuid7_clock_out_of_range")

    random_value = (randbits or secrets.randbits)(_UUID7_RANDOM_BITS)
    if type(random_value) is not int or not 0 <= random_value < (1 << 74):
        raise ValueError("uuid7_random_bits_out_of_range")

    random_a = random_value >> 62
    random_b = random_value & ((1 << 62) - 1)
    uuid_int = (
        (unix_milliseconds << 80)
        | (0b0111 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return UUID(int=uuid_int)


def new_public_id(
    kind: PublicIdKind,
    physical_id: UUID,
    *,
    uuid7_factory: Callable[[], UUID] | None = None,
) -> str:
    """Issue a public alias backed by a UUIDv7 independent of the physical ID."""

    if kind not in _PUBLIC_ID_PREFIXES:
        raise ValueError("unsupported_public_id_kind")
    if type(physical_id) is not UUID:
        raise TypeError("physical_id_must_be_uuid")
    if physical_id.version != 7 or physical_id.variant != RFC_4122:
        raise ValueError("physical_id_must_be_uuid7")

    alias_id = (uuid7_factory or new_uuid7)()
    if (
        type(alias_id) is not UUID
        or alias_id.version != 7
        or alias_id.variant != RFC_4122
    ):
        raise ValueError("public_alias_must_use_uuid7")
    if alias_id == physical_id:
        raise ValueError("public_alias_must_not_reveal_physical_id")
    return f"{_PUBLIC_ID_PREFIXES[kind]}_{alias_id.hex}"


def validate_legacy_project_public_id(value: str) -> str:
    """Validate and preserve an accepted legacy project public alias exactly."""

    if (
        type(value) is not str
        or _LEGACY_PROJECT_PUBLIC_ID_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("invalid_legacy_project_public_id")
    return value
