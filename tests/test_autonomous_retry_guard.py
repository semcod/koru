"""Tests for autonomous retry circuit breaker and real workspace change detection."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

from koru.autonomy.cycle.cycle_common import DiagnosticResult
from koru.autonomy.cycle.cycle_post_drive import _handle_post_drive_verification, _take_pre_drive_snapshot
from koru.autonomy.cycle.cycle_skip_conditions import _check_autopilot_skip_conditions
from koru.autonomy.state import AutoloopState
from koru.autonomy.verification_engine import (
    _workspace_delta,
    drive_budget_exhausted,
    record_unsuccessful_drive,
    reserve_drive_attempt,
    take_snapshot,
)
from koru.queue import QueueLoopResult
from koru.task_model_policy import drive_with_model_policy


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Koru Test"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@koru.dev"], cwd=path, capture_output=True, check=True)


def test_drive_budget_exhausted_persists_across_calls(tmp_path: Path) -> None:
    ticket = "PLF-901"
    assert not drive_budget_exhausted(tmp_path, ticket, limit=3)

    record_unsuccessful_drive(tmp_path, ticket)
    assert not drive_budget_exhausted(tmp_path, ticket, limit=3)

    record_unsuccessful_drive(tmp_path, ticket)
    assert not drive_budget_exhausted(tmp_path, ticket, limit=3)

    record_unsuccessful_drive(tmp_path, ticket)
    assert drive_budget_exhausted(tmp_path, ticket, limit=3)

    # Other tickets remain unexhausted
    assert not drive_budget_exhausted(tmp_path, "PLF-902", limit=3)
    assert not drive_budget_exhausted(tmp_path, "")


def test_drive_budget_fails_closed_on_storage_error(tmp_path: Path) -> None:
    # Point db path to an unreadable directory/file
    db_file = tmp_path / ".planfile" / ".koru" / "drive-budget.sqlite"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    db_file.write_text("not a valid sqlite database", encoding="utf-8")

    assert drive_budget_exhausted(tmp_path, "PLF-903")


def test_workspace_fingerprints_and_delta_on_git_workspace(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)

    # Initial commit
    file_a = tmp_path / "src" / "alpha.py"
    file_a.parent.mkdir(parents=True, exist_ok=True)
    file_a.write_text("print('alpha v1')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)

    snap_before = take_snapshot(tmp_path)
    assert snap_before.workspace_fingerprints is not None
    assert "worktree:src/alpha.py" in snap_before.workspace_fingerprints

    # 1. Untracked file
    file_b = tmp_path / "src" / "beta.py"
    file_b.write_text("print('beta')\n", encoding="utf-8")
    delta_untracked = _workspace_delta(tmp_path, snap_before)
    assert delta_untracked.files_changed == 1

    # 2. Staged file
    subprocess.run(["git", "add", "src/beta.py"], cwd=tmp_path, capture_output=True, check=True)
    delta_staged = _workspace_delta(tmp_path, snap_before)
    assert delta_staged.files_changed == 1

    # 3. Committed delta
    subprocess.run(["git", "commit", "-m", "add beta"], cwd=tmp_path, capture_output=True, check=True)
    delta_committed = _workspace_delta(tmp_path, snap_before)
    assert delta_committed.files_changed == 1

    # 4. Dirty modification
    file_a.write_text("print('alpha v2')\n", encoding="utf-8")
    delta_dirty = _workspace_delta(tmp_path, snap_before)
    assert delta_dirty.files_changed == 2

    # 5. Deletion
    file_b.unlink()
    delta_deleted = _workspace_delta(tmp_path, snap_before)
    assert delta_deleted.files_changed == 2


def test_cycle_skip_conditions_skips_when_drive_budget_exhausted(tmp_path: Path) -> None:
    ticket_id = "PLF-904"
    record_unsuccessful_drive(tmp_path, ticket_id)
    record_unsuccessful_drive(tmp_path, ticket_id)
    record_unsuccessful_drive(tmp_path, ticket_id)

    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[ticket_id],
        last_status="waiting_input",
        last_ticket_id=ticket_id,
    )
    state = AutoloopState()
    telemetry: dict[str, object] = {}

    skip, reason = _check_autopilot_skip_conditions(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="",
        diag_result=DiagnosticResult("ok", False),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lambda _: None,
    )

    assert skip is True
    assert reason == "skipped(drive_budget)"
    assert telemetry.get("autopilot_skipped_drive_budget") is True
    assert telemetry.get("drive_budget_ticket") == ticket_id


def waiting():
    return QueueLoopResult(iterations=1, completed=[], failed=[], waiting=["PLF-099"],
                           last_status="waiting_input", last_ticket_id="PLF-099")


def test_real_shell_policy_stops_before_fourth_call_across_restart(tmp_path):
    drive = Mock(return_value={"ok": True, "client_id": "aider", "provider": "google"})
    for _ in range(3):
        assert drive_with_model_policy(drive, task={"id": "PLF-099"}, project=tmp_path,
                                       client_id="claude-code", execute=True)["ok"]
    # The guard has no in-memory counter to restore. A new process sees the debit.
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-c",
                             "from pathlib import Path; from koru.autonomy.verification_engine import "
                             "drive_budget_exhausted; import sys; "
                             "assert drive_budget_exhausted(Path(sys.argv[1]), 'PLF-099')", str(tmp_path)],
                            capture_output=True, text=True,
                            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                                 "PYTHONDONTWRITEBYTECODE": "1"})
    assert result.returncode == 0, result.stderr
    reply = drive_with_model_policy(drive, task={"id": "PLF-099"}, project=tmp_path,
                                    client_id="claude-code", execute=True)
    assert not reply["ok"] and "drive_budget" in reply["message"]
    assert drive.call_count == 3
    assert not drive_budget_exhausted(tmp_path, "OTHER-1")
    rows = [json.loads(line) for line in (tmp_path / ".planfile/.koru/model-routing.jsonl").read_text().splitlines()]
    assert rows[-1]["status"] == "blocked"
    assert rows[1]["client"] == "claude-code" and rows[1]["actual_client"] == "aider"
    assert rows[1]["actual_provider"] == "google" and rows[1]["actual_model"] == ""


def test_concurrent_reservations_never_admit_more_than_three(tmp_path):
    # Initialize schema first; racing independent connections then serialize CAS.
    assert not drive_budget_exhausted(tmp_path, "PLF-099")
    with ThreadPoolExecutor(max_workers=8) as pool:
        admissions = list(pool.map(lambda _: reserve_drive_attempt(tmp_path, "PLF-099"), range(12)))
    assert sum(admissions) == 3


def test_storage_failure_closes_paid_boundary(tmp_path):
    path = tmp_path / ".planfile/.koru"
    path.mkdir(parents=True)
    (path / "drive-budget.sqlite").write_bytes(b"corrupted SQLite file")
    drive = Mock()
    assert drive_budget_exhausted(tmp_path, "PLF-099")
    reply = drive_with_model_policy(drive, task={"id": "PLF-099"}, project=tmp_path,
                                    client_id="claude-code", execute=True)
    assert not reply["ok"]
    drive.assert_not_called()


def test_failed_verification_vetoes_health_chat_and_limits_llm_ready(tmp_path, monkeypatch):
    import koru.autonomy.cycle.cycle_post_drive as mod
    evaluation, rewrite = Mock(), Mock()
    monkeypatch.setattr(mod, "_llm_evaluate_drive_result", evaluation)
    monkeypatch.setattr(mod, "_llm_generate_better_prompt", rewrite)
    for _ in range(3):
        state = AutoloopState()  # waiting streak and counters reset each time
        state.last_driven_prompt = "Refactor PLF-099"
        state.autopilot_events = [{"type": "message.sent", "timestamp": 9999999999}]
        _take_pre_drive_snapshot(tmp_path, state, None)
        _handle_post_drive_verification(tmp_path, state, 1, waiting(),
                                        "failed(shell_finalize:verify_failed:ruff)",
                                        None, lambda *args: None, lambda *args: None)
        assert state.last_drive_verdict["outcome"] == "degraded"
    assert drive_budget_exhausted(tmp_path, "PLF-099")
    telemetry = {}
    skipped, reason = _check_autopilot_skip_conditions(
        tmp_path, waiting(), AutoloopState(), "drive", False, False, 999, "",
        DiagnosticResult(status="ok", failed=[]), False, telemetry, lambda *args: None,
    )
    assert skipped and reason == "skipped(drive_budget)"
    assert telemetry["autopilot_skipped_drive_budget"]
    evaluation.assert_not_called()
    rewrite.assert_not_called()
    with sqlite3.connect(tmp_path / ".planfile/.koru/drive-budget.sqlite") as db:
        assert db.execute("SELECT count FROM failures WHERE ticket='PLF-099'").fetchone() == (3,)
