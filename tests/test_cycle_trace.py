from koru.autonomy.cycle_trace import decision_next_step_hint


def test_decision_next_step_hint_prefers_ok_status() -> None:
    assert (
        decision_next_step_hint(
            queue_status="waiting_input",
            autopilot_status="ok",
            cycle_telemetry={"autopilot_skipped_plugin_missing": True},
        )
        == "wait for IDE response, then advance queue"
    )


def test_decision_next_step_hint_uses_ordered_telemetry() -> None:
    assert (
        decision_next_step_hint(
            queue_status="idle",
            autopilot_status="skipped(plugin_not_connected)",
            cycle_telemetry={
                "autopilot_skipped_plugin_missing": True,
                "autopilot_skipped_idle_no_ticket": True,
            },
        )
        == "wait for plugin reconnect (manual reload may be needed)"
    )


def test_decision_next_step_hint_falls_back_to_queue_status() -> None:
    assert (
        decision_next_step_hint(
            queue_status="waiting_input",
            autopilot_status="skipped(action_off)",
            cycle_telemetry={},
        )
        == "keep waiting ticket scoped; rerun queue next cycle"
    )


def test_decision_next_step_hint_submit_unverified_does_not_retry() -> None:
    assert (
        decision_next_step_hint(
            queue_status="waiting_input",
            autopilot_status="failed",
            cycle_telemetry={"autopilot_submit_unverified": True},
        )
        == "manual send required; validate submit trace before any redrive"
    )
