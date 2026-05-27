from __future__ import annotations

import json
import time
from pathlib import Path

from koru.autonomous_cycle import _drain_autopilot_events, _handle_autopilot_events
from koru.autonomy.state import AutoloopState


def _append_event(path: Path, payload: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def test_drain_autopilot_events_ignores_stale_events_from_previous_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    path = tmp_path / "koru-autopilot-events.ndjson"
    state = AutoloopState()
    state.autopilot_event_cursor_ts = time.time()
    _append_event(
        path,
        {
            "ts": state.autopilot_event_cursor_ts - 60.0,
            "type": "message.sent",
            "ide": "vscodium",
        },
    )

    assert _drain_autopilot_events(state, autopilot_ide="vscodium") == []
    assert path.read_text(encoding="utf-8") == ""


def test_handle_autopilot_events_logs_only_selected_ide(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    path = tmp_path / "koru-autopilot-events.ndjson"
    state = AutoloopState()
    state.autopilot_event_cursor_ts = time.time() - 1.0
    now = time.time()
    _append_event(path, {"ts": now, "type": "message.sent", "ide": "cursor"})
    _append_event(path, {"ts": now + 0.001, "type": "message.sent", "ide": "vscodium"})
    logs: list[str] = []

    _handle_autopilot_events(state, logs.append, autopilot_ide="vscodium")

    assert logs == ["  event: message.sent ide=vscodium"]
    assert state.autopilot_events == [
        {"ts": now + 0.001, "type": "message.sent", "ide": "vscodium"}
    ]
    assert state.last_message_sent_ide == "vscodium"
