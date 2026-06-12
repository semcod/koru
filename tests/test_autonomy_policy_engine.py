from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import DiagnosticResult
from koru.autonomy.policy_engine import AutopilotPolicyContext, decide_autopilot_policy
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def _context() -> AutopilotPolicyContext:
    return AutopilotPolicyContext(
        project=Path("/tmp/project"),
        queue_result=QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
        ),
        state=AutoloopState(),
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        diag_result=DiagnosticResult(status="ok", failed=[]),
        topology_integration=True,
        cycle_telemetry={},
        human_log=lambda *args, **kwargs: None,
    )


def test_policy_engine_returns_proceed(monkeypatch: Any) -> None:
    import koru.autonomy.policy_engine as policy_engine

    monkeypatch.setattr(
        policy_engine,
        "_check_autopilot_skip_conditions",
        lambda *args, **kwargs: (False, ""),
    )

    decision = decide_autopilot_policy(_context())

    assert decision.should_skip is False
    assert decision.status == ""


def test_policy_engine_wraps_legacy_skip_status(monkeypatch: Any) -> None:
    import koru.autonomy.policy_engine as policy_engine

    monkeypatch.setattr(
        policy_engine,
        "_check_autopilot_skip_conditions",
        lambda *args, **kwargs: (True, "skipped(chat_activity)"),
    )

    decision = decide_autopilot_policy(_context())

    assert decision.should_skip is True
    assert decision.status == "skipped(chat_activity)"
    assert decision.reason_code == "chat_activity"
