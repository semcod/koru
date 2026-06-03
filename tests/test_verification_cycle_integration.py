"""Integration tests: verification engine hooked into autonomous cycle."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koru.autonomy.state import AutoloopState
from koru.autonomy.verification_engine import Snapshot
from koru.autonomous_cycle import (
    _handle_post_drive_verification,
    _take_pre_drive_snapshot,
)
from koru.autonomous_wup import WupHealthResult
from koru.queue import QueueLoopResult

# These tests use subprocess and are slow; skip by default
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queue_result(
    *,
    last_status: str = "idle",
    waiting: list[str] | None = None,
) -> QueueLoopResult:
    return QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=waiting or [],
        last_status=last_status,
        last_message="",
    )


def _make_wup_health(status: str = "ok") -> WupHealthResult:
    return WupHealthResult(status=status, failing_services=[], new_events=0)


def _fake_git_head(project, **kw):
    return subprocess.CompletedProcess([], 0, stdout="abc123\n", stderr="")


def _fake_git_status(project, **kw):
    return subprocess.CompletedProcess([], 0, stdout="", stderr="")


def _fake_git_diff_stat(project, **kw):
    return subprocess.CompletedProcess(
        [], 0,
        stdout=" foo.py | 10 +++\n 1 file changed, 10 insertions(+)\n",
        stderr="",
    )


def _fake_git_diff_no_change(project, **kw):
    return subprocess.CompletedProcess([], 0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# _take_pre_drive_snapshot
# ---------------------------------------------------------------------------


class TestTakePreDriveSnapshot:
    def test_captures_snapshot(self, tmp_path: Path):
        state = AutoloopState()
        wup = _make_wup_health("ok")
        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            side_effect=[_fake_git_head(tmp_path), _fake_git_status(tmp_path)],
        ):
            _take_pre_drive_snapshot(tmp_path, state, wup)
        assert state.last_drive_snapshot["git_head"] == "abc123"
        assert state.last_drive_snapshot["test_status"] == "ok"
        assert state.last_drive_snapshot["timestamp"] > 0

    def test_stores_wup_status_in_snapshot(self, tmp_path: Path):
        state = AutoloopState()
        wup = _make_wup_health("failing")
        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            side_effect=[_fake_git_head(tmp_path), _fake_git_status(tmp_path)],
        ):
            _take_pre_drive_snapshot(tmp_path, state, wup)
        assert state.last_drive_snapshot["test_status"] == "failing"


# ---------------------------------------------------------------------------
# _handle_post_drive_verification
# ---------------------------------------------------------------------------


class TestHandlePostDriveVerification:
    def test_skips_when_autopilot_skipped(self, tmp_path: Path):
        state = AutoloopState()
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result()
        _handle_post_drive_verification(
            tmp_path, state, 1, qr, "skipped", _make_wup_health(), hp, emit,
        )
        hp.assert_not_called()
        emit.assert_not_called()
        assert state.last_drive_verdict == {}

    def test_collects_verdict_on_ok_drive(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {
            "git_head": "abc123",
            "git_dirty_count": 0,
            "test_status": "ok",
            "timestamp": 100.0,
        }
        state.last_message_sent_ts = 100.0
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        def fake_run(cmd, **kw):
            if "diff" in cmd:
                return _fake_git_diff_stat(tmp_path)
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            side_effect=fake_run,
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "ok", _make_wup_health("ok"), hp, emit,
            )

        assert state.last_drive_verdict["outcome"] in {
            "completed", "in_progress", "no_change",
            "submitted_but_no_effect", "degraded", "unknown",
        }
        assert state.last_drive_verdict["confidence"] >= 0.0
        assert hp.call_count == 2
        assert "verdict:" in hp.call_args_list[0][0][0]
        assert "decision:" in hp.call_args_list[1][0][0]
        assert emit.call_count == 2
        assert emit.call_args_list[0][0][0] == "DriveVerdict"
        assert emit.call_args_list[1][0][0] == "ActionPlan"

    def test_tracks_per_ticket_drive_count(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {"git_head": "", "git_dirty_count": 0, "test_status": "unknown", "timestamp": 0}
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "ok", _make_wup_health(), hp, emit,
            )
            assert state.drive_count_for_ticket == 1
            assert state.last_driven_ticket_for_count == "T-1"

            _handle_post_drive_verification(
                tmp_path, state, 2, qr, "ok", _make_wup_health(), hp, emit,
            )
            assert state.drive_count_for_ticket == 2

        # Different ticket resets count
        qr2 = _make_queue_result(last_status="waiting_input", waiting=["T-2"])
        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 3, qr2, "ok", _make_wup_health(), hp, emit,
            )
            assert state.drive_count_for_ticket == 1
            assert state.last_driven_ticket_for_count == "T-2"

    def test_failed_drive_also_generates_verdict(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {"git_head": "", "git_dirty_count": 0, "test_status": "unknown", "timestamp": 0}
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "failed", _make_wup_health(), hp, emit,
            )

        assert state.last_drive_verdict != {}
        assert emit.call_count == 2
        verdict_payload = emit.call_args_list[0][0][1]
        assert verdict_payload["autopilot_status"] == "failed"
        plan_payload = emit.call_args_list[1][0][1]
        assert plan_payload["action"] in {
            "drive_ticket", "redrive_improved", "close_ticket",
            "escalate_ticket", "switch_ticket", "run_discovery",
            "wait", "reflect", "noop",
        }

    def test_message_sent_without_local_effect_is_explicit_verdict(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {
            "git_head": "abc", "git_dirty_count": 0, "test_status": "ok", "timestamp": 100,
        }
        state.last_message_sent_ts = 100.0
        state.autopilot_events = [{"type": "message.sent", "ts": 101.0, "ide": "vscodium"}]
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "ok", _make_wup_health("ok"), hp, emit,
            )

        assert state.last_drive_verdict["outcome"] == "submitted_but_no_effect"
        assert state.last_drive_verdict["confidence"] == 0.95
        assert state.last_drive_action_plan["action"] == "escalate_ticket"
        assert "prompt was submitted but no local work was applied" in state.last_drive_action_plan["reason"]
        event_names = [call.args[0] for call in emit.call_args_list]
        assert event_names == ["DriveEffect", "DriveVerdict", "ActionPlan"]
        effect_payload = emit.call_args_list[0].args[1]
        assert effect_payload["prompt_submitted"] is True
        assert effect_payload["work_applied"] is False
        assert effect_payload["planfile_delta"] == "still_waiting_input"
        assert any("drive_effect: submitted_but_no_effect" in call.args[0] for call in hp.call_args_list)


# ---------------------------------------------------------------------------
# AutoloopState new fields
# ---------------------------------------------------------------------------


class TestDecisionArbiterInCycle:
    def test_produces_action_plan_on_ok_drive(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {
            "git_head": "", "git_dirty_count": 0,
            "test_status": "ok", "timestamp": 0,
        }
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "ok", _make_wup_health("ok"), hp, emit,
            )

        assert state.last_drive_action_plan != {}
        assert state.last_drive_action_plan["action"] in {
            "drive_ticket", "redrive_improved", "close_ticket",
            "escalate_ticket", "switch_ticket", "run_discovery",
            "wait", "reflect", "noop",
        }
        plan_event = emit.call_args_list[1]
        assert plan_event[0][0] == "ActionPlan"
        assert plan_event[0][1]["cycle"] == 1

    def test_escalates_after_many_no_change_drives(self, tmp_path: Path):
        state = AutoloopState()
        # Use unknown test status so score stays < 0.3 → verdict = no_change
        state.last_drive_snapshot = {
            "git_head": "abc", "git_dirty_count": 0,
            "test_status": "unknown", "timestamp": 0,
        }
        state.last_driven_ticket_for_count = "T-1"
        state.drive_count_for_ticket = 2  # will become 3 after this call
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 3, qr, "ok", _make_wup_health("unknown"), hp, emit,
            )

        assert state.drive_count_for_ticket == 3
        assert state.last_drive_action_plan["action"] == "escalate_ticket"
        assert "no change" in state.last_drive_action_plan["reason"]

    def test_waits_on_failing_tests(self, tmp_path: Path):
        state = AutoloopState()
        state.last_drive_snapshot = {
            "git_head": "", "git_dirty_count": 0,
            "test_status": "failing", "timestamp": 0,
        }
        hp = MagicMock()
        emit = MagicMock()
        qr = _make_queue_result(last_status="waiting_input", waiting=["T-1"])

        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ):
            _handle_post_drive_verification(
                tmp_path, state, 1, qr, "ok", _make_wup_health("failing"), hp, emit,
            )

        assert state.last_drive_action_plan["action"] == "wait"
        assert "failing" in state.last_drive_action_plan["reason"]


class TestAutoloopStateVerificationFields:
    def test_default_fields(self):
        state = AutoloopState()
        assert state.last_drive_snapshot == {}
        assert state.last_drive_verdict == {}
        assert state.last_drive_action_plan == {}
        assert state.drive_count_for_ticket == 0
        assert state.last_driven_ticket_for_count == ""
