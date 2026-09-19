"""Lease coordination: heartbeat, deadline, takeover and audit.

The property under test: one actor holds a ticket's execution lease at a time,
only that actor may renew it, and a different actor may take it over only after
``deadline + grace`` — never by racing the original holder. The append-only
audit survives a restart and ties every transition to its actor and deadline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from koru.queue.lease import (
    ACTION_RENEW,
    ACTION_TAKEOVER,
    TAKEOVER_GRACE_SECONDS,
    can_claim,
    can_release,
    can_renew,
    can_takeover,
    current_generation,
    lease_deadline,
    lease_snapshot,
    parse_lease_datetime,
    projected_deadline,
    read_lease_audit,
    record_lease_event,
    takeover_at,
)

_NOW = datetime(2026, 9, 14, 12, 0, 0, tzinfo=UTC)


def _ticket(*, assigned_to=None, lease_expires_at=None, takeover=None) -> dict:
    execution: dict = {}
    if assigned_to is not None:
        execution["assigned_to"] = assigned_to
    if lease_expires_at is not None:
        execution["lease_expires_at"] = lease_expires_at.isoformat()
    if takeover is not None:
        execution["takeover_at"] = takeover.isoformat()
    return {"id": "PLF-1", "execution": execution}


def test_deadline_and_takeover_boundary_use_fixed_grace() -> None:
    deadline = _NOW + timedelta(hours=1)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    assert lease_deadline(ticket) == deadline
    assert takeover_at(ticket) == deadline + timedelta(seconds=TAKEOVER_GRACE_SECONDS)


def test_explicit_takeover_at_wins_over_grace() -> None:
    deadline = _NOW + timedelta(hours=1)
    explicit = _NOW + timedelta(hours=2)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline, takeover=explicit)

    assert takeover_at(ticket) == explicit


def test_parse_lease_datetime_handles_z_and_naive_values() -> None:
    assert parse_lease_datetime("2026-09-14T12:00:00Z") == _NOW
    assert parse_lease_datetime("2026-09-14T12:00:00+00:00") == _NOW
    assert parse_lease_datetime("2026-09-14T12:00:00") == _NOW
    assert parse_lease_datetime("nope") is None
    assert parse_lease_datetime(None) is None


def test_timeout_transitions_from_active_to_takeover_eligible() -> None:
    deadline = _NOW + timedelta(seconds=60)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    before = lease_snapshot(ticket, now=_NOW)
    assert before.active and not before.takeover_eligible

    after_deadline = lease_snapshot(ticket, now=_NOW + timedelta(seconds=61))
    assert not after_deadline.active and not after_deadline.takeover_eligible

    after_grace = lease_snapshot(
        ticket, now=_NOW + timedelta(seconds=61 + TAKEOVER_GRACE_SECONDS),
    )
    assert not after_grace.active and after_grace.takeover_eligible


def test_one_active_lease_refuses_a_second_actor() -> None:
    deadline = _NOW + timedelta(hours=1)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    decision = can_claim(ticket, "actor-b", now=_NOW)

    assert not decision.ok
    assert "held by actor-a" in decision.reason


def test_claim_within_grace_is_still_refused() -> None:
    deadline = _NOW - timedelta(seconds=1)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    decision = can_claim(ticket, "actor-b", now=_NOW)

    assert not decision.ok
    assert "grace" in decision.reason


def test_takeover_allowed_after_grace() -> None:
    deadline = _NOW - timedelta(seconds=TAKEOVER_GRACE_SECONDS + 1)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    claim = can_claim(ticket, "actor-b", now=_NOW)
    takeover = can_takeover(ticket, "actor-b", now=_NOW)

    assert claim.ok and claim.action == ACTION_TAKEOVER
    assert takeover.ok and takeover.action == ACTION_TAKEOVER


def test_takeover_preserves_history_and_scope() -> None:
    deadline = _NOW - timedelta(seconds=TAKEOVER_GRACE_SECONDS + 1)
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=deadline)

    can_takeover(ticket, "actor-b", now=_NOW)

    assert ticket["execution"]["assigned_to"] == "actor-a"
    assert lease_deadline(ticket) == deadline


def test_renew_is_owner_only() -> None:
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=_NOW + timedelta(hours=1))

    assert can_renew(ticket, "actor-a", now=_NOW).ok
    denied = can_renew(ticket, "actor-b", now=_NOW)
    assert not denied.ok
    assert "held by actor-a" in denied.reason


def test_renew_extends_the_deadline() -> None:
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=_NOW + timedelta(seconds=60))

    decision = can_claim(ticket, "actor-a", now=_NOW)
    new_deadline = projected_deadline(3600, now=_NOW)

    assert decision.ok and decision.action == ACTION_RENEW
    assert new_deadline > lease_deadline(ticket)


def test_no_lease_cannot_be_renewed() -> None:
    assert not can_renew(_ticket(), "actor-a", now=_NOW).ok


def test_release_is_owner_only() -> None:
    ticket = _ticket(assigned_to="actor-a", lease_expires_at=_NOW + timedelta(hours=1))

    assert can_release(ticket, "actor-a", now=_NOW).ok
    assert not can_release(ticket, "actor-b", now=_NOW).ok


def test_audit_records_actor_and_lease(tmp_path) -> None:
    deadline = projected_deadline(3600, now=_NOW)
    record_lease_event(
        tmp_path, "PLF-1", action="claim", actor="actor-a",
        deadline=deadline, takeover_boundary=deadline + timedelta(seconds=TAKEOVER_GRACE_SECONDS),
        now=_NOW,
    )

    records = read_lease_audit(tmp_path, "PLF-1")

    assert len(records) == 1
    assert records[0]["actor"] == "actor-a"
    assert records[0]["action"] == "claim"
    assert records[0]["generation"] == 1
    assert records[0]["lease_expires_at"] == deadline.isoformat().replace("+00:00", "Z")


def test_restart_preserves_audit_and_keeps_generation_monotonic(tmp_path) -> None:
    record_lease_event(tmp_path, "PLF-1", action="claim", actor="actor-a", now=_NOW)
    record_lease_event(tmp_path, "PLF-1", action="release", actor="actor-a", now=_NOW)

    # Simulate a restart: read the audit again through a fresh call stack.
    records = read_lease_audit(tmp_path, "PLF-1")
    assert [r["action"] for r in records] == ["claim", "release"]
    assert [r["generation"] for r in records] == [1, 2]
    assert current_generation(tmp_path, "PLF-1") == 2


def test_takeover_after_restart_refuses_a_stale_owner_renew(tmp_path) -> None:
    record_lease_event(tmp_path, "PLF-1", action="claim", actor="actor-a", now=_NOW)
    record_lease_event(tmp_path, "PLF-1", action="takeover", actor="actor-b", now=_NOW)

    # After takeover the lease owner is actor-b; actor-a is stale.
    ticket = _ticket(assigned_to="actor-b", lease_expires_at=_NOW + timedelta(hours=1))
    assert can_renew(ticket, "actor-b", now=_NOW).ok
    assert not can_renew(ticket, "actor-a", now=_NOW).ok
