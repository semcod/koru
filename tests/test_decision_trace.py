"""Tests for ``koru.autonomy.decision_trace`` ring buffer + builder."""

from __future__ import annotations

import json
from pathlib import Path

from koru.autonomy.decision_trace import (
    DECISION_TRACE_RING_SIZE,
    DecisionRecord,
    append_decision_record,
    build_decision_record,
    classify_skip_code,
    decision_trace_path,
    human_skip_reason,
    load_recent_decisions,
)


def _record(cycle: int) -> DecisionRecord:
    return DecisionRecord(
        at=f"2026-05-25T13:00:{cycle:02d}+00:00",
        cycle=cycle,
        observed=f"queue=idle streak={cycle}",
        decided="skip:idle_no_ticket",
        action="no_op",
        evidence="diagnostics=skipped",
        next_step="scan",
        skip_code="idle_no_ticket",
        skip_because="queue idle AND zero open planfile tickets",
    )


def test_compact_line_arrow_separated_format() -> None:
    line = _record(1).compact_line()
    assert line.count(" → ") == 4, "compact line must have exactly 4 arrow separators"
    assert line.startswith("observed=queue=idle"), "starts with observed=…"
    assert "decided=skip:idle_no_ticket" in line
    assert line.endswith("next=scan")


def test_ring_buffer_keeps_last_10_decisions(tmp_path: Path) -> None:
    project = tmp_path
    for c in range(1, 15):
        append_decision_record(project, _record(c))
    history = load_recent_decisions(project)
    assert len(history) == DECISION_TRACE_RING_SIZE
    cycles = [item["cycle"] for item in history]
    assert cycles == list(range(5, 15)), "ring buffer must drop oldest entries first"


def test_ring_buffer_persists_through_existing_telemetry(tmp_path: Path) -> None:
    """``recent_decisions`` must coexist with the existing snapshot payload."""
    project = tmp_path
    path = decision_trace_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"updated_at": "x", "cycle": 7, "cumulative": {"a": 1}}),
        encoding="utf-8",
    )
    append_decision_record(project, _record(8))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["cycle"] == 7, "must not clobber existing top-level fields"
    assert payload["cumulative"] == {"a": 1}, "cumulative counters preserved"
    assert len(payload["recent_decisions"]) == 1


def test_ring_buffer_recovers_from_corrupted_file(tmp_path: Path) -> None:
    project = tmp_path
    path = decision_trace_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    append_decision_record(project, _record(1))
    history = load_recent_decisions(project)
    assert len(history) == 1, "corrupt file must not block new appends"


def test_classify_skip_code_orders_upstream_gates_first() -> None:
    telemetry = {
        "autopilot_skipped_plugin_missing": True,
        "autopilot_skipped_chat_activity": True,
        "autopilot_skipped_idle_no_ticket": True,
    }
    assert classify_skip_code(telemetry, "skipped(idle_no_ticket)") == "plugin_missing"


def test_classify_skip_code_parses_inline_status() -> None:
    assert classify_skip_code({}, "skipped(idle_only)") == "idle_only"
    assert classify_skip_code({}, "ok") == "ok"
    assert classify_skip_code({}, "failed") == "failed"
    assert classify_skip_code({}, "") == "unknown"


def test_human_skip_reason_returns_known_descriptions() -> None:
    text = human_skip_reason("plugin_missing")
    assert "VSIX" in text or "plugin" in text.lower()


def test_build_decision_record_idle_no_ticket_uses_explicit_because() -> None:
    record = build_decision_record(
        cycle=10,
        queue_status="idle",
        waiting_ticket="-",
        stagnation_streak=3,
        autopilot_status="skipped(idle_no_ticket)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={"autopilot_skipped_idle_no_ticket": True},
        next_step="scan / reopen done ticket",
    )
    assert record.skip_code == "idle_no_ticket"
    assert "zero open planfile tickets" in record.skip_because
    assert record.decided == "skip:idle_no_ticket"
    assert record.action == "no_op"
    assert "diagnostics=skipped" in record.evidence
    assert "wup=changed" in record.evidence


def test_build_decision_record_successful_drive_records_backend() -> None:
    record = build_decision_record(
        cycle=11,
        queue_status="waiting_input",
        waiting_ticket="STARTER-237",
        stagnation_streak=0,
        autopilot_status="ok",
        autopilot_ide="cursor",
        autopilot_backend="plugin",
        autopilot_drive_kind="ticket_prompt",
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={},
        next_step="wait for IDE response",
    )
    assert record.skip_code == "ok"
    assert record.decided == "ticket_prompt"
    assert record.action == "submit_verified(backend=plugin)"
    assert "backend=plugin" in record.evidence


def test_build_decision_record_chat_activity_includes_last_event() -> None:
    record = build_decision_record(
        cycle=12,
        queue_status="waiting_input",
        waiting_ticket="STARTER-237",
        stagnation_streak=0,
        autopilot_status="skipped(chat_activity)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="ok",
        cycle_telemetry={
            "autopilot_skipped_chat_activity": True,
            "autopilot_chat_activity_last_event": "drive.ack",
        },
        next_step="wait for chat cooldown to expire",
    )
    assert record.skip_code == "chat_activity"
    assert "drive.ack" in record.skip_because
    assert "chat_event=drive.ack" in record.evidence
