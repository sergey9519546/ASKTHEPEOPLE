"""No-network startup preflight for the graph/report Celery worker."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.worker_startup import (  # noqa: E402
    WorkerStartupConfigurationError,
    validate_worker_configuration,
    validate_worker_zep_configuration,  # noqa: F401 - compatibility export
)


def main(
    environ: Mapping[str, str] | None = None,
    *,
    stderr: TextIO | None = None,
) -> int:
    environment = os.environ if environ is None else environ
    error_stream = sys.stderr if stderr is None else stderr
    try:
        validate_worker_configuration(environment)
    except WorkerStartupConfigurationError as exc:
        print(f"fatal: {exc}", file=error_stream)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
