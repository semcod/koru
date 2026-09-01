from __future__ import annotations

from datetime import UTC, datetime

from koru.queue.living_status import (
    LIVING_STATUS_START,
    lease_expiry_text,
    living_status_block,
    upsert_living_status,
)


def test_two_hour_expiry_is_normalized_utc() -> None:
    now = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    assert lease_expiry_text(lease_seconds=7200, now=now) == "2026-09-01T12:00:00Z"


def test_living_status_is_single_and_preserves_source_description() -> None:
    ticket = {
        "id": "PLF-41",
        "description": "Original evidence",
        "sync": {"onedev": {"url": "https://control.example/issues/41"}},
    }
    first = living_status_block(
        ticket,
        state="in_progress",
        actor="koru-a",
        lease_expires_at="2026-09-01T12:00:00Z",
    )
    second = living_status_block(
        ticket,
        state="waiting_human_triage",
        actor="koru",
        lease_expires_at=None,
        urgent=True,
    )

    updated = upsert_living_status("Original evidence", first)
    replaced = upsert_living_status(updated, second)

    assert replaced.startswith("Original evidence")
    assert replaced.count(LIVING_STATUS_START) == 1
    assert "in_progress" not in replaced
    assert "waiting_human_triage" in replaced
    assert "sla:urgent" in replaced
    assert "https://control.example/issues/41" in replaced
