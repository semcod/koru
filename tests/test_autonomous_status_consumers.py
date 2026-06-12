from __future__ import annotations

from types import SimpleNamespace

from koru.autonomous_auto_pipeline import AutoPipelineState, _auto_pipeline_has_pressure
from koru.autonomous_cycle_skip_conditions import _previous_drive_needs_manual_send
from koru.autonomy.state import AutoloopState


def test_auto_pipeline_pressure_uses_parsed_failed_status() -> None:
    state = AutoPipelineState(seen_cycles=1, last_autopilot_status="failed(submit_failed)")

    assert _auto_pipeline_has_pressure(state, max_iterations=50) == (
        True,
        "autopilot failed",
    )


def test_previous_drive_needs_manual_send_uses_parsed_submit_failed_status() -> None:
    state = AutoloopState(last_autopilot_status="failed(submit_failed)")

    assert _previous_drive_needs_manual_send(state) is True


def test_previous_drive_needs_manual_send_ignores_plain_failed_status() -> None:
    state = AutoloopState(last_autopilot_status="failed")

    assert _previous_drive_needs_manual_send(state) is False
