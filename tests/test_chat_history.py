"""Tests for :mod:`koruide.chat_history`.

These pin the on-disk contract between the autopilot daemon (which writes
NDJSON chat events) and the autonomous loop (which now reads those events
to avoid redriving the same prompt while the IDE-side LLM is still working).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from koruide.chat_history import (
    ChatEvent,
    has_recent_activity,
    last_event,
    read_events,
)


def _write_events(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(e, separators=(",", ":")) for e in events) + "\n",
        encoding="utf-8",
    )


def test_read_events_filters_by_ide_and_type(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    now = time.time()
    _write_events(
        path,
        [
            {"ts": now - 10, "type": "message.sent", "ide": "vscode", "chat": "default", "text": "hi"},
            {"ts": now - 5, "type": "message.received", "ide": "vscode", "chat": "default", "text": "ok"},
            {"ts": now - 1, "type": "message.sent", "ide": "cursor", "chat": "default", "text": "hi"},
        ],
    )
    vscode = read_events(path, ide="vscode")
    assert [e.type for e in vscode] == ["message.sent", "message.received"]
    just_sent = read_events(path, types=("message.sent",))
    assert all(e.type == "message.sent" for e in just_sent)
    assert len(just_sent) == 2


def test_read_events_filters_by_age(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    now = time.time()
    _write_events(
        path,
        [
            {"ts": now - 1000, "type": "message.sent", "ide": "vscode", "chat": "default"},
            {"ts": now - 10, "type": "message.sent", "ide": "vscode", "chat": "default"},
        ],
    )
    fresh = read_events(path, max_age_seconds=60)
    assert len(fresh) == 1
    assert fresh[0].age_seconds < 60


def test_read_events_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_events(tmp_path / "nope.ndjson") == []


def test_read_events_skips_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    path.write_text(
        "{this is not json}\n"
        '{"ts": "not-a-float", "type": "x", "ide": "vscode"}\n'
        '{"ts": 1716406400.0, "type": "message.sent", "ide": "vscode", "chat": "default"}\n',
        encoding="utf-8",
    )
    events = read_events(path)
    assert len(events) >= 1
    assert events[-1].type == "message.sent"


def test_last_event_returns_most_recent(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    now = time.time()
    _write_events(
        path,
        [
            {"ts": now - 5, "type": "message.sent", "ide": "vscode", "chat": "default", "text": "first"},
            {"ts": now - 1, "type": "message.received", "ide": "vscode", "chat": "default", "text": "last"},
        ],
    )
    ev = last_event(path, ide="vscode")
    assert ev is not None
    assert ev.text == "last"


def test_has_recent_activity_true_when_event_within_window(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    now = time.time()
    _write_events(
        path,
        [{"ts": now - 30, "type": "message.sent", "ide": "vscode", "chat": "default"}],
    )
    assert has_recent_activity(path=path, ide="vscode", within_seconds=120) is True


def test_has_recent_activity_false_when_event_too_old(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    now = time.time()
    _write_events(
        path,
        [{"ts": now - 3600, "type": "message.sent", "ide": "vscode", "chat": "default"}],
    )
    assert has_recent_activity(path=path, ide="vscode", within_seconds=60) is False


def test_chat_event_age_seconds_is_non_negative() -> None:
    ev = ChatEvent(ts=time.time() + 1000, type="message.sent", ide="vscode", chat="default")
    assert ev.age_seconds == 0.0
