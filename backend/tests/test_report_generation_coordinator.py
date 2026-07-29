import pytest

from app.services.report_generation_coordinator import (
    ReportGenerationCancelled,
    ReportGenerationCoordinator,
)


def test_report_generation_lease_excludes_duplicates_and_fences_writes():
    coordinator = ReportGenerationCoordinator()
    lease, active = coordinator.acquire("sim_1", "report_1")
    assert active is None
    assert lease is not None

    duplicate, active = coordinator.acquire("sim_1", "report_2")
    assert duplicate is None
    assert active is lease

    writes = []
    with lease.write_guard():
        writes.append("before_cancel")

    lease.cancel()
    with pytest.raises(ReportGenerationCancelled):
        with lease.write_guard():
            writes.append("stale_worker_write")

    with lease.write_guard(allow_cancelled=True):
        writes.append("authoritative_terminal_write")

    assert writes == ["before_cancel", "authoritative_terminal_write"]

    coordinator.release(lease)
    replacement, active = coordinator.acquire("sim_1", "report_2")
    assert active is None
    assert replacement is not None
