from __future__ import annotations

from koru.autonomy.policy_decision import AutopilotPolicyDecision


def test_proceed_contract_defaults() -> None:
    decision = AutopilotPolicyDecision.proceed()
    assert decision.should_skip is False
    assert decision.reason_code == ""
    assert decision.status == ""
    assert decision.as_skip_tuple() == (False, "")


def test_skip_contract_renders_legacy_status() -> None:
    decision = AutopilotPolicyDecision.skip(
        "chat_activity",
        because="cooldown active",
        action_hint="wait",
    )
    assert decision.should_skip is True
    assert decision.reason_code == "chat_activity"
    assert decision.status == "skipped(chat_activity)"
    assert decision.because == "cooldown active"
    assert decision.action_hint == "wait"
    assert decision.as_skip_tuple() == (True, "skipped(chat_activity)")


def test_skip_contract_normalizes_empty_reason_to_unknown() -> None:
    decision = AutopilotPolicyDecision.skip("")
    assert decision.reason_code == "unknown"
    assert decision.status == "skipped(unknown)"
