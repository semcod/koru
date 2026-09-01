from __future__ import annotations

from copy import deepcopy

import pytest

from koru.poa.contracts import ContractError
from koru.poa.logs import (
    ZERO_HASH,
    LogContractError,
    append_planning_event,
    calculate_event_hash,
    validate_event,
    validate_event_chain,
)

INPUT_HASH = "a" * 64


def _append(events=(), *, event_type="koru.poa.binding_selected", occurred_at="2026-09-01T10:00:00Z"):
    return append_planning_event(
        events,
        stream="koru.poa.ticket-023",
        event_type=event_type,
        occurred_at=occurred_at,
        correlation_id="koru:ticket-023:run-1",
        producer="agent:koru",
        subject_ref="ticket:ticket-023",
        outcome="ACCEPTED",
        subject_state="bound",
        input_hash=INPUT_HASH,
        evidence=(
            {
                "path": "src/koru/data/poa-process-v1.schema.json",
                "sha256": "b" * 64,
            },
        ),
    )


def test_planning_events_are_closed_safe_and_hash_chained() -> None:
    events = _append()
    events = _append(events, event_type="koru.poa.plan_compiled", occurred_at="2026-09-01T10:00:01Z")
    validated = validate_event_chain(events, expected_stream="koru.poa.ticket-023")
    assert [event["sequence"] for event in validated] == [1, 2]
    assert validated[0]["previousHash"] == ZERO_HASH
    assert validated[0]["causationId"] is None
    assert validated[1]["previousHash"] == validated[0]["eventHash"]
    assert validated[1]["causationId"] == validated[0]["eventId"]
    assert all(event["mode"] == "PLAN" for event in validated)
    assert all(event["rawOutputIncluded"] is False for event in validated)
    assert all(event["secretMaterialIncluded"] is False for event in validated)
    assert all(calculate_event_hash(event) == event["eventHash"] for event in validated)


def test_event_content_tampering_breaks_its_canonical_hash() -> None:
    event = deepcopy(_append()[0])
    event["outcome"] = "REJECTED"
    with pytest.raises(LogContractError, match="event hash differs"):
        validate_event(event)


def test_rehashed_sequence_and_predecessor_tampering_still_breaks_chain() -> None:
    events = list(_append())
    events = list(_append(events, occurred_at="2026-09-01T10:00:01Z"))
    events[1]["previousHash"] = "c" * 64
    events[1]["eventHash"] = calculate_event_hash(events[1])
    with pytest.raises(LogContractError, match="predecessor"):
        validate_event_chain(events)

    events = list(_append())
    events[0]["sequence"] = 2
    events[0]["eventHash"] = calculate_event_hash(events[0])
    with pytest.raises(LogContractError, match="sequence"):
        validate_event_chain(events)


def test_raw_output_secret_flags_and_reserved_event_namespace_fail_closed() -> None:
    event = deepcopy(_append()[0])
    event["rawOutputIncluded"] = True
    event["eventHash"] = calculate_event_hash(event)
    with pytest.raises(LogContractError, match="closed schema"):
        validate_event(event)

    with pytest.raises(LogContractError, match="closed schema"):
        _append(event_type="logs.private")


def test_secret_shaped_values_and_floats_never_enter_canonical_events() -> None:
    with pytest.raises(ContractError, match="secret-shaped value"):
        append_planning_event(
            (),
            stream="koru.poa.ticket-023",
            event_type="koru.poa.plan_compiled",
            occurred_at="2026-09-01T10:00:00Z",
            correlation_id="github_pat_abcdefghijklmnopqrstuvwxyz",
            producer="agent:koru",
            subject_ref="ticket:ticket-023",
            outcome="SUCCEEDED",
            subject_state="planned",
            input_hash=INPUT_HASH,
        )
    with pytest.raises(ContractError, match="floating-point"):
        calculate_event_hash({"unsafe": 0.1})


def test_chain_requires_monotonic_normalized_utc_timestamps() -> None:
    events = _append(occurred_at="2026-09-01T10:00:02Z")
    with pytest.raises(LogContractError, match="timestamps"):
        _append(events, occurred_at="2026-09-01T10:00:01Z")
    with pytest.raises(LogContractError, match="normalized UTC"):
        _append(occurred_at="2026-09-01T12:00:00+02:00")
