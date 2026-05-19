"""Regression: ``koru autonomous up --emit-events jsonl`` NDJSON envelope."""

from __future__ import annotations

import json
from types import SimpleNamespace

from koru import autonomous as autonomous_mod
from koru.stdio_events import KORU_STDIO_EVENT_SCHEMA_VERSION


def _parse_jsonl(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def test_jsonl_session_emits_versioned_envelope(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=0 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
            iterations=0,
            completed=[],
            failed=[],
            waiting=[],
            last_message="",
            last_ticket_id=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    import io

    buf = io.StringIO()
    monkeypatch.setattr(autonomous_mod.sys, "stdout", buf)

    rc = autonomous_mod.autonomous_main(
        [
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
            "--emit-events",
            "jsonl",
            "--agent-lane",
            "none",
        ],
    )
    assert rc == 0
    events = _parse_jsonl(buf.getvalue())
    types = [e["type"] for e in events]
    assert "SessionStarted" in types
    assert "CycleStarted" in types
    assert "QueueIteration" in types
    assert "DiagnosticsCompleted" in types
    assert "WupHealthChanged" in types
    assert "AutopilotDecision" in types
    assert "CycleCompleted" in types
    assert "AutonomousStopped" in types

    first = events[0]
    for key in ("type", "schema_version", "ts", "correlation_id", "payload"):
        assert key in first
    assert first["schema_version"] == KORU_STDIO_EVENT_SCHEMA_VERSION
    assert first["correlation_id"]


def test_default_stdio_format_from_env_jsonl(monkeypatch) -> None:
    from koru import stdio_events

    monkeypatch.setenv("KORU_STDIO_FORMAT", "jsonl")
    assert stdio_events.default_stdio_format_from_env() == "jsonl"
    monkeypatch.setenv("KORU_STDIO_FORMAT", "bogus")
    assert stdio_events.default_stdio_format_from_env() == "human"


def test_stdio_event_schema_version_constant() -> None:
    from koru.stdio_events import KORU_STDIO_EVENT_SCHEMA_VERSION

    assert KORU_STDIO_EVENT_SCHEMA_VERSION == "1.0"
