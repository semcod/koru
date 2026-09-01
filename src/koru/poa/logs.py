"""Wellmanifest Logs v0.3 planning-event projection and hash-chain checks."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from typing import Any

from .contracts import (
    POA_PROCESS_SCHEMA_SHA256,
    WELLMANIFEST_LOGS_CONTRACT_SHA256,
    ContractError,
    load_logs_contract,
    reject_secret_material,
    sha256_json,
    validate_json_document,
)
from .planning import verify_planning_result

ZERO_HASH = "0" * 64
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?Z$"
)


class LogContractError(ContractError):
    """A Wellmanifest Logs event or chain violates the pinned contract."""


def calculate_event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: deepcopy(value) for key, value in event.items() if key != "eventHash"}
    return sha256_json(payload)


def validate_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise LogContractError("log event must be an object")
    value = deepcopy(dict(event))
    reject_secret_material(value)
    bundle = load_logs_contract()
    if (
        bundle.get("schema") != "wellmanifest.logs/contract-bundle/v1"
        or bundle.get("version") != "0.3.0"
        or bundle.get("hashProfile") != "wellmanifest-canonical-json-v1+SHA-256"
    ):
        raise LogContractError("vendored Logs bundle has an unsupported semantic profile")
    try:
        event_schema = bundle["schemas"]["event"]
    except (KeyError, TypeError) as error:
        raise LogContractError("vendored Logs bundle lacks the event schema") from error
    try:
        validate_json_document(value, event_schema, label="log event")
    except ContractError as error:
        raise LogContractError(str(error)) from error
    _parse_utc(value["occurredAt"], "event occurredAt")
    if value["code"] is not None:
        raise LogContractError("planning events cannot cite an unvendored diagnostic definition")
    if value["rawOutputIncluded"] is not False or value["secretMaterialIncluded"] is not False:
        raise LogContractError("planning event safety flags must both be false")
    if calculate_event_hash(value) != value["eventHash"]:
        raise LogContractError("event hash differs from canonical bytes")
    return value


def append_planning_event(
    events: Sequence[Mapping[str, Any]],
    *,
    stream: str,
    event_type: str,
    occurred_at: str,
    correlation_id: str,
    producer: str,
    subject_ref: str,
    outcome: str,
    subject_state: str | None,
    input_hash: str,
    evidence: Sequence[Mapping[str, str]] = (),
    severity: str = "INFO",
    source: str = "koru.poa",
    receipt_ref: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return a new immutable-style chain with one canonical PLAN event appended."""

    existing = validate_event_chain(events, expected_stream=stream) if events else ()
    if existing and existing[0]["correlationId"] != correlation_id:
        raise LogContractError("planning chain correlation ID changed")
    if _SHA256_RE.fullmatch(input_hash) is None:
        raise LogContractError("planning event input hash is invalid")
    _parse_utc(occurred_at, "event occurredAt")
    sequence = len(existing) + 1
    previous_hash = existing[-1]["eventHash"] if existing else ZERO_HASH
    causation_id = existing[-1]["eventId"] if existing else None
    event: dict[str, Any] = {
        "schema": "wellmanifest.logs/event/v1",
        "eventId": "",
        "stream": stream,
        "sequence": sequence,
        "eventType": event_type,
        "severity": severity,
        "mode": "PLAN",
        "occurredAt": occurred_at,
        "correlationId": correlation_id,
        "causationId": causation_id,
        "producer": producer,
        "source": source,
        "code": None,
        "subjectRef": subject_ref,
        "outcome": outcome,
        "subjectState": subject_state,
        "evidence": [deepcopy(dict(item)) for item in evidence],
        "inputHash": input_hash,
        "receiptRef": receipt_ref,
        "previousHash": previous_hash,
        "eventHash": ZERO_HASH,
        "rawOutputIncluded": False,
        "secretMaterialIncluded": False,
    }
    identity_hash = sha256_json({key: value for key, value in event.items() if key not in {"eventId", "eventHash"}})
    event["eventId"] = f"event:{stream}:{sequence}:{identity_hash[:16]}"
    event["eventHash"] = calculate_event_hash(event)
    validated = validate_event(event)
    return validate_event_chain((*existing, validated), expected_stream=stream)


def validate_event_chain(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_stream: str | None = None,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise LogContractError("event chain must be a sequence")
    validated: list[dict[str, Any]] = []
    stream = expected_stream
    correlation_id: str | None = None
    previous_hash = ZERO_HASH
    previous_id: str | None = None
    previous_time: datetime | None = None
    for sequence, event in enumerate(events, start=1):
        value = validate_event(event)
        if stream is None:
            stream = value["stream"]
        if value["stream"] != stream:
            raise LogContractError("event chain spans more than one stream")
        if value["sequence"] != sequence:
            raise LogContractError("event chain sequence is not contiguous")
        if value["previousHash"] != previous_hash:
            raise LogContractError("event predecessor hash is invalid")
        if value["causationId"] != previous_id:
            raise LogContractError("event causation does not bind the predecessor event")
        if correlation_id is None:
            correlation_id = value["correlationId"]
        elif value["correlationId"] != correlation_id:
            raise LogContractError("event chain correlation ID changed")
        occurred_at = _parse_utc(value["occurredAt"], "event occurredAt")
        if previous_time is not None and occurred_at < previous_time:
            raise LogContractError("event timestamps are not monotonic")
        previous_time = occurred_at
        previous_id = value["eventId"]
        previous_hash = value["eventHash"]
        validated.append(value)
    return tuple(validated)


def planning_events_for_result(
    result: Mapping[str, Any],
    *,
    observed_at: str,
    planned_at: str,
    producer: str = "agent:koru",
) -> tuple[dict[str, Any], ...]:
    """Project an inert planning result as two ordered Wellmanifest events."""

    verify_planning_result(result)
    ticket_ref = result["ticketRef"]
    ticket_id = ticket_ref.removeprefix("ticket:")
    stream = f"koru.poa.{ticket_id}"
    correlation_id = f"koru:{ticket_id}:{result['resultHash'][:16]}"
    events = append_planning_event(
        (),
        stream=stream,
        event_type="koru.poa.binding_selected",
        occurred_at=observed_at,
        correlation_id=correlation_id,
        producer=producer,
        subject_ref=ticket_ref,
        outcome="ACCEPTED",
        subject_state="bound",
        input_hash=result["snapshotSha256"],
        evidence=(
            {
                "path": "src/koru/data/poa-process-v1.schema.json",
                "sha256": POA_PROCESS_SCHEMA_SHA256,
            },
        ),
    )
    return append_planning_event(
        events,
        stream=stream,
        event_type="koru.poa.plan_compiled",
        occurred_at=planned_at,
        correlation_id=correlation_id,
        producer=producer,
        subject_ref=ticket_ref,
        outcome="SUCCEEDED",
        subject_state="planned",
        input_hash=result["plan"]["plan_hash"],
        evidence=(
            {
                "path": "src/koru/data/wellmanifest-logs-contract-v0.3.json",
                "sha256": WELLMANIFEST_LOGS_CONTRACT_SHA256,
            },
        ),
    )


def _parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        raise LogContractError(f"{label} is not normalized UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise LogContractError(f"{label} is invalid") from error


__all__ = [
    "LogContractError",
    "ZERO_HASH",
    "append_planning_event",
    "calculate_event_hash",
    "planning_events_for_result",
    "validate_event",
    "validate_event_chain",
]
