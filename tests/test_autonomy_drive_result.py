from __future__ import annotations

from koru.autonomy.drive_result import DriveAttemptResult


def test_drive_attempt_result_classifies_submit_unverified_as_not_safe_to_redrive() -> None:
    result = DriveAttemptResult.from_reply(
        {
            "ok": False,
            "backend": "plugin",
            "verification": "submit_unverified",
            "submitted": False,
            "submit_failure_reason": "input still contains pasted text",
            "photo_vql_observe": {
                "capture_provenance": {"capture_confirmed": False},
            },
        }
    )

    assert result.status == "failed"
    assert result.reason_code == "submit_unverified"
    assert result.legacy_autopilot_status() == "failed(submit_unverified)"
    assert result.safe_to_redrive is False
    assert result.retryable is False
    assert result.capture_confirmed is False


def test_drive_attempt_result_classifies_manual_focus_as_skip() -> None:
    result = DriveAttemptResult.from_reply(
        {
            "ok": False,
            "message": "chat input is not focused/open",
            "diagnostics": {"focusOpenCandidates": []},
        }
    )

    assert result.status == "skipped"
    assert result.reason_code == "manual_focus"
    assert result.requires_manual_focus is True
    assert result.legacy_autopilot_status() == "skipped(manual_focus)"


def test_drive_attempt_result_preserves_ok_vdisplay_capture_context() -> None:
    result = DriveAttemptResult.from_reply(
        {
            "ok": True,
            "backend": "vdisplay",
            "verification": "submit_ok",
            "capture_confirmed": True,
        }
    )

    assert result.status == "ok"
    assert result.reason_code == "ok"
    assert result.backend == "vdisplay"
    assert result.capture_confirmed is True
