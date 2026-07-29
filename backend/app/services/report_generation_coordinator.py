"""Single-worker report-generation leases with cooperative cancellation."""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


class ReportGenerationCancelled(RuntimeError):
    """Raised when a report worker reaches a cancellation checkpoint."""


@dataclass
class ReportGenerationLease:
    simulation_id: str
    report_id: str
    token: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str | None = None
    state: str = "running"
    _cancel_event: threading.Event = field(
        default_factory=threading.Event,
        repr=False,
    )
    _write_lock: threading.RLock = field(
        default_factory=threading.RLock,
        repr=False,
    )

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def checkpoint(self) -> None:
        if self.cancelled:
            raise ReportGenerationCancelled("report_generation_cancelled")

    def cancel(self) -> None:
        # Taking the write gate first establishes a fencing point: after this
        # method returns, no new guarded worker write can begin.
        with self._write_lock:
            self._cancel_event.set()
            self.state = "cancelling"

    @contextmanager
    def write_guard(self, *, allow_cancelled: bool = False) -> Iterator[None]:
        with self._write_lock:
            if not allow_cancelled:
                self.checkpoint()
            yield

    def to_public_dict(self) -> dict[str, str | None]:
        return {
            "simulation_id": self.simulation_id,
            "report_id": self.report_id,
            "task_id": self.task_id,
            "state": self.state,
        }


class ReportGenerationCoordinator:
    """Own process-local leases for the documented one-worker topology."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._leases: dict[str, ReportGenerationLease] = {}

    def acquire(
        self,
        simulation_id: str,
        report_id: str,
    ) -> tuple[ReportGenerationLease | None, ReportGenerationLease | None]:
        with self._lock:
            active = self._leases.get(simulation_id)
            if active is not None:
                return None, active
            lease = ReportGenerationLease(
                simulation_id=simulation_id,
                report_id=report_id,
            )
            self._leases[simulation_id] = lease
            return lease, None

    def release(self, lease: ReportGenerationLease) -> None:
        with self._lock:
            active = self._leases.get(lease.simulation_id)
            if active is not None and active.token == lease.token:
                self._leases.pop(lease.simulation_id, None)

    def get(self, simulation_id: str) -> ReportGenerationLease | None:
        with self._lock:
            return self._leases.get(simulation_id)


report_generation_coordinator = ReportGenerationCoordinator()
