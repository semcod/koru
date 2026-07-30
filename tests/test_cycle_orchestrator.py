"""Tests for koru.autonomy.cycle.cycle_orchestrator.

Targets the pure decision/status functions directly:
- ``_drive_result_autopilot_status``: the core branch logic mapping a raw
  drive reply + decision_kind into the autopilot status string the rest of
  the cycle acts on (this is the function most other cycle modules key off
  of, so its branch coverage matters most).
- ``_plugin_gate_recovery_key``: the cooldown-dedup key builder.

The heavier IDE-plugin-reconnect machinery (``_plugin_gate_status``,
``_attempt_plugin_gate_recovery``, ``_handle_autopilot_phase``) is not
covered here -- it requires deep mocking of live IDE/plugin client state
with low confidence the mocks reflect real plugin behavior.
"""

from __future__ import annotations

from pathlib import Path

from koru.autonomy.cycle.cycle_common import DiagnosticResult
from koru.autonomy.cycle.cycle_orchestrator import (
    _drive_result_autopilot_status,
    _handle_autopilot_phase,
    _plugin_gate_recovery_key,
)
from koru.queue import QueueLoopResult


def _queue_result(**overrides) -> QueueLoopResult:
    defaults = dict(
        iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
    )
    defaults.update(overrides)
    return QueueLoopResult(**defaults)


class TestDriveResultAutopilotStatus:
    def test_idle_no_ticket_decision_kind(self) -> None:
        telemetry: dict = {}
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply={},
            ok=False,
            decision_kind="idle_no_ticket",
            cycle_telemetry=telemetry,
        )
        assert status == "skipped(idle_no_ticket)"
        assert telemetry["autopilot_skipped_idle_no_ticket"] is True

    def test_skipped_idle_no_ticket_decision_kind_normalized(self) -> None:
        telemetry: dict = {}
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply={},
            ok=False,
            decision_kind="skipped(idle_no_ticket)",
            cycle_telemetry=telemetry,
        )
        assert status == "skipped(idle_no_ticket)"

    def test_waiting_ticket_closed_records_ticket_label(self) -> None:
        telemetry: dict = {}
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(waiting=["STARTER-42"]),
            reply={},
            ok=False,
            decision_kind="waiting_ticket_closed",
            cycle_telemetry=telemetry,
        )
        assert status == "skipped(waiting_ticket_closed)"
        assert telemetry["autopilot_skipped_waiting_ticket_closed"] is True
        assert telemetry["autopilot_skipped_waiting_ticket_closed_ticket"] == "STARTER-42"

    def test_successful_drive_returns_ok(self) -> None:
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply={"ok": True},
            ok=True,
            decision_kind=None,
            cycle_telemetry={},
        )
        assert status == "ok"

    def test_manual_focus_required(self) -> None:
        telemetry: dict = {}
        reply = {
            "ok": False,
            "message": "chat input is not focused/open",
            "diagnostics": {"focusOpenCandidates": []},
        }
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply=reply,
            ok=False,
            decision_kind=None,
            cycle_telemetry=telemetry,
        )
        assert status == "skipped(manual_focus)"
        assert telemetry["autopilot_skipped_manual_focus"] is True

    def test_submit_unverified_records_reason_and_legacy_status(self) -> None:
        telemetry: dict = {}
        reply = {
            "ok": False,
            "verification": "submit_unverified",
            "submit_failure_reason": "no ack from plugin",
        }
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply=reply,
            ok=False,
            decision_kind=None,
            cycle_telemetry=telemetry,
        )
        assert status == "failed(submit_unverified)"
        assert telemetry["autopilot_submit_unverified"] is True
        assert telemetry["autopilot_submit_unverified_reason"] == "no ack from plugin"

    def test_plain_failure_returns_failed(self) -> None:
        status = _drive_result_autopilot_status(
            queue_result=_queue_result(),
            reply={"ok": False, "message": "some transport error"},
            ok=False,
            decision_kind=None,
            cycle_telemetry={},
        )
        assert status == "failed"


class TestPluginGateRecoveryKey:
    def test_deterministic_for_same_inputs(self, tmp_path: Path) -> None:
        k1 = _plugin_gate_recovery_key(tmp_path, "VSCode", "Plugin Not Connected")
        k2 = _plugin_gate_recovery_key(tmp_path, "VSCode", "Plugin Not Connected")
        assert k1 == k2

    def test_normalizes_ide_and_reason_case(self, tmp_path: Path) -> None:
        k1 = _plugin_gate_recovery_key(tmp_path, "VSCode", "Plugin Not Connected")
        k2 = _plugin_gate_recovery_key(tmp_path, "vscode", "plugin not connected")
        assert k1 == k2

    def test_different_project_changes_key(self, tmp_path: Path) -> None:
        other = tmp_path / "other"
        other.mkdir()
        k1 = _plugin_gate_recovery_key(tmp_path, "vscode", "reason")
        k2 = _plugin_gate_recovery_key(other, "vscode", "reason")
        assert k1 != k2

    def test_reason_truncated_to_240_chars(self, tmp_path: Path) -> None:
        long_reason = "x" * 500
        key = _plugin_gate_recovery_key(tmp_path, "vscode", long_reason)
        assert len(key[2]) == 240


def test_handle_autopilot_phase_skips_unavailable_agent_before_client_use(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import koru.autonomy.cycle.cycle_orchestrator as orchestrator
    from koru.agent_availability import block_agent

    block_agent("qoder", reason="usage_limit_exhausted")
    emitted: dict[str, object] = {}
    monkeypatch.setattr(
        orchestrator,
        "_emit_autopilot_preflight_skip",
        lambda **kwargs: emitted.update(kwargs),
    )
    telemetry: dict[str, object] = {}
    logs: list[str] = []

    status, backend, drive_kind = _handle_autopilot_phase(
        project=tmp_path,
        state=object(),
        cycle=1,
        queue_result=_queue_result(waiting=["STARTER-1"]),
        enable_autopilot=True,
        client=None,
        autopilot_ide="qoder",
        drive_prompt="work",
        submit=True,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="",
        diag_result=DiagnosticResult(status="ok", failed=[]),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=logs.append,
        _emit=lambda *_args, **_kwargs: None,
    )

    assert (status, backend, drive_kind) == ("skipped(agent_unavailable)", None, None)
    assert telemetry["autopilot_skipped_agent_unavailable"] is True
    assert emitted["blocker"] == "agent_unavailable"
    assert emitted["verification"] == "agent_operational"
