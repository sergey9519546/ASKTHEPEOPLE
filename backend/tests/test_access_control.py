import pytest

from app.services.access_control import (
    AccessTicketError,
    issue_ws_ticket,
    verify_ws_ticket,
)


def test_ws_ticket_is_bound_to_scope_resource_and_expiry():
    ticket, expires_at = issue_ws_ticket(
        "test-secret",
        "simulation",
        "sim_123",
        now=1_000,
    )

    assert expires_at == 1_060
    verify_ws_ticket(ticket, "test-secret", "simulation", "sim_123", now=1_059)

    with pytest.raises(AccessTicketError, match="scope"):
        verify_ws_ticket(ticket, "test-secret", "report", "sim_123", now=1_059)
    with pytest.raises(AccessTicketError, match="scope"):
        verify_ws_ticket(ticket, "test-secret", "simulation", "sim_456", now=1_059)
    with pytest.raises(AccessTicketError, match="expired"):
        verify_ws_ticket(ticket, "test-secret", "simulation", "sim_123", now=1_061)


def test_ws_ticket_rejects_tampering_and_bad_resource_ids():
    ticket, _ = issue_ws_ticket("test-secret", "report", "report_123", now=2_000)

    with pytest.raises(AccessTicketError, match="invalid_ticket"):
        verify_ws_ticket(
            ticket + "x",
            "test-secret",
            "report",
            "report_123",
            now=2_001,
        )
    with pytest.raises(AccessTicketError, match="invalid_resource_id"):
        issue_ws_ticket("test-secret", "report", "../report", now=2_000)


def test_ws_ticket_is_single_use_and_expires_at_exact_deadline():
    ticket, _ = issue_ws_ticket(
        "test-secret",
        "simulation",
        "sim_single_use",
        now=3_000,
    )
    verify_ws_ticket(
        ticket,
        "test-secret",
        "simulation",
        "sim_single_use",
        now=3_001,
    )
    with pytest.raises(AccessTicketError, match="ticket_replayed"):
        verify_ws_ticket(
            ticket,
            "test-secret",
            "simulation",
            "sim_single_use",
            now=3_002,
        )

    expiring_ticket, _ = issue_ws_ticket(
        "test-secret",
        "report",
        "report_exact_expiry",
        now=4_000,
    )
    with pytest.raises(AccessTicketError, match="expired_ticket"):
        verify_ws_ticket(
            expiring_ticket,
            "test-secret",
            "report",
            "report_exact_expiry",
            now=4_060,
        )
