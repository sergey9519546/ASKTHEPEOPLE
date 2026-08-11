"""Fail closed while the legacy Railway topology is a release NO-GO."""

from __future__ import annotations

import sys


def main() -> int:
    """Return EX_CONFIG without inspecting configuration or credentials."""
    print("legacy_split_service_deployment_disabled", file=sys.stderr)
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
