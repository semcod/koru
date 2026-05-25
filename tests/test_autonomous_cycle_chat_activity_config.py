"""Tests for autonomous_cycle_chat_activity_config module (R-CA1 extraction).

Targets the env-config readers directly. Existing redrive cooldown tests
exercise the same logic via the legacy ``_autopilot_redrive_cooldown_seconds``
import path on ``autonomous_cycle_chat_activity``; these focused tests keep
that contract explicit at the new module boundary.
"""

from __future__ import annotations

import pytest

from koru.autonomous_cycle_chat_activity_config import (
    autopilot_escalation_cooldown_seconds,
    autopilot_redrive_cooldown_seconds,
    chat_intake_ticket_enabled,
    llm_needs_input_heuristic_enabled,
    llm_needs_input_ticket_enabled,
    llm_needs_input_ticket_priority,
    llm_needs_input_ticket_queue_name,
    llm_reflection_summary_max_age_seconds,
)


# ---------------------------------------------------------------------------
# autopilot_redrive_cooldown_seconds
# ---------------------------------------------------------------------------


def test_redrive_cooldown_default_is_300s(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", raising=False)
    assert autopilot_redrive_cooldown_seconds() == pytest.approx(300.0)


def test_redrive_cooldown_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "75")
    assert autopilot_redrive_cooldown_seconds() == pytest.approx(75.0)


def test_redrive_cooldown_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "garbage")
    assert autopilot_redrive_cooldown_seconds() == pytest.approx(300.0)


def test_redrive_cooldown_negative_clamped_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "-50")
    assert autopilot_redrive_cooldown_seconds() == 0.0


# ---------------------------------------------------------------------------
# autopilot_escalation_cooldown_seconds (depends on base_cooldown floor)
# ---------------------------------------------------------------------------


def test_escalation_cooldown_default_is_1800s(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", raising=False)
    assert autopilot_escalation_cooldown_seconds(300.0) == pytest.approx(1800.0)


def test_escalation_cooldown_never_below_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escalation cooldown must never shrink below the base redrive cooldown."""
    monkeypatch.setenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "60")
    assert autopilot_escalation_cooldown_seconds(300.0) == pytest.approx(300.0)


def test_escalation_cooldown_uses_env_when_above_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "3600")
    assert autopilot_escalation_cooldown_seconds(300.0) == pytest.approx(3600.0)


def test_escalation_cooldown_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "nope")
    assert autopilot_escalation_cooldown_seconds(300.0) == pytest.approx(1800.0)


# ---------------------------------------------------------------------------
# llm_reflection_summary_max_age_seconds
# ---------------------------------------------------------------------------


def test_llm_reflection_max_age_default_is_1800s(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS", raising=False)
    assert llm_reflection_summary_max_age_seconds() == pytest.approx(1800.0)


def test_llm_reflection_max_age_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS", "60")
    assert llm_reflection_summary_max_age_seconds() == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Boolean toggles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "Off"])
def test_llm_needs_input_ticket_disabled_via_env(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("KORU_LLM_NEEDS_INPUT_TICKET", value)
    assert llm_needs_input_ticket_enabled() is False


def test_llm_needs_input_ticket_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_NEEDS_INPUT_TICKET", raising=False)
    assert llm_needs_input_ticket_enabled() is True


def test_llm_needs_input_heuristic_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_NEEDS_INPUT_HEURISTIC", raising=False)
    assert llm_needs_input_heuristic_enabled() is True


def test_chat_intake_ticket_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_CHAT_INTAKE_TICKET", raising=False)
    assert chat_intake_ticket_enabled() is True


def test_chat_intake_ticket_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_CHAT_INTAKE_TICKET", "0")
    assert chat_intake_ticket_enabled() is False


# ---------------------------------------------------------------------------
# String env readers
# ---------------------------------------------------------------------------


def test_llm_needs_input_ticket_queue_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_NEEDS_INPUT_TICKET_QUEUE", raising=False)
    assert llm_needs_input_ticket_queue_name() == "operator"


def test_llm_needs_input_ticket_queue_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_NEEDS_INPUT_TICKET_QUEUE", "review")
    assert llm_needs_input_ticket_queue_name() == "review"


def test_llm_needs_input_ticket_priority_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY", raising=False)
    assert llm_needs_input_ticket_priority() == "high"


def test_llm_needs_input_ticket_priority_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY", "medium")
    assert llm_needs_input_ticket_priority() == "medium"


# ---------------------------------------------------------------------------
# Re-export contract: legacy private aliases on chat_activity module still work
# ---------------------------------------------------------------------------


def test_legacy_private_aliases_remain_importable_from_chat_activity_module() -> None:
    """Existing test imports of ``_autopilot_redrive_cooldown_seconds`` etc.
    from ``koru.autonomous_cycle_chat_activity`` must keep working after the
    R-CA1 extraction (backward-compat contract)."""

    from koru.autonomous_cycle_chat_activity import (
        _autopilot_escalation_cooldown_seconds,
        _autopilot_redrive_cooldown_seconds,
        _chat_intake_ticket_enabled,
        _llm_needs_input_heuristic_enabled,
        _llm_needs_input_ticket_enabled,
        _llm_needs_input_ticket_priority,
        _llm_needs_input_ticket_queue_name,
        _llm_reflection_summary_max_age_seconds,
    )

    # Aliases must point at the same callable as the public names.
    assert _autopilot_redrive_cooldown_seconds is autopilot_redrive_cooldown_seconds
    assert _autopilot_escalation_cooldown_seconds is autopilot_escalation_cooldown_seconds
    assert _llm_reflection_summary_max_age_seconds is llm_reflection_summary_max_age_seconds
    assert _llm_needs_input_ticket_enabled is llm_needs_input_ticket_enabled
    assert _llm_needs_input_ticket_queue_name is llm_needs_input_ticket_queue_name
    assert _llm_needs_input_ticket_priority is llm_needs_input_ticket_priority
    assert _llm_needs_input_heuristic_enabled is llm_needs_input_heuristic_enabled
    assert _chat_intake_ticket_enabled is chat_intake_ticket_enabled
