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
        evidence="blocked_by=idle_no_ticket, diagnostics=skipped",
        next_step="scan",
        blocked_by="idle_no_ticket",
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
        "autopilot_skipped_plugin_blocker": "plugin_not_connected",
        "autopilot_skipped_chat_activity": True,
        "autopilot_skipped_idle_no_ticket": True,
    }
    assert classify_skip_code(telemetry, "skipped(idle_no_ticket)") == "plugin_not_connected"


def test_classify_skip_code_parses_inline_status() -> None:
    assert classify_skip_code({}, "skipped(idle_only)") == "idle_only"
    assert classify_skip_code({}, "skipped(waiting_ticket_closed)") == "waiting_ticket_closed"
    assert classify_skip_code({}, "ok") == "ok"
    assert classify_skip_code({}, "failed") == "failed"
    assert classify_skip_code({}, "") == "unknown"


def test_classify_skip_code_prefers_waiting_ticket_closed_telemetry() -> None:
    telemetry = {
        "autopilot_skipped_waiting_ticket_closed": True,
        "autopilot_skipped_waiting_ticket_closed_ticket": "STARTER-239",
    }
    assert (
        classify_skip_code(telemetry, "skipped(idle_only)")
        == "waiting_ticket_closed"
    )


def test_classify_skip_code_submit_unverified_requires_manual_send() -> None:
    assert (
        classify_skip_code({"autopilot_submit_unverified": True}, "failed")
        == "manual_send_required"
    )


def test_human_skip_reason_returns_known_descriptions() -> None:
    text = human_skip_reason("plugin_missing")
    assert "VSIX" in text or "plugin" in text.lower()


def test_build_decision_record_plugin_version_mismatch_uses_precise_blocker() -> None:
    record = build_decision_record(
        cycle=9,
        queue_status="waiting_input",
        waiting_ticket="STARTER-215",
        stagnation_streak=0,
        autopilot_status="skipped(plugin_version_mismatch)",
        autopilot_ide="vscodium",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_plugin_missing": True,
            "autopilot_skipped_plugin_blocker": "plugin_version_mismatch",
            "autopilot_skipped_plugin_missing_reason": (
                "connected autopilot plugin version mismatch: "
                "connected=0.1.63 expected=0.1.64"
            ),
        },
        next_step="reload plugin",
    )
    assert record.skip_code == "plugin_version_mismatch"
    assert record.blocked_by == "plugin_version_mismatch"
    assert "connected=0.1.63" in record.skip_because
    assert "plugin_reason=connected autopilot plugin version mismatch" in record.evidence


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
    assert record.blocked_by == "idle_no_ticket"
    assert "blocked_by=idle_no_ticket" in record.evidence
    assert "diagnostics=skipped" in record.evidence
    assert "wup=changed" in record.evidence


def test_build_decision_record_submit_unverified_does_not_plan_retry() -> None:
    record = build_decision_record(
        cycle=11,
        queue_status="waiting_input",
        waiting_ticket="STARTER-298",
        stagnation_streak=0,
        autopilot_status="failed",
        autopilot_ide="vscodium",
        autopilot_backend="plugin",
        autopilot_drive_kind="ticket_prompt",
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_submit_unverified": True,
            "autopilot_submit_unverified_reason": "input still contains pasted text",
        },
        next_step="manual send required; validate submit trace before any redrive",
    )
    assert record.skip_code == "manual_send_required"
    assert record.blocked_by == "manual_send_required"
    assert record.decided == "manual_send_required"
    assert record.action == "submit_unverified"
    assert "input still contains pasted text" in record.skip_because
    assert "blocked_by=manual_send_required" in record.evidence
    assert "retry next cycle" not in record.compact_line()


def test_build_decision_record_waiting_ticket_closed_uses_explicit_because() -> None:
    record = build_decision_record(
        cycle=10,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=1,
        autopilot_status="skipped(waiting_ticket_closed)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_waiting_ticket_closed": True,
            "autopilot_skipped_waiting_ticket_closed_ticket": "STARTER-239",
        },
        next_step="pick next open ticket",
    )
    assert record.skip_code == "waiting_ticket_closed"
    assert "ticket=STARTER-239" in record.skip_because
    assert record.decided == "skip:waiting_ticket_closed"
    assert record.action == "no_op"


def test_build_decision_record_waiting_ticket_closed_from_orchestrator_payload() -> None:
    """Telemetry-first mapping must stay stable for orchestrator payloads."""
    record = build_decision_record(
        cycle=611,
        queue_status="waiting_input",
        waiting_ticket="-",
        stagnation_streak=2,
        autopilot_status="skipped(waiting_ticket_closed)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind="waiting_ticket_closed",
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_waiting_ticket_closed": True,
            "autopilot_skipped_waiting_ticket_closed_ticket": "STARTER-239",
        },
        next_step="refresh queue snapshot",
    )
    assert record.skip_code == "waiting_ticket_closed"
    assert record.blocked_by == "waiting_ticket_closed"
    assert record.decided == "skip:waiting_ticket_closed"
    assert record.action == "no_op"
    assert "ticket=STARTER-239" in record.skip_because
    assert "blocked_by=waiting_ticket_closed" in record.evidence
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
    assert record.blocked_by == ""
    assert record.decided == "ticket_prompt"
    assert record.action == "submit_verified(backend=plugin)"
    assert "backend=plugin" in record.evidence


