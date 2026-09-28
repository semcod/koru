"""Tests for autonomous retry circuit breaker and real workspace change detection."""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

from koru.autonomy.cycle.cycle_common import DiagnosticResult
from koru.autonomy.cycle.cycle_skip_conditions import _check_autopilot_skip_conditions
from koru.autonomy.state import AutoloopState
from koru.autonomy.verification_engine import (
    GitEvidence,
    _workspace_delta,
    _workspace_fingerprints,
    drive_budget_exhausted,
    record_unsuccessful_drive,
    take_snapshot,
)
from koru.queue import QueueLoopResult


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
