"""Compile and verify exact, inert POA plans.

Compilation selects the highest-priority binding for every required
capability, verifies the process dependency graph, and emits a hash-pinned
``poa.plan/v1`` plus planning result that never crosses the execution
boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, NamedTuple

from .contracts import (
    POA_PROCESS_SCHEMA_SHA256,
    POA_REQUEST_GRAMMAR_SHA256,
    sha256_json,
    validate_poa_document,
)
from .errors import (
    AmbiguousBinding,
    BindingNotFound,
    PlanningError,
    PolicyDenied,
)
from .policy_decisions import policy_input_hash, validate_policy_decision
from .snapshots import validate_source_registry_snapshot
from .validation import SHA256_RE, parse_utc, validate_ticket_and_hash


class _ValidatedInputs(NamedTuple):
    """Documents that passed the planning-input and policy-boundary checks."""

    process: Mapping[str, Any]
    snapshot: Mapping[str, Any]
    decision: Mapping[str, Any]


class _PlannedCompilation(NamedTuple):
    """Compiled per-step output plus the selected-binding evidence trail."""

    planned_steps: list[dict[str, Any]]
    selected_evidence: list[dict[str, Any]]


class _CompiledPlan(NamedTuple):
    """Validated ``poa.plan/v1`` document and its source process hash."""

    plan: dict[str, Any]
    process_hash: str


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

    inputs = _validate_planning_inputs(
        process=process,
        snapshot=snapshot,
        policy_decision=policy_decision,
        ticket_id=ticket_id,
        input_sha256=input_sha256,
        grant_ttl_seconds=grant_ttl_seconds,
    )
    _require_validity_window(inputs.snapshot, valid_until)
    request_hash = _request_hash(inputs.process, input_ref, input_sha256)
    _validate_process_graph(inputs.process["steps"])
    selected = _select_bindings(inputs.process, inputs.snapshot)
    compiled = _compile_planned_steps(
        inputs.process, selected, ticket_id, input_ref, input_sha256, request_hash
    )
    compiled_plan = _build_plan(
        process_value=inputs.process,
        snapshot_value=inputs.snapshot,
        decision=inputs.decision,
        ticket_id=ticket_id,
        valid_until=valid_until,
        subject=subject,
        grant_ttl_seconds=grant_ttl_seconds,
        request_hash=request_hash,
        planned_steps=compiled.planned_steps,
    )
    return _planning_result(
        ticket_id=ticket_id,
        snapshot_value=inputs.snapshot,
        decision=inputs.decision,
        selected_evidence=compiled.selected_evidence,
        compiled_plan=compiled_plan,
    )


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
    if not isinstance(supplied, str) or SHA256_RE.fullmatch(supplied) is None:
        raise PlanningError("planning result hash is invalid")
    unhashed = {key: deepcopy(value) for key, value in result.items() if key != "resultHash"}
    if sha256_json(unhashed) != supplied:
        raise PlanningError("planning result hash differs from canonical bytes")
    plan = validate_poa_document(result["plan"], expected_schema="poa.plan/v1")
    plan_hash = plan["plan_hash"]
    if sha256_json({key: value for key, value in plan.items() if key != "plan_hash"}) != plan_hash:
        raise PlanningError("POA plan hash differs from canonical bytes")


def _validate_planning_inputs(
    *,
    process: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    policy_decision: Mapping[str, Any],
    ticket_id: str,
    input_sha256: str,
    grant_ttl_seconds: int,
) -> _ValidatedInputs:
    process_value = validate_poa_document(process, expected_schema="poa.process/v1")
    snapshot_value = validate_source_registry_snapshot(snapshot)
    decision = validate_policy_decision(policy_decision)
    validate_ticket_and_hash(ticket_id, input_sha256)
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
    return _ValidatedInputs(process_value, snapshot_value, decision)


def _require_validity_window(snapshot_value: Mapping[str, Any], valid_until: str) -> None:
    requested_until = parse_utc(valid_until, "plan validUntil")
    snapshot_created = parse_utc(snapshot_value["createdAt"], "snapshot createdAt")
    snapshot_until = parse_utc(snapshot_value["validUntil"], "snapshot validUntil")
    if not snapshot_created < requested_until <= snapshot_until:
        raise PlanningError("plan validity is outside the source snapshot interval")


def _request_hash(process_value: Mapping[str, Any], input_ref: str, input_sha256: str) -> str:
    request = {
        "schema": "poa.request/v1",
        "operation": "plan",
        "process_ref": process_value["process_ref"],
        "input_ref": input_ref,
        "input_sha256": input_sha256,
    }
    validate_poa_document(request, expected_schema="poa.request/v1")
    return sha256_json(request)


def _compile_planned_steps(
    process_value: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Any]],
    ticket_id: str,
    input_ref: str,
    input_sha256: str,
    request_hash: str,
) -> _PlannedCompilation:
    planned_steps: list[dict[str, Any]] = []
    selected_evidence: list[dict[str, Any]] = []
    for step in process_value["steps"]:
        planned_steps.append(
            _planned_step(step, selected, ticket_id, input_ref, input_sha256, request_hash)
        )
        selected_evidence.append(_binding_evidence(step, selected))
    return _PlannedCompilation(planned_steps, selected_evidence)


def _planned_step(
    step: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Any]],
    ticket_id: str,
    input_ref: str,
    input_sha256: str,
    request_hash: str,
) -> dict[str, Any]:
    binding = selected[step["capability_ref"]]["binding"]
    _require_process_uri_kind(binding["process_uri"], step["kind"])
    idempotency_digest = sha256_json(
        {
            "ticket": ticket_id,
            "step": step["id"],
            "request": request_hash,
            "binding": binding["binding_id"],
        }
    )
    planned: dict[str, Any] = {
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
    compensation_uri = _compensation_process_uri(step, selected)
    if compensation_uri is not None:
        planned["compensation_process_uri"] = compensation_uri
    return planned


def _compensation_process_uri(
    step: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Any]],
) -> str | None:
    compensation_ref = step.get("compensation_capability_ref")
    if compensation_ref is None:
        return None
    compensation = selected[compensation_ref]["binding"]
    _require_process_uri_kind(compensation["process_uri"], "command")
    return compensation["process_uri"]


def _binding_evidence(
    step: Mapping[str, Any],
    selected: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate = selected[step["capability_ref"]]
    return {
        "stepId": step["id"],
        "bindingId": candidate["binding"]["binding_id"],
        "sourceIds": deepcopy(candidate["sourceIds"]),
    }


def _build_plan(
    *,
    process_value: Mapping[str, Any],
    snapshot_value: Mapping[str, Any],
    decision: Mapping[str, Any],
    ticket_id: str,
    valid_until: str,
    subject: str,
    grant_ttl_seconds: int,
    request_hash: str,
    planned_steps: list[dict[str, Any]],
) -> _CompiledPlan:
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
    return _CompiledPlan(
        plan=validate_poa_document(plan, expected_schema="poa.plan/v1"),
        process_hash=process_hash,
    )


def _planning_result(
    *,
    ticket_id: str,
    snapshot_value: Mapping[str, Any],
    decision: Mapping[str, Any],
    selected_evidence: list[dict[str, Any]],
    compiled_plan: _CompiledPlan,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "koru.poa/planning-result/v1",
        "ticketRef": f"ticket:{ticket_id}",
        "processSha256": compiled_plan.process_hash,
        "snapshotSha256": snapshot_value["snapshotHash"],
        "policyDecisionRef": decision["decisionRef"],
        "policyDecisionSha256": decision["decisionSha256"],
        "selectedBindings": selected_evidence,
        "plan": compiled_plan.plan,
        "authorityGranted": False,
        "executable": False,
    }
    result["resultHash"] = sha256_json(result)
    return result


def _select_bindings(process: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    by_capability: dict[str, list[Mapping[str, Any]]] = {}
    for candidate in snapshot["candidates"]:
        capability = candidate["binding"]["capability_ref"]
        by_capability.setdefault(capability, []).append(candidate)

    required = {step["capability_ref"] for step in process["steps"]}
    required.update(
        step["compensation_capability_ref"] for step in process["steps"] if "compensation_capability_ref" in step
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


__all__ = [
    "compile_inert_plan",
    "verify_planning_result",
]
