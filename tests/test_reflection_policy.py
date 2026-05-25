from __future__ import annotations

from types import SimpleNamespace

from koru.autonomy.reflection_policy import decide_chat_reflection


def test_reflection_disabled_returns_reason() -> None:
    decision = decide_chat_reflection(
        enabled=False,
        last_type="message.received",
        reflection_events=[SimpleNamespace(type="message.received")],
    )

    assert decision.should_reflect is False
    assert decision.reason == "disabled"


def test_reflection_uses_llm_for_received_events() -> None:
    decision = decide_chat_reflection(
        enabled=True,
        last_type="message.received",
        reflection_events=[SimpleNamespace(type="message.sent"), SimpleNamespace(type="message.received")],
    )

    assert decision.should_reflect is True
    assert decision.reason == "message_received_ambiguous"


def test_reflection_skips_llm_for_sent_only_cooldown() -> None:
    decision = decide_chat_reflection(
        enabled=True,
        last_type="message.sent",
        reflection_events=[SimpleNamespace(type="message.sent")],
    )

    assert decision.should_reflect is True
    assert decision.reason == "sent_only_operator_reflection_enabled"
