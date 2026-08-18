#!/usr/bin/env python3
"""Guard: vercel.json must never reference the legacy deploy blocker."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BLOCKED_REF = "block_legacy_railway_deploy"
VERCEL_PATHS = [Path("vercel.json"), Path("frontend/vercel.json")]


def main() -> int:
    errors = []
    for p in VERCEL_PATHS:
        if not p.exists():
            continue
        content = json.loads(p.read_text(encoding="utf-8"))
        cmd = content.get("buildCommand", "")
        if isinstance(cmd, str) and BLOCKED_REF in cmd:
            errors.append(f"{p}: buildCommand references blocked script: {cmd}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
