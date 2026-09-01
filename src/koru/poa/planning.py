"""Pure POA-P planning over evidence-only Subactor source snapshots."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from typing import Any

from .contracts import (
    POA_PROCESS_SCHEMA_SHA256,
    POA_REQUEST_GRAMMAR_SHA256,
    ContractError,
    canonical_json,
    reject_secret_material,
    sha256_json,
    validate_poa_document,
    validate_source_snapshot,
)

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_TICKET_RE = re.compile(r"^ticket-[0-9]{3,}$")
_POLICY_RE = re.compile(r"^policy://[a-z0-9.-]+/[a-z][a-z0-9._:/-]*/v[1-9][0-9]*$")
_ARTIFACT_RE = re.compile(r"^artifact://[a-z0-9.-]+/[A-Za-z0-9._:/-]+/r[1-9][0-9]*$")
_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?Z$"
)
_POLICY_FIELDS = {
    "schema",
    "policyRef",
    "decisionRef",
    "decisionSha256",
    "inputHash",
    "decision",
    "authority",
    "executionAuthorityGranted",
}


class PlanningError(ContractError):
    """A deterministic planning failure."""


class BindingNotFound(PlanningError):
    """No exact candidate exists for a required capability."""


class AmbiguousBinding(PlanningError):
    """More than one candidate has the highest priority."""


class PolicyDenied(PlanningError):
    """The separate policy boundary did not admit inert planning."""


def build_source_snapshot(
    *,
    snapshot_id: str,
    created_at: str,
    valid_until: str,
    config_responses: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build and validate a hash-pinned snapshot from secret-free discovery data."""

    responses = [deepcopy(dict(item)) for item in config_responses]
    snapshot: dict[str, Any] = {
        "schema": "koru.poa/source-registry-snapshot/v1",
        "snapshotId": snapshot_id,
        "createdAt": created_at,
        "validUntil": valid_until,
        "resolutions": [
            {"response": response, "responseSha256": sha256_json(response)} for response in responses
        ],
        "evidence": [deepcopy(dict(item)) for item in evidence],
        "candidates": [deepcopy(dict(item)) for item in candidates],
    }
    snapshot["snapshotHash"] = sha256_json(snapshot)
    return validate_source_registry_snapshot(snapshot)


