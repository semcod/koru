from __future__ import annotations

from copy import deepcopy

import pytest

from koru.poa.contracts import ContractError, sha256_json
from koru.poa.logs import planning_events_for_result, validate_event_chain
from koru.poa.planning import (
    AmbiguousBinding,
    BindingNotFound,
    PlanningError,
    PolicyDenied,
    build_source_snapshot,
    compile_inert_plan,
    policy_input_hash,
    validate_source_registry_snapshot,
    verify_planning_result,
)

INPUT_SHA256 = "1" * 64
POLICY_REF = "policy://subactor.policy/koru/plan-admission/v1"


def _source(source_id: str, kind: str, owner: str) -> dict:
    return {
        "schema": "subactor.configuration-source/v1",
        "id": source_id,
        "kind": kind,
        "owners": [owner],
        "trust": "versioned",
        "authority": "evidence-only",
        "provides": ["capability.bind", f"{kind}.lookup"],
        "locations": [
            {
                "id": "catalog",
                "uri": f"repo://github.com/{owner}/catalog.json",
                "access": "read",
                "status": "configured",
            }
        ],
        "availability": {
            "state": "ready",
            "repositories": [{"repository": owner, "present": True}],
        },
    }


def _config_response(need: str, sources: list[dict]) -> dict:
    return {
        "schema": "subactor.config-response/v1",
        "data": {
            "schema": "subactor.configuration-resolution/v1",
            "need": need,
            "matchedSources": sources,
            "authority": "evidence-only",
            "control": {
                "configurationMode": "versioned-proposal",
                "requesters": ["human:user", "agent:supervisor"],
                "supervisorDecisionScope": "all-declared-sources",
                "authoritySource": "external-policy-or-grant",
                "mutationMode": "plan-hash-grant-apply-eql",
                "localVerification": "onedev/local-verify",
            },
        },
    }


def _binding(*, binding_id: str = "binding.inspect.primary", priority: int = 10) -> dict:
    return {
        "schema": "poa.binding/v1",
        "binding_id": binding_id,
        "capability_ref": "capability://koru.dev/repository/inspect/v1",
        "process_uri": "github://github.com/repository/query/inspect",
        "target_ref": "target://github.com/semcod/koru",
        "adapter_ref": "adapter://subactor.dev/config/read/v1",
        "observation_ref": "artifact://subactor.dev/config/observation/r1",
        "observation_sha256": "a" * 64,
        "priority": priority,
    }


def _candidate(binding: dict | None = None) -> dict:
    return {
        "configNeeds": ["registry.lookup", "capability.bind"],
        "sourceIds": ["system-registry", "strategy-runtime"],
        "binding": deepcopy(binding or _binding()),
    }


def _config_responses() -> list[dict]:
    return [
        _config_response(
            "registry.lookup",
            [_source("system-registry", "registry", "subactor/registry")],
        ),
        _config_response(
            "capability.bind",
            [_source("strategy-runtime", "strategy", "subactor/strategy")],
        ),
    ]


def _snapshot(*, candidates: list[dict] | None = None, config_responses: list[dict] | None = None) -> dict:
    return build_source_snapshot(
        snapshot_id="snapshot:ticket-023:r1",
        created_at="2026-09-01T10:00:00Z",
        valid_until="2026-09-01T10:30:00Z",
        config_responses=config_responses or _config_responses(),
        evidence=(
            {
                "role": "registry",
                "sourceId": "system-registry",
                "schemaRef": "schema://subactor.dev/registry/federation/v1",
                "artifactRef": "artifact://subactor.dev/registry/federation/r1",
                "sha256": "b" * 64,
            },
            {
                "role": "strategy",
                "sourceId": "strategy-runtime",
                "schemaRef": "schema://subactor.dev/strategy/proposal/v1",
                "artifactRef": "artifact://subactor.dev/strategy/proposal/r1",
                "sha256": "c" * 64,
            },
        ),
        candidates=candidates or [_candidate()],
    )


def _process() -> dict:
    return {
        "schema": "poa.process/v1",
        "process_ref": "poa://koru.dev/process/inspect-repository/v1",
        "title": "Inspect repository metadata",
        "owner": "service:koru",
        "input_schema_ref": "schema://koru.dev/repository/input/v1",
        "output_schema_ref": "schema://koru.dev/repository/observation/v1",
        "policy_refs": [POLICY_REF],
        "steps": [
            {
                "id": "inspect",
                "capability_ref": "capability://koru.dev/repository/inspect/v1",
                "kind": "query",
                "effects": ["read_data"],
                "depends_on": [],
                "requires_approval": False,
                "timeout_seconds": 30,
                "max_attempts": 1,
                "idempotency": "read_only",
                "verification": [
                    {
                        "capability_ref": "capability://koru.dev/repository/verify/v1",
                        "expectation_schema_ref": "schema://koru.dev/repository/observation/v1",
                    }
                ],
            }
        ],
    }


def _policy(process: dict, snapshot: dict, *, decision: str = "admit-plan") -> dict:
    value = {
        "schema": "koru.poa/policy-decision-input/v1",
        "policyRef": POLICY_REF,
        "decisionRef": "artifact://subactor.dev/policy/decision/r1",
        "inputHash": policy_input_hash(
            process=process,
            snapshot=snapshot,
            ticket_id="ticket-023",
            input_sha256=INPUT_SHA256,
        ),
        "decision": decision,
        "authority": "evidence-only",
        "executionAuthorityGranted": False,
    }
    value["decisionSha256"] = sha256_json(value)
    return value


