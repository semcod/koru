from __future__ import annotations

import time

from koru.autonomy.events import correlation_id, normalize_chat_events, prompt_hash


def test_prompt_hash_is_stable_for_whitespace() -> None:
    assert prompt_hash("hello   world") == prompt_hash("hello world")


def test_correlation_id_includes_ticket_ide_and_prompt_hash() -> None:
    cid = correlation_id(ticket_id="STARTER-1", ide="vscodium", prompt="do work")

    assert cid.startswith("STARTER-1:vscodium:")
    assert cid.endswith(prompt_hash("do work"))


def test_normalize_chat_events_keeps_previous_ticket_correlation() -> None:
    events = [
        {
            "type": "message.sent",
            "ts": time.time() - 10,
            "ide": "vscodium",
            "chat": "default",
            "text": "code2llm reports previous ticket",
        }
    ]

    normalized = normalize_chat_events(
        events,
        waiting_ticket="STARTER-261",
        last_driven_ticket="STARTER-260",
        last_driven_prompt="code2llm reports previous ticket",
        environment_key="os=wayland|ide=vscodium",
    )

    assert len(normalized) == 1
    event = normalized[0]
    assert event.kind == "chat.message_sent"
    assert event.ticket_id == "STARTER-260"
    assert event.payload["waiting_ticket"] == "STARTER-261"
    assert event.payload["matches_last_driven_prompt"] is True
