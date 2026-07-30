from __future__ import annotations

import json

from koru.agent_availability import (
    block_agent,
    classify_unavailability,
    clear_agent_block,
    get_agent_availability,
    learn_unavailability_from_events,
)
from koru.cli_agent_availability import agent_availability_main


def test_durable_block_and_clear() -> None:
    blocked = block_agent(" Qoder ", reason="usage_limit_exhausted", now=100.0)

    assert blocked.blocked is True
    assert get_agent_availability("qoder", now=101.0).reason == "usage_limit_exhausted"

    clear_agent_block("qoder")

    assert get_agent_availability("qoder").status == "available"


def test_temporary_rate_limit_expires() -> None:
    block_agent(
        "cursor",
        reason="rate_limit",
        retry_after_seconds=60,
        now=100.0,
    )

    assert get_agent_availability("cursor", now=159.0).blocked is True
    expired = get_agent_availability("cursor", now=160.0)
    assert expired.blocked is False
    assert expired.reason == "temporary block expired"


def test_environment_available_override_wins(monkeypatch) -> None:
    block_agent("qoder", reason="usage_limit_exhausted")
    monkeypatch.setenv("KORU_AGENT_UNAVAILABLE", "cursor,qoder")
    monkeypatch.setenv("KORU_AGENT_AVAILABLE", "qoder")

    assert get_agent_availability("qoder").status == "available"
    assert get_agent_availability("cursor").blocked is True


def test_classifier_is_high_precision() -> None:
    assert classify_unavailability("You have reached your usage limit.").reason == (
        "usage_limit_exhausted"
    )
    assert classify_unavailability("You have 0 weighted tokens left.").reason == (
        "usage_limit_exhausted"
    )
    assert classify_unavailability("429: too many requests").reason == "rate_limit"
    assert classify_unavailability("I fixed the code that checks a usage limit.") is None


def test_learning_uses_received_events_only() -> None:
    sent_only = learn_unavailability_from_events(
        "qoder",
        [{"type": "message.sent", "text": "The Qoder usage limit is exhausted"}],
    )
    assert sent_only is None
    assert get_agent_availability("qoder").blocked is False

    learned = learn_unavailability_from_events(
        "qoder",
        [{"type": "message.received", "text": "You have reached your usage limit."}],
    )
    assert learned is not None
    assert learned.source == "autopilot:message.received"
    assert get_agent_availability("qoder").blocked is True


def test_learning_checks_error_fields_after_generic_message() -> None:
    from koru.agent_availability import learn_unavailability_from_reply

    learned = learn_unavailability_from_reply(
        "qoder",
        {"message": "drive failed", "stderr": "429: too many requests"},
    )

    assert learned is not None
    assert learned.reason == "rate_limit"


def test_cli_block_status_and_clear(capsys) -> None:
    assert agent_availability_main(
        ["block", "qoder", "--reason", "usage_limit_exhausted"]
    ) == 0
    capsys.readouterr()

    assert agent_availability_main(["status", "qoder", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "unavailable"
    assert payload["agent_id"] == "qoder"

    assert agent_availability_main(["clear", "qoder"]) == 0
    assert "status=available" in capsys.readouterr().out
