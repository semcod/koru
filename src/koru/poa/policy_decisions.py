"""Validate the separate policy boundary's inputs for inert planning.

The policy boundary never grants execution authority; these functions pin the
planning input hash and validate the closed decision-input contract that the
boundary must answer over.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .contracts import reject_secret_material, sha256_json, validate_poa_document
from .errors import PlanningError
from .snapshots import validate_source_registry_snapshot
from .validation import (
    ARTIFACT_RE,
    POLICY_RE,
    SHA256_RE,
    validate_ticket_and_hash,
)

POLICY_FIELDS = {
    "schema",
    "policyRef",
    "decisionRef",
    "decisionSha256",
    "inputHash",
    "decision",
    "authority",
    "executionAuthorityGranted",
}


def policy_input_hash(
    *,
    process: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    ticket_id: str,
    input_sha256: str,
) -> str:
    process_value = validate_poa_document(process, expected_schema="poa.process/v1")
    snapshot_value = validate_source_registry_snapshot(snapshot)
    validate_ticket_and_hash(ticket_id, input_sha256)
    return sha256_json(
        {
            "schema": "koru.poa/policy-input/v1",
            "ticketRef": f"ticket:{ticket_id}",
            "processSha256": sha256_json(process_value),
            "snapshotSha256": snapshot_value["snapshotHash"],
            "inputSha256": input_sha256,
        }
    )


def validate_policy_decision(document: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise PlanningError("policy decision must be an object")
    decision = deepcopy(dict(document))
    reject_secret_material(decision)
    _validate_decision_shape(decision)
    if decision.get("decision") not in {"admit-plan", "deny-plan"}:
        raise PlanningError("policy decision verdict is invalid")
    if decision.get("authority") != "evidence-only" or decision.get("executionAuthorityGranted") is not False:
        raise PlanningError("policy decision attempts to grant execution authority")
    return decision


def _validate_decision_shape(decision: dict[str, Any]) -> None:
    if set(decision) != POLICY_FIELDS:
        raise PlanningError("policy decision fields do not match the closed input contract")
    if decision.get("schema") != "koru.poa/policy-decision-input/v1":
        raise PlanningError("policy decision schema is unsupported")
    policy_ref = decision.get("policyRef")
    decision_ref = decision.get("decisionRef")
    if not isinstance(policy_ref, str) or POLICY_RE.fullmatch(policy_ref) is None:
        raise PlanningError("policy decision reference is invalid")
    if not isinstance(decision_ref, str) or ARTIFACT_RE.fullmatch(decision_ref) is None:
        raise PlanningError("policy decision artifact reference is invalid")
    for field in ("decisionSha256", "inputHash"):
        value = decision.get(field)
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise PlanningError(f"policy decision {field} is invalid")
    decision_payload = {key: value for key, value in decision.items() if key != "decisionSha256"}
    if sha256_json(decision_payload) != decision["decisionSha256"]:
        raise PlanningError("policy decision digest differs from canonical bytes")


__all__ = [
    "policy_input_hash",
    "validate_policy_decision",
]
