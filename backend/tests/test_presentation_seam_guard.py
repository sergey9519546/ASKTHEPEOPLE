"""Repository lock: the API route layer must answer through the seam.

Style follows ``test_secret_scan_policy.py``: a repo-level lock that reads the
tracked tree and fails when the forbidden pattern reappears.

C2 seam follow-up (issue #170): every response under the simulation API must
be shaped by ``app/api/presentation.py`` (``present`` / ``error_response`` /
``present_raw``). Hand-rolled ``jsonify({"success": False, ...})`` envelopes
in route modules bypass the seam, so this guard counts them across
``backend/app/api/routes/`` and ``backend/app/api/simulation.py``.

The allowlist maps a guarded file (posix path relative to ``backend/``) to the
number of hand-rolled error-envelope occurrences it may contain. It is
currently EMPTY because every known site has been migrated. Only ever shrink
it; a new occurrence in an unlisted file, or a count above the allowlisted
number, fails the suite.
"""

from __future__ import annotations

import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
API_DIR = BACKEND_ROOT / "app" / "api"
GUARDED_FILES: tuple[Path, ...] = (
    *sorted((API_DIR / "routes").glob("*.py")),
    API_DIR / "simulation.py",
)

# file (posix, relative to backend/) -> allowed occurrences of the
# hand-rolled error-envelope pattern. Empty by design; do not grow it.
ERROR_ENVELOPE_ALLOWLIST: dict[str, int] = {}

# Whitespace-flexible so multi-line call sites are counted too, not just
# single-line literals.
_ERROR_ENVELOPE = re.compile(r'jsonify\(\s*\{\s*"success":\s*False')


def _guarded() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in GUARDED_FILES:
        if not path.is_file():
            continue
        relative = path.relative_to(BACKEND_ROOT).as_posix()
        counts[relative] = len(_ERROR_ENVELOPE.findall(path.read_text(encoding="utf-8")))
    return counts


def test_guard_pattern_actually_matches_the_forbidden_shape() -> None:
    """The lock must fire on the real thing, not a stale regex."""
    sample = (
        'return jsonify({"success": False, "error": "boom"}), 500\n'
        'resp = jsonify({\n    "success": False,\n    "code": "x",\n})\n'
    )
    assert len(_ERROR_ENVELOPE.findall(sample)) == 2


def test_seam_helpers_are_not_bypassed_by_error_envelopes_in_routes() -> None:
    counts = _guarded()

    for relative in ERROR_ENVELOPE_ALLOWLIST:
        assert relative in counts, (
            f"allowlist entry {relative!r} is not a guarded file; remove it"
        )

    offenders = {
        relative: actual
        for relative, actual in counts.items()
        if actual > ERROR_ENVELOPE_ALLOWLIST.get(relative, 0)
    }

    assert offenders == {}, (
        "Hand-rolled error envelopes found outside the presentation seam; "
        "use app.api.presentation.error_response (or present_raw for "
        "caller-owned payloads) and shrink ERROR_ENVELOPE_ALLOWLIST only "
        f"with justification: {offenders}"
    )


def test_allowlisted_counts_do_not_exceed_their_budget() -> None:
    """Even an allowlisted site must never gain occurrences."""
    for relative, allowed in ERROR_ENVELOPE_ALLOWLIST.items():
        actual = _guarded().get(relative)
        assert actual is not None, f"allowlist entry {relative!r} is not guarded"
        assert actual <= allowed, (
            f"{relative} now has {actual} hand-rolled error envelopes "
            f"(allowed: {allowed}); migrate to the seam instead of growing this"
        )


def test_guarded_surface_covers_the_route_layer() -> None:
    """The lock must keep watching the whole route layer."""
    relatives = {path.relative_to(BACKEND_ROOT).as_posix() for path in GUARDED_FILES}
    assert "app/api/simulation.py" in relatives
    assert "app/api/routes/execution_routes.py" in relatives
    assert "app/api/routes/interview_routes.py" in relatives
    assert "app/api/routes/read_routes.py" in relatives
