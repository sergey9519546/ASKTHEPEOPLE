"""Celery ownership for the protected Zep deployment canary."""

from __future__ import annotations

from typing import Any

from ..celery_app import celery_app
from ..services.zep_live_canary import run_protected_zep_canary


@celery_app.task(
    name="tasks.run_zep_live_canary",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_zep_live_canary_task(self, evidence: dict[str, Any]):
    """Execute only inside the deployed worker; the task accepts no provider input."""
    return run_protected_zep_canary(
        evidence=evidence,
        execute=True,
        run_id=str(self.request.id or ""),
    )
