from __future__ import annotations

from pathlib import Path

from koru.autonomous_cycle_drive_outcome import apply_autopilot_drive_outcome
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def test_apply_drive_outcome_tracks_submit_failed_status(monkeypatch) -> None:
    import koru.autonomous_cycle_drive_outcome as outcome
    import koru.autonomous_cycle_orchestrator as orchestrator

    state = AutoloopState()
    queue = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-1"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-1",
    )
    monkeypatch.setattr(outcome.time, "time", lambda: 123.0)
    monkeypatch.setattr(outcome, "_log_autopilot_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "_emit_autopilot_observability_outcome", lambda **kwargs: None)

    apply_autopilot_drive_outcome(
        project=Path("/tmp/project"),
        state=state,
        queue_result=queue,
        reply={"ok": False, "delivered": True, "verification": "submit_failed"},
        ok=False,
        decision_kind="ticket_prompt",
        idle_prompt_kind=None,
        autopilot_status="failed(submit_failed)",
        autopilot_ide="cursor",
        cycle=1,
        cycle_telemetry={},
        _hp=lambda *args, **kwargs: None,
    )

    assert state.last_submit_unverified_ts == 123.0
    assert state.last_submit_unverified_ticket_id == "STARTER-1"
