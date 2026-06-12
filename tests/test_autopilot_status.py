from __future__ import annotations

from koru.autonomy.autopilot_status import parse_autopilot_status


def test_parse_autopilot_status_ok() -> None:
    status = parse_autopilot_status("ok")

    assert status.ok is True
    assert status.code == "ok"
    assert status.blocker_code == ""


def test_parse_autopilot_status_submit_unverified() -> None:
    status = parse_autopilot_status("failed(submit_unverified)")

    assert status.failed is True
    assert status.submit_unverified is True
    assert status.blocker_code == "manual_send_required"


def test_parse_autopilot_status_manual_focus() -> None:
    status = parse_autopilot_status("skipped(manual_focus)")

    assert status.skipped is True
    assert status.manual_focus is True
    assert status.blocker_code == "manual_focus_required"


def test_parse_autopilot_status_plain_failed() -> None:
    status = parse_autopilot_status("failed")

    assert status.failed is True
    assert status.code == "drive_failed"