def _compile(*, process: dict | None = None, snapshot: dict | None = None, policy: dict | None = None) -> dict:
    process_value = process or _process()
    snapshot_value = snapshot or _snapshot()
    policy_value = policy or _policy(process_value, snapshot_value)
    return compile_inert_plan(
        process=process_value,
        snapshot=snapshot_value,
        policy_decision=policy_value,
        ticket_id="ticket-023",
        input_ref="artifact://semcod.dev/koru/ticket-023/input/r1",
        input_sha256=INPUT_SHA256,
        valid_until="2026-09-01T10:20:00Z",
    )


def test_dynamic_sources_compile_to_one_deterministic_inert_plan() -> None:
    first = _compile()
    second = _compile()
    assert first == second
    verify_planning_result(first)
    assert first["authorityGranted"] is False
    assert first["executable"] is False
    assert first["selectedBindings"] == [
        {
            "stepId": "inspect",
            "bindingId": "binding.inspect.primary",
            "sourceIds": ["system-registry", "strategy-runtime"],
        }
    ]
    assert first["plan"]["steps"][0]["process_uri"] == "github://github.com/repository/query/inspect"
    assert first["plan"]["plan_hash"] == sha256_json(
        {key: value for key, value in first["plan"].items() if key != "plan_hash"}
    )


def test_lower_priority_candidate_does_not_change_exact_selection() -> None:
    candidates = [
        _candidate(_binding()),
        _candidate(_binding(binding_id="binding.inspect.secondary", priority=5)),
    ]
    result = _compile(snapshot=_snapshot(candidates=candidates))
    assert result["selectedBindings"][0]["bindingId"] == "binding.inspect.primary"


def test_equal_priority_and_missing_bindings_fail_closed() -> None:
    ambiguous = _snapshot(
        candidates=[
            _candidate(_binding()),
            _candidate(_binding(binding_id="binding.inspect.equal", priority=10)),
        ]
    )
    with pytest.raises(AmbiguousBinding, match="ambiguous"):
        _compile(snapshot=ambiguous)

    unrelated = _binding(binding_id="binding.other.primary")
    unrelated["capability_ref"] = "capability://koru.dev/repository/other/v1"
    with pytest.raises(BindingNotFound, match="no binding"):
        _compile(snapshot=_snapshot(candidates=[_candidate(unrelated)]))


def test_config_registry_and_strategy_remain_evidence_only() -> None:
    responses = _config_responses()
    responses[0]["data"]["matchedSources"][0]["authority"] = "execution"
    with pytest.raises(ContractError, match="closed schema"):
        _snapshot(config_responses=responses)

    snapshot = _snapshot()
    snapshot["policyDecision"] = {"decision": "admit-plan"}
    snapshot["snapshotHash"] = sha256_json({key: value for key, value in snapshot.items() if key != "snapshotHash"})
    with pytest.raises(ContractError, match="closed schema"):
        validate_source_registry_snapshot(snapshot)


def test_policy_is_separate_but_cannot_grant_execution_authority() -> None:
    process = _process()
    snapshot = _snapshot()
    escalation = _policy(process, snapshot)
    escalation["executionAuthorityGranted"] = True
    escalation["decisionSha256"] = sha256_json(
        {key: value for key, value in escalation.items() if key != "decisionSha256"}
    )
    with pytest.raises(PlanningError, match="execution authority"):
        _compile(process=process, snapshot=snapshot, policy=escalation)

    denied = _policy(process, snapshot, decision="deny-plan")
    with pytest.raises(PolicyDenied, match="denied"):
        _compile(process=process, snapshot=snapshot, policy=denied)


def test_policy_decision_is_bound_to_process_snapshot_ticket_and_input() -> None:
    process = _process()
    snapshot = _snapshot()
    stale = _policy(process, snapshot)
    stale["inputHash"] = "e" * 64
    stale["decisionSha256"] = sha256_json({key: value for key, value in stale.items() if key != "decisionSha256"})
    with pytest.raises(PlanningError, match="planning input"):
        _compile(process=process, snapshot=snapshot, policy=stale)


def test_snapshot_requires_ready_registry_and_strategy_evidence() -> None:
    responses = _config_responses()
    responses[1]["data"]["matchedSources"][0]["availability"]["state"] = "unavailable"
    responses[1]["data"]["matchedSources"][0]["availability"]["repositories"][0]["present"] = False
    with pytest.raises(PlanningError, match="not ready"):
        _snapshot(config_responses=responses)


def test_config_resolution_need_and_source_uris_are_fail_closed() -> None:
    responses = _config_responses()
    responses[0]["data"]["need"] = "unrelated.need"
    with pytest.raises(PlanningError, match="does not provide"):
        _snapshot(config_responses=responses)

    responses = _config_responses()
    responses[0]["data"]["matchedSources"][0]["locations"][0]["uri"] += "?token=redacted"
    with pytest.raises(ContractError, match="secret-shaped value"):
        _snapshot(config_responses=responses)


def test_inert_result_projects_to_wellmanifest_planning_events() -> None:
    result = _compile()
    events = planning_events_for_result(
        result,
        observed_at="2026-09-01T10:15:00Z",
        planned_at="2026-09-01T10:15:01Z",
    )
    validate_event_chain(events, expected_stream="koru.poa.ticket-023")
    assert [event["eventType"] for event in events] == [
        "koru.poa.binding_selected",
        "koru.poa.plan_compiled",
    ]
    assert events[-1]["inputHash"] == result["plan"]["plan_hash"]