def validate_source_registry_snapshot(document: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = validate_source_snapshot(document)
    supplied_hash = snapshot["snapshotHash"]
    unhashed = {key: value for key, value in snapshot.items() if key != "snapshotHash"}
    if sha256_json(unhashed) != supplied_hash:
        raise PlanningError("source snapshot hash differs from canonical bytes")

    created_at = _parse_utc(snapshot["createdAt"], "snapshot createdAt")
    valid_until = _parse_utc(snapshot["validUntil"], "snapshot validUntil")
    if valid_until <= created_at:
        raise PlanningError("source snapshot validity interval is not increasing")

    resolutions: dict[str, Mapping[str, Any]] = {}
    sources: dict[str, Mapping[str, Any]] = {}
    sources_by_need: dict[str, set[str]] = {}
    for resolution in snapshot["resolutions"]:
        response = resolution["response"]
        if sha256_json(response) != resolution["responseSha256"]:
            raise PlanningError("Subactor Config response digest differs from canonical bytes")
        data = response["data"]
        need = data["need"]
        if need in resolutions:
            raise PlanningError("source snapshot contains duplicate Config resolution needs")
        resolutions[need] = response
        source_rows = data["matchedSources"]
        source_ids = [row["id"] for row in source_rows]
        if len(source_ids) != len(set(source_ids)):
            raise PlanningError("Subactor Config response contains duplicate source IDs")
        if any(need not in row["provides"] for row in source_rows):
            raise PlanningError("Subactor Config response source does not provide its resolved need")
        sources_by_need[need] = set(source_ids)
        for row in source_rows:
            existing = sources.get(row["id"])
            if existing is not None and canonical_json(existing) != canonical_json(row):
                raise PlanningError("Subactor Config source differs between resolution responses")
            sources[row["id"]] = row

    evidence_by_role: dict[str, Mapping[str, Any]] = {}
    for item in snapshot["evidence"]:
        role = item["role"]
        if role in evidence_by_role:
            raise PlanningError(f"source snapshot contains duplicate {role} evidence")
        evidence_by_role[role] = item
    if set(evidence_by_role) != {"registry", "strategy"}:
        raise PlanningError("source snapshot requires exactly one Registry and one Strategy evidence reference")
    for role, item in evidence_by_role.items():
        source = sources.get(item["sourceId"])
        if source is None or source["kind"] != role:
            raise PlanningError(f"{role} evidence is not bound to its discovered source kind")
        if source["availability"]["state"] != "ready":
            raise PlanningError(f"{role} evidence source is not ready")

    required_source_ids = {item["sourceId"] for item in evidence_by_role.values()}
    binding_ids: set[str] = set()
    for candidate in snapshot["candidates"]:
        config_needs = set(candidate["configNeeds"])
        if not config_needs.issubset(resolutions):
            raise PlanningError("binding candidate references an unavailable Config resolution need")
        candidate_sources = set(candidate["sourceIds"])
        if not required_source_ids.issubset(candidate_sources) or not candidate_sources.issubset(sources):
            raise PlanningError(
                "binding candidate provenance is not closed over discovered Registry and Strategy sources"
            )
        if any(not candidate_sources.intersection(sources_by_need[need]) for need in config_needs):
            raise PlanningError("binding candidate does not bind every declared Config resolution need")
        binding = validate_poa_document(candidate["binding"], expected_schema="poa.binding/v1")
        binding_id = binding["binding_id"]
        if binding_id in binding_ids:
            raise PlanningError("source snapshot contains duplicate binding IDs")
        binding_ids.add(binding_id)
    return snapshot


def policy_input_hash(
    *,
    process: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    ticket_id: str,
    input_sha256: str,
) -> str:
    process_value = validate_poa_document(process, expected_schema="poa.process/v1")
    snapshot_value = validate_source_registry_snapshot(snapshot)
    _validate_ticket_and_hash(ticket_id, input_sha256)
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
    if set(decision) != _POLICY_FIELDS:
        raise PlanningError("policy decision fields do not match the closed input contract")
    if decision.get("schema") != "koru.poa/policy-decision-input/v1":
        raise PlanningError("policy decision schema is unsupported")
    policy_ref = decision.get("policyRef")
    decision_ref = decision.get("decisionRef")
    if not isinstance(policy_ref, str) or _POLICY_RE.fullmatch(policy_ref) is None:
        raise PlanningError("policy decision reference is invalid")
    if not isinstance(decision_ref, str) or _ARTIFACT_RE.fullmatch(decision_ref) is None:
        raise PlanningError("policy decision artifact reference is invalid")
    for field in ("decisionSha256", "inputHash"):
        value = decision.get(field)
        if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
            raise PlanningError(f"policy decision {field} is invalid")
    decision_payload = {key: value for key, value in decision.items() if key != "decisionSha256"}
    if sha256_json(decision_payload) != decision["decisionSha256"]:
        raise PlanningError("policy decision digest differs from canonical bytes")
    if decision.get("decision") not in {"admit-plan", "deny-plan"}:
        raise PlanningError("policy decision verdict is invalid")
    if decision.get("authority") != "evidence-only" or decision.get("executionAuthorityGranted") is not False:
        raise PlanningError("policy decision attempts to grant execution authority")
    return decision


def compile_inert_plan(
    *,
    process: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    policy_decision: Mapping[str, Any],
    ticket_id: str,
    input_ref: str,
    input_sha256: str,
    valid_until: str,
    subject: str = "agent:koru",
    grant_ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Compile an exact, inert POA plan; never issue a grant or execute it."""

    process_value = validate_poa_document(process, expected_schema="poa.process/v1")
    snapshot_value = validate_source_registry_snapshot(snapshot)
    decision = validate_policy_decision(policy_decision)
    _validate_ticket_and_hash(ticket_id, input_sha256)
    if decision["policyRef"] not in process_value["policy_refs"]:
        raise PlanningError("policy decision is not declared by the process")
    expected_policy_input = policy_input_hash(
        process=process_value,
        snapshot=snapshot_value,
        ticket_id=ticket_id,
        input_sha256=input_sha256,
    )
    if decision["inputHash"] != expected_policy_input:
        raise PlanningError("policy decision is not bound to the planning input")
    if decision["decision"] != "admit-plan":
        raise PolicyDenied("separate policy boundary denied inert planning")
    if (
        isinstance(grant_ttl_seconds, bool)
        or not isinstance(grant_ttl_seconds, int)
        or not 1 <= grant_ttl_seconds <= 900
    ):
        raise PlanningError("grant TTL is outside the POA contract")

    requested_until = _parse_utc(valid_until, "plan validUntil")
    snapshot_created = _parse_utc(snapshot_value["createdAt"], "snapshot createdAt")
    snapshot_until = _parse_utc(snapshot_value["validUntil"], "snapshot validUntil")
    if not snapshot_created < requested_until <= snapshot_until:
        raise PlanningError("plan validity is outside the source snapshot interval")

    request = {
        "schema": "poa.request/v1",
        "operation": "plan",
        "process_ref": process_value["process_ref"],
        "input_ref": input_ref,
        "input_sha256": input_sha256,
    }
    validate_poa_document(request, expected_schema="poa.request/v1")
    request_hash = sha256_json(request)
    _validate_process_graph(process_value["steps"])
    selected = _select_bindings(process_value, snapshot_value)

    planned_steps: list[dict[str, Any]] = []
    selected_evidence: list[dict[str, Any]] = []
    for step in process_value["steps"]:
        candidate = selected[step["capability_ref"]]
        binding = candidate["binding"]
        _require_process_uri_kind(binding["process_uri"], step["kind"])
        idempotency_digest = sha256_json(
            {
                "ticket": ticket_id,
                "step": step["id"],
                "request": request_hash,
                "binding": binding["binding_id"],
            }
        )
        planned_step: dict[str, Any] = {
            "id": step["id"],
            "capability_ref": step["capability_ref"],
            "process_uri": binding["process_uri"],
            "target_ref": binding["target_ref"],
            "kind": step["kind"],
            "effects": deepcopy(step["effects"]),
            "depends_on": deepcopy(step["depends_on"]),
            "input_ref": input_ref,
            "input_sha256": input_sha256,
            "timeout_seconds": step["timeout_seconds"],
            "max_attempts": step["max_attempts"],
            "idempotency_key": f"{ticket_id.replace('-', '.')}.{step['id']}.{idempotency_digest[:16]}",
            "verification": deepcopy(step["verification"]),
        }
        compensation_ref = step.get("compensation_capability_ref")
        if compensation_ref is not None:
            compensation = selected[compensation_ref]["binding"]
            _require_process_uri_kind(compensation["process_uri"], "command")
            planned_step["compensation_process_uri"] = compensation["process_uri"]
        planned_steps.append(planned_step)
        selected_evidence.append(
            {
                "stepId": step["id"],
                "bindingId": binding["binding_id"],
                "sourceIds": deepcopy(candidate["sourceIds"]),
            }
        )

    process_hash = sha256_json(process_value)
    seed_hash = sha256_json(
        {
            "ticket": ticket_id,
            "process": process_hash,
            "snapshot": snapshot_value["snapshotHash"],
            "policy": decision["decisionSha256"],
            "request": request_hash,
            "validUntil": valid_until,
        }
    )
    plan: dict[str, Any] = {
        "schema": "poa.plan/v1",
        "plan_id": f"plan.{ticket_id.replace('-', '.')}.{seed_hash[:16]}",
        "process_ref": process_value["process_ref"],
        "request_sha256": request_hash,
        "valid_until": valid_until,
        "steps": planned_steps,
        "dsl_contract": {
            "schema_ref": "schema://wellmanifest.dev/poa/process/v1",
            "grammar_ref": "grammar://wellmanifest.dev/poa/request/v1",
            "schema_sha256": POA_PROCESS_SCHEMA_SHA256,
            "grammar_sha256": POA_REQUEST_GRAMMAR_SHA256,
            "canonical_sha256": request_hash,
            "canonicalization": "RFC8785",
            "hash_algorithm": "SHA-256",
            "validated": True,
            "additional_properties": False,
        },
        "authority_requirements": {
            "subject": subject,
            "scopes": ["poa.plan"],
            "grant_ttl_seconds": grant_ttl_seconds,
            "intent_required": True,
            "plan_hash_binding": True,
        },
        "execution_boundary": {
            "boundary_ref": "target://koru.dev/planning/inert",
            "host_shell": False,
            "arbitrary_executable": False,
            "transport_from_registry": True,
        },
        "hash_profile": "RFC8785+SHA-256",
    }
    plan["plan_hash"] = sha256_json(plan)
    plan = validate_poa_document(plan, expected_schema="poa.plan/v1")

    result: dict[str, Any] = {
        "schema": "koru.poa/planning-result/v1",
        "ticketRef": f"ticket:{ticket_id}",
        "processSha256": process_hash,
        "snapshotSha256": snapshot_value["snapshotHash"],
        "policyDecisionRef": decision["decisionRef"],
        "policyDecisionSha256": decision["decisionSha256"],
        "selectedBindings": selected_evidence,
        "plan": plan,
        "authorityGranted": False,
        "executable": False,
    }
    result["resultHash"] = sha256_json(result)
    return result


def verify_planning_result(result: Mapping[str, Any]) -> None:
    expected_fields = {
        "schema",
        "ticketRef",
        "processSha256",
        "snapshotSha256",
        "policyDecisionRef",
        "policyDecisionSha256",
        "selectedBindings",
        "plan",
        "authorityGranted",
        "executable",
        "resultHash",
    }
    if set(result) != expected_fields or result.get("schema") != "koru.poa/planning-result/v1":
        raise PlanningError("planning result fields do not match the closed contract")
    if result.get("authorityGranted") is not False or result.get("executable") is not False:
        raise PlanningError("planning result attempts to cross the execution boundary")
    supplied = result.get("resultHash")
    if not isinstance(supplied, str) or _SHA256_RE.fullmatch(supplied) is None:
        raise PlanningError("planning result hash is invalid")
    unhashed = {key: deepcopy(value) for key, value in result.items() if key != "resultHash"}
    if sha256_json(unhashed) != supplied:
        raise PlanningError("planning result hash differs from canonical bytes")
    plan = validate_poa_document(result["plan"], expected_schema="poa.plan/v1")
    plan_hash = plan["plan_hash"]
    if sha256_json({key: value for key, value in plan.items() if key != "plan_hash"}) != plan_hash:
        raise PlanningError("POA plan hash differs from canonical bytes")


def _select_bindings(process: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    by_capability: dict[str, list[Mapping[str, Any]]] = {}
    for candidate in snapshot["candidates"]:
        capability = candidate["binding"]["capability_ref"]
        by_capability.setdefault(capability, []).append(candidate)

    required = {step["capability_ref"] for step in process["steps"]}
    required.update(
        step["compensation_capability_ref"]
        for step in process["steps"]
        if "compensation_capability_ref" in step
    )
    selected: dict[str, Mapping[str, Any]] = {}
    for capability in sorted(required):
        candidates = by_capability.get(capability, [])
        if not candidates:
            raise BindingNotFound(f"no binding for required capability {capability}")
        highest = max(candidate["binding"]["priority"] for candidate in candidates)
        winners = [candidate for candidate in candidates if candidate["binding"]["priority"] == highest]
        if len(winners) != 1:
            raise AmbiguousBinding(f"ambiguous highest-priority binding for {capability}")
        selected[capability] = winners[0]
    return selected


def _validate_process_graph(steps: Sequence[Mapping[str, Any]]) -> None:
    ids = [step["id"] for step in steps]
    if len(ids) != len(set(ids)):
        raise PlanningError("process contains duplicate step IDs")
    known = set(ids)
    graph = {step["id"]: set(step["depends_on"]) for step in steps}
    if any(not dependencies.issubset(known) for dependencies in graph.values()):
        raise PlanningError("process step depends on an unknown step")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visiting:
            raise PlanningError("process dependency graph contains a cycle")
        if step_id in visited:
            return
        visiting.add(step_id)
        for dependency in graph[step_id]:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in ids:
        visit(step_id)


def _require_process_uri_kind(process_uri: str, kind: str) -> None:
    marker = f"/{kind}/"
    if marker not in process_uri:
        raise PlanningError(f"binding process URI does not implement the declared {kind} kind")


def _validate_ticket_and_hash(ticket_id: str, input_sha256: str) -> None:
    if not isinstance(ticket_id, str) or _TICKET_RE.fullmatch(ticket_id) is None:
        raise PlanningError("ticket ID is invalid")
    if not isinstance(input_sha256, str) or _SHA256_RE.fullmatch(input_sha256) is None:
        raise PlanningError("input SHA-256 is invalid")


def _parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        raise PlanningError(f"{label} is not normalized UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise PlanningError(f"{label} is invalid") from error


__all__ = [
    "AmbiguousBinding",
    "BindingNotFound",
    "PlanningError",
    "PolicyDenied",
    "build_source_snapshot",
    "canonical_json",
    "compile_inert_plan",
    "policy_input_hash",
    "validate_policy_decision",
    "validate_source_registry_snapshot",
    "verify_planning_result",
]
