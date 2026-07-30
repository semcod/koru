"""Autopilot event-drain and socket helpers for the autonomous cycle.

Extracted verbatim from ``koru.autonomy.cycle.cycle`` (STARTER-545). The legacy
``_underscored`` names remain importable from ``koru.autonomy.cycle.cycle`` via
``import as`` re-exports so existing tests/callers keep working unchanged.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from koru.autonomy.state import AutoloopState


def _autopilot_event_path() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "koru-autopilot-events.ndjson"


def _coerce_event_ts(event: dict[str, Any]) -> float | None:
    try:
        return float(event.get("ts"))
    except (TypeError, ValueError):
        return None


def _drain_autopilot_events(
    state: AutoloopState,
    *,
    autopilot_ide: str | None = None,
) -> list[dict[str, Any]]:
    path = _autopilot_event_path()
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    events: list[dict[str, Any]] = []
    cursor_ts = float(getattr(state, "autopilot_event_cursor_ts", 0.0) or 0.0)
    max_seen_ts = cursor_ts
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_ts = _coerce_event_ts(event)
        if event_ts is None:
            continue
        max_seen_ts = max(max_seen_ts, event_ts)
        if event_ts < cursor_ts:
            continue
        if autopilot_ide and str(event.get("ide") or "") != autopilot_ide:
            continue
        events.append(event)
    if raw.strip():
        path.write_text("", encoding="utf-8")
    if max_seen_ts > cursor_ts:
        state.autopilot_event_cursor_ts = max_seen_ts
    return events


def _heal_stale_socket() -> None:
    """Auto-heal: remove only orphan socket files (not the active daemon's socket)."""
    try:
        import sys

        from koru.autopilot import default_socket_path
        from koru.ide_adapters.bridge import gc_stale_sockets_for_lane
        target = default_socket_path()
        for removed in gc_stale_sockets_for_lane(target):
            print(f"koru autonomous: auto-healed stale socket {removed}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — healing is best-effort, but say it failed
        print(f"koru autonomous: stale-socket GC failed: {exc}", file=sys.stderr)


def _handle_autopilot_events(
    state: AutoloopState,
    _hp: callable,
    *,
    autopilot_ide: str | None = None,
) -> None:
    from koru import autonomous_cycle as _cycle_mod

    events = _cycle_mod._drain_autopilot_events(state, autopilot_ide=autopilot_ide)
    if events:
        for ev in events:
            ev_type = ev.get("type", "unknown")
            _hp(f"  event: {ev_type} ide={ev.get('ide', '?')}")
        state.autopilot_events.extend(events)
        if len(state.autopilot_events) > 500:
            state.autopilot_events = state.autopilot_events[-500:]
        for ev in events:
            if ev.get("type") == "message.sent":
                try:
                    state.last_message_sent_ts = float(ev.get("ts") or time.time())
                except (TypeError, ValueError):
                    state.last_message_sent_ts = time.time()
                state.last_message_sent_ide = str(ev.get("ide") or "")
        if autopilot_ide:
            try:
                from koru.agent_availability import learn_unavailability_from_events

                unavailable = learn_unavailability_from_events(autopilot_ide, events)
            except OSError as exc:
                _hp(f"  agent availability registry write failed: {exc}")
            else:
                if unavailable is not None:
                    _hp(
                        "  agent unavailable learned from response: "
                        f"ide={unavailable.agent_id} reason={unavailable.reason}; "
                        "future drives are blocked"
                    )


def _cycle_socket_path(client: Any) -> Path | None:
    raw = (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    if raw:
        return Path(raw).expanduser()
    if client is not None:
        raw_path = getattr(client, "socket_path", None)
        if raw_path is not None:
            return Path(raw_path)
    return None
