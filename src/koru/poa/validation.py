"""Shared primitive validators for POA-P planning inputs.

These are the leaf checks (canonical SHA-256 text, ticket IDs, policy and
artifact references, normalized UTC timestamps) shared by the snapshot,
policy-decision and plan-compilation responsibilities.
"""

from __future__ import annotations

import re
from datetime import datetime

from .errors import PlanningError

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
TICKET_RE = re.compile(r"^ticket-[0-9]{3,}$")
POLICY_RE = re.compile(r"^policy://[a-z0-9.-]+/[a-z][a-z0-9._:/-]*/v[1-9][0-9]*$")
ARTIFACT_RE = re.compile(r"^artifact://[a-z0-9.-]+/[A-Za-z0-9._:/-]+/r[1-9][0-9]*$")
UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?Z$"
)


def parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise PlanningError(f"{label} is not normalized UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise PlanningError(f"{label} is invalid") from error


def validate_ticket_and_hash(ticket_id: str, input_sha256: str) -> None:
    if not isinstance(ticket_id, str) or TICKET_RE.fullmatch(ticket_id) is None:
        raise PlanningError("ticket ID is invalid")
    if not isinstance(input_sha256, str) or SHA256_RE.fullmatch(input_sha256) is None:
        raise PlanningError("input SHA-256 is invalid")


__all__ = [
    "ARTIFACT_RE",
    "POLICY_RE",
    "SHA256_RE",
    "TICKET_RE",
    "UTC_RE",
    "parse_utc",
    "validate_ticket_and_hash",
]
