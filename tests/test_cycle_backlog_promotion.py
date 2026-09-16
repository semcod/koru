"""Backlog promotion runs on every idle queue, before opt-in idle discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomy.cycle import cycle as cycle_mod
from koru.autonomy.phases.contexts import CyclePhaseContext, PhaseCallbacks, QueueScanPhaseConfig
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def _config(*, scan_after_idle_queue: bool) -> QueueScanPhaseConfig:
    return QueueScanPhaseConfig(
        actor="koru",
        queue_name=None,
        enable_scan=True,
        max_iterations=1,
        include_semcod_artifacts=None,
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="normal",
        diagnostic_state_dir=None,
        wup_watch_enabled=False,
        wup_diagnostic_tickets=False,
        wup_ticket_queue="default",
        scan_skip_if_clean=False,
        scan_skip_after=0,
        scan_after_idle_queue=scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=0.0,
        topology_integration=False,
    )


@pytest.mark.parametrize(
    ("promotion", "scan_after_idle_queue", "idle_scan_called"),
    [
        ({"applied": ["PLF-1"]}, True, False),
        ({"applied": []}, True, True),
        (None, True, True),
        ({"applied": ["PLF-1"]}, False, False),
    ],
)
def test_pre_drive_promotes_backlog_before_idle_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    promotion: dict | None,
    scan_after_idle_queue: bool,
    idle_scan_called: bool,
) -> None:
    calls: list[str] = []
    queue = QueueLoopResult(iterations=1, completed=[], failed=[], waiting=[], last_status="idle")
    monkeypatch.setattr(cycle_mod._queue_phase, "handle_queue_hygiene", lambda *a: None)
    monkeypatch.setattr(cycle_mod, "_handle_post_run_verify_ide", lambda *a: None)
    monkeypatch.setattr(cycle_mod, "_handle_scan_phase", lambda *a: None)
    monkeypatch.setattr(cycle_mod, "_handle_queue_loop_phase", lambda *a: (queue, None))
    monkeypatch.setattr(cycle_mod, "_update_stagnation_state", lambda *a: None)
    monkeypatch.setattr(cycle_mod, "_escalate_error_stagnation", lambda *a: None)
    monkeypatch.setattr(cycle_mod, "_handle_diagnostics", lambda *a: ("diag", "wup"))

    def promote(project, state, queue_result, telemetry, hp, emit):
        assert queue_result is queue
        calls.append("promote")
        return promotion

    def idle_scan(project, state, cycle, queue_result, enabled, *rest):
        assert enabled is scan_after_idle_queue
        calls.append("idle_scan")

    monkeypatch.setattr(cycle_mod, "_handle_backlog_promotion_after_idle", promote)
    monkeypatch.setattr(cycle_mod, "_handle_scan_after_idle", idle_scan)
    context = CyclePhaseContext(
        project=tmp_path,
        state=AutoloopState(),
        cycle=1,
        callbacks=PhaseCallbacks(hp=lambda *a: None, emit=lambda *a, **k: None),
    )

    result = cycle_mod._run_pre_drive_cycle_phases(
        context,
        _config(scan_after_idle_queue=scan_after_idle_queue),
        cycle_telemetry={},
    )

    assert calls == (["promote", "idle_scan"] if idle_scan_called else ["promote"])
    assert result.queue_result is queue
