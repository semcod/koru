"""REPAIR_RUN handler uses real lane repair runtime."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from coru.repair.domain import RepairAttempt, RepairPlan, RepairProblem
from dsl2koru.bus import dispatch


def test_repair_run_delegates_to_runtime(monkeypatch, tmp_path: Path) -> None:
    plan = RepairPlan(
        session_id="sess-1",
        problems=(RepairProblem(code="daemon_not_running", severity="error", message="down"),),
        attempts=(RepairAttempt(action_id="ensure_daemon", mode="auto", ok=True, message="ok"),),
        resolved=True,
        trigger="dsl2koru",
    )
    mock_run = MagicMock(return_value=plan)
    monkeypatch.setattr("coru.repair.runtime.run_lane_repair", mock_run)

    result = dispatch(
        "REPAIR_RUN IDE cursor INSTANCE cursor-main PROJECT .",
        default_project=str(tmp_path),
        project_root=tmp_path,
    )

    mock_run.assert_called_once()
    assert result.ok is True
    assert result.verb == "REPAIR_RUN"
    assert result.data["session_id"] == "sess-1"
    assert result.data["resolved"] is True
    assert "ensure_daemon" in result.data["attempts"]
