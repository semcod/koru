"""Inner queue denial must survive the outer agent fallback boundary."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from koru.autonomy.cycle import cycle_skip_conditions as skip
from koru.autonomy.state import AutoloopState
from koru.queue.loop import run_planfile_queue_loop
from koru.queue.types import QueueLoopResult


def decision(project: Path, result: QueueLoopResult, streak: int = 0):
    state = AutoloopState()
    state.stagnation_streak = streak
    return skip._check_autopilot_skip_conditions(
        project=project, queue_result=result, state=state,
        autopilot_action="drive", autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0, autopilot_skip_statuses="waiting_input",
        diag_result=SimpleNamespace(status="skipped"), topology_integration=False,
        cycle_telemetry={}, _hp=lambda _line: None,
    )


@pytest.mark.parametrize("streak", [0, 1, 100])
def test_real_queue_denial_blocks_outer_drive(tmp_path, monkeypatch, streak):
    ticket = {
        "id": "SBX-001", "name": "Reduce duplication",
        "labels": ["jscpd", "duplication", "llm-ready"],
        "files": [".jscpd/jscpd-report.json"],
        "executor": {"kind": "llm", "mode": "interactive"},
        "inputs": {"prompt": "refactor duplicate code"},
    }
    monkeypatch.setattr("koru.queue.runner._next_ticket_or_result", lambda *a, **k: (ticket, None))
    native = Mock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    execute = Mock(side_effect=AssertionError("executor must not be invoked"))
    result = run_planfile_queue_loop(
        project=tmp_path, max_iterations=1, planfile_runner=native,
        shell_runner=execute, api_runner=execute, llm_runner=execute,
        prompt_runner=execute,
    )
    assert result.last_status == "waiting_input"
    assert result.waiting == ["SBX-001"]
    assert result.completed == []
    assert result.autopilot_blocked
    commands = [c.args[0] for c in native.call_args_list]
    assert any("block" in c for c in commands)
    assert not any(op in c for c in commands for op in ("claim", "start", "done"))
    # Neither automatic llm-ready promotion nor cooldown may override denial.
    promotion = Mock(side_effect=AssertionError("must not promote denied ticket"))
    monkeypatch.setattr(skip, "_autopromote_waiting_ticket_llm_ready", promotion)
    assert decision(tmp_path, result, streak) == (True, "skipped(queue_admission)")
    execute.assert_not_called()
    promotion.assert_not_called()


@pytest.mark.parametrize("status", [
    "infrastructure_error", "planfile_error", "unsupported_executor", "claim_failed", "dry_run",
])
@pytest.mark.parametrize("streak", [0, 100])
def test_outer_drive_cannot_bypass_queue_failures(tmp_path, status, streak):
    result = QueueLoopResult(1, [], [], [], status, last_ticket_id="SBX-001")
    assert decision(tmp_path, result, streak) == (True, "skipped(queue_admission)")


def test_ordinary_interactive_waiting_still_allows_agent(tmp_path):
    result = QueueLoopResult(1, [], [], ["SBX-001"], "waiting_input", last_ticket_id="SBX-001")
    assert decision(tmp_path, result) == (False, "")
