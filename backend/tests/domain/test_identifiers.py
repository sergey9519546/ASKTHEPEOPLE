from collections.abc import Iterator
from uuid import RFC_4122, UUID

import pytest


def test_uuid7_has_rfc9562_version_variant_and_time_window() -> None:
    from app.domain.identifiers import new_uuid7

    clock_values: Iterator[float] = iter(
        (1_700_000_000.123, 1_700_000_000.123, 1_700_000_000.124)
    )
    random_values: Iterator[int] = iter((0, 1, 0))
    requested_random_bits: list[int] = []

    def clock() -> float:
        return next(clock_values)

    def randbits(bit_count: int) -> int:
        requested_random_bits.append(bit_count)
        return next(random_values)

    first = new_uuid7(clock=clock, randbits=randbits)
    same_millisecond = new_uuid7(clock=clock, randbits=randbits)
    next_millisecond = new_uuid7(clock=clock, randbits=randbits)

    assert first.version == 7
    assert first.variant == RFC_4122
    assert first.int >> 80 == 1_700_000_000_123
    assert first != same_millisecond
    assert first < next_millisecond
    assert requested_random_bits == [74, 74, 74]

    with pytest.raises(ValueError, match="uuid7_clock_out_of_range"):
        new_uuid7(clock=lambda: -0.001, randbits=lambda _: 0)
    with pytest.raises(ValueError, match="uuid7_clock_out_of_range"):
        new_uuid7(clock=lambda: (1 << 48) / 1000, randbits=lambda _: 0)


def test_new_public_alias_uses_kind_and_independent_uuid7_hex() -> None:
    from app.domain.identifiers import new_public_id, new_uuid7

    physical_id = new_uuid7(clock=lambda: 1_700_000_000, randbits=lambda _: 0x123)
    alias_id = new_uuid7(clock=lambda: 1_700_000_001, randbits=lambda _: 0x456)

    assert (
        new_public_id("org", physical_id, uuid7_factory=lambda: alias_id)
        == f"org_{alias_id.hex}"
    )
    assert (
        new_public_id("user", physical_id, uuid7_factory=lambda: alias_id)
        == f"user_{alias_id.hex}"
    )
    assert (
        new_public_id("workspace", physical_id, uuid7_factory=lambda: alias_id)
        == f"workspace_{alias_id.hex}"
    )
    assert (
        new_public_id("project", physical_id, uuid7_factory=lambda: alias_id)
        == f"proj_{alias_id.hex}"
    )
    assert alias_id != physical_id

    with pytest.raises(ValueError, match="unsupported_public_id_kind"):
        new_public_id("decision", physical_id)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="physical_id_must_be_uuid"):
        new_public_id("org", str(physical_id))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="physical_id_must_be_uuid7"):
        new_public_id("org", UUID("12345678-1234-4234-8234-123456789abc"))
    with pytest.raises(ValueError, match="public_alias_must_use_uuid7"):
        new_public_id(
            "org",
            physical_id,
            uuid7_factory=lambda: UUID("12345678-1234-4234-8234-123456789abc"),
        )
    with pytest.raises(ValueError, match="public_alias_must_not_reveal_physical_id"):
        new_public_id("org", physical_id, uuid7_factory=lambda: physical_id)


def test_legacy_project_alias_is_preserved_but_invalid_alias_is_rejected() -> None:
    from app.domain.identifiers import validate_legacy_project_public_id

    accepted = (
        "proj_0123456789ab",
        "Legacy-PROJECT_01",
        "A",
        "a" * 128,
    )
    for alias in accepted:
        assert validate_legacy_project_public_id(alias) == alias

    rejected: tuple[object, ...] = (
        "",
        "a" * 129,
        "_project",
        "-project",
        "project with spaces",
        "project.dot",
        "project/path",
        "prøject",
        123,
    )
    for alias in rejected:
        with pytest.raises(ValueError, match="invalid_legacy_project_public_id"):
            validate_legacy_project_public_id(alias)  # type: ignore[arg-type]
