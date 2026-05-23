"""Regression: autopilot must not redrive a ticket while the IDE chat is busy.

Reproducer (from production log, terminal 8):

* cycle 351 → ``CHAT drive → ide=vscode (236 znaków)`` for STARTER-184
* cycle 352 (60 s later) → exact same prompt re-sent, even though the
  plugin emitted ``message.sent`` for the same ticket and the IDE-side LLM
  was still typing its answer.

The cooldown reads the daemon's shared NDJSON event file and skips drive
when a recent ``message.sent`` / ``message.received`` exists for the same
IDE within :func:`_autopilot_redrive_cooldown_seconds`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from koru.autonomous_cycle import (
    _autopilot_redrive_cooldown_seconds,
    _skip_due_to_recent_chat_activity,
)


_EVENTS_FILENAME = "koru-autopilot-events.ndjson"


def _events_path(tmp_path: Path) -> Path:
    return tmp_path / _EVENTS_FILENAME


def _write_event(path: Path, ts_offset: float, type_: str, ide: str = "vscode") -> None:
    payload = {
        "ts": time.time() + ts_offset,
        "type": type_,
        "ide": ide,
        "chat": "default",
        "text": "drive",
        "length": 5,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


class _FakeQueue:
    def __init__(self, ticket: str = "STARTER-184") -> None:
        self.last_status = "waiting_input"
        self.last_message = "Architektura: wprowadź CQRS"
        self.last_ticket_id = ticket
        self.waiting_ticket_id = ticket


def test_cooldown_default_is_5_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", raising=False)
    assert _autopilot_redrive_cooldown_seconds() == pytest.approx(300.0)


def test_cooldown_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "45")
    assert _autopilot_redrive_cooldown_seconds() == pytest.approx(45.0)


def test_cooldown_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "0")
    assert _autopilot_redrive_cooldown_seconds() == 0.0


def test_cooldown_invalid_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "not-a-number")
    assert _autopilot_redrive_cooldown_seconds() == pytest.approx(300.0)


def test_skip_when_recent_message_sent_for_same_ide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events_path = _events_path(tmp_path)
    _write_event(events_path, ts_offset=-20.0, type_="message.sent", ide="vscode")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "300")

    state = mock.Mock()
    state.stagnation_streak = 1
    telemetry: dict[str, Any] = {}
    logs: list[str] = []

    skipped = _skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=_FakeQueue(),
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )
    assert skipped is True
    assert telemetry.get("autopilot_skipped_chat_activity") is True
    assert telemetry.get("autopilot_chat_activity_last_event") == "message.sent"
    assert any("recent_chat_activity" in line for line in logs), logs


def test_no_skip_when_events_are_old(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_path = _events_path(tmp_path)
    _write_event(events_path, ts_offset=-3600.0, type_="message.sent", ide="vscode")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "120")

    state = mock.Mock()
    state.stagnation_streak = 1

    skipped = _skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=_FakeQueue(),
        state=state,
        cycle_telemetry={},
        _hp=lambda _msg: None,
    )
    assert skipped is False


def test_no_skip_when_cooldown_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_path = _events_path(tmp_path)
    _write_event(events_path, ts_offset=-5.0, type_="message.sent", ide="vscode")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "0")

    state = mock.Mock()
    state.stagnation_streak = 1

    skipped = _skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=_FakeQueue(),
        state=state,
        cycle_telemetry={},
        _hp=lambda _msg: None,
    )
    assert skipped is False


def test_no_skip_for_different_ide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_path = _events_path(tmp_path)
    _write_event(events_path, ts_offset=-5.0, type_="message.sent", ide="cursor")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "300")

    state = mock.Mock()
    state.stagnation_streak = 1

    skipped = _skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=_FakeQueue(),
        state=state,
        cycle_telemetry={},
        _hp=lambda _msg: None,
    )
    assert skipped is False


def test_llx_reflection_done_keeps_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If llx reflect reports ``done=True``, the loop should still skip redrive."""
    events_path = _events_path(tmp_path)
    _write_event(events_path, ts_offset=-10.0, type_="message.received", ide="vscode")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "300")
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")

    from koru import llm_reflect as lr

    monkeypatch.setattr(lr, "shutil", mock.Mock(which=lambda _n: "/usr/bin/llx"))
    monkeypatch.setattr(
        lr,
        "reflect_on_chat",
        lambda **_k: lr.ReflectionResult(
            done=True, needs_input=False, summary="patch landed", raw=""
        ),
    )

    state = mock.Mock()
    state.stagnation_streak = 1
    state.last_driven_prompt = "Wprowadź CQRS"
    telemetry: dict[str, Any] = {}

    skipped = _skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=_FakeQueue(),
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )
    assert skipped is True
    assert telemetry.get("autopilot_llx_reflection", {}).get("done") is True