def test_build_decision_record_stuck_waiting_input_has_full_reason() -> None:
    """Regression: ``stuck_waiting_input`` skip path was hitting ``unknown``."""
    record = build_decision_record(
        cycle=628,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=1,
        autopilot_status="skipped(stuck_waiting_input)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_stuck_status": True,
            "autopilot_skipped_stuck_status_queue": "waiting_input",
            "autopilot_skipped_stuck_status_streak": 1,
        },
        next_step="mark ticket llm-ready OR move it to input/done before next drive",
    )
    assert record.skip_code == "stuck_waiting_input"
    assert "STARTER-239" in record.skip_because
    assert "streak=1" in record.skip_because
    assert human_skip_reason(record.skip_code) != record.skip_code, (
        "stuck_waiting_input must have a populated human description"
    )


def test_build_decision_record_diagnostics_fail_names_failing_services() -> None:
    """Regression: cycle #633 logged ``because[diagnostics_fail]`` with the
    generic SKIP_CODE_DESCRIPTIONS line and an empty ``skip_because`` —
    the operator couldn't tell *which* WUP/diagnostic check broke or that
    a diag ticket was already created. The builder must surface the
    failing services from telemetry and tell the operator the three
    concrete unblock paths.
    """
    record = build_decision_record(
        cycle=633,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=2,
        autopilot_status="skipped(diagnostics_fail)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="failed",
        wup_status="failed",
        cycle_telemetry={
            "autopilot_skipped_diagnostics_fail": True,
            "autopilot_skipped_diagnostics_failed_services": ["wup", "koru-shell"],
        },
        next_step="fix failing WUP/diagnostics",
    )
    assert record.skip_code == "diagnostics_fail"
    assert "wup" in record.skip_because
    assert "koru-shell" in record.skip_because
    assert "--no-autopilot-skip-on-diagnostics-fail" in record.skip_because


def test_build_decision_record_diagnostics_fail_without_services_uses_generic_because() -> None:
    record = build_decision_record(
        cycle=634,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=3,
        autopilot_status="skipped(diagnostics_fail)",
        autopilot_ide="cursor",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="failed",
        wup_status="failed",
        cycle_telemetry={"autopilot_skipped_diagnostics_fail": True},
        next_step="rerun with --no-autopilot-skip-on-diagnostics-fail",
    )
    assert record.skip_code == "diagnostics_fail"
    assert record.skip_because, "diagnostics_fail must always populate skip_because"
    assert "--no-autopilot-skip-on-diagnostics-fail" in record.skip_because


def test_classify_skip_code_falls_back_to_stuck_status_for_inline_form() -> None:
    """When telemetry flags weren't set but status string says ``stuck_*``."""
    assert classify_skip_code({}, "skipped(stuck_waiting_input)") == "stuck_waiting_input"
    assert classify_skip_code({}, "skipped(stuck_completed)") == "stuck_status"


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
    assert record.blocked_by == "chat_activity"
    assert "drive.ack" in record.skip_because
    assert "blocked_by=chat_activity" in record.evidence
    assert "chat_event=drive.ack" in record.evidence


def test_build_decision_record_chat_activity_prefers_telemetry_because() -> None:
    record = build_decision_record(
        cycle=13,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=0,
        autopilot_status="skipped(chat_activity)",
        autopilot_ide="vscode",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_chat_activity": True,
            "autopilot_chat_activity_last_event": "message.sent",
            "autopilot_skipped_chat_activity_because": (
                "recent_chat_activity last=message.sent age=12s cooldown=300s "
                "ticket=STARTER-239"
            ),
        },
        next_step="wait",
    )
    assert record.skip_because.startswith("recent_chat_activity")


def test_build_decision_record_plugin_missing_uses_detailed_reason() -> None:
    record = build_decision_record(
        cycle=14,
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        stagnation_streak=5,
        autopilot_status="skipped(plugin_missing)",
        autopilot_ide="vscode",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        diag_status="skipped",
        wup_status="changed",
        cycle_telemetry={
            "autopilot_skipped_plugin_missing": True,
            "autopilot_skipped_plugin_missing_reason": "daemon status plugin list is empty",
        },
        next_step="reload plugin",
    )
    assert record.skip_because == "daemon status plugin list is empty"
    assert "plugin_reason=daemon status plugin list is empty" in record.evidence
