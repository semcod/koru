from types import SimpleNamespace

from koru.autonomy.cycle_trace import decision_next_step_hint, record_decision_trace
from koru.autonomy.decision_trace import load_recent_decisions


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


def test_decision_next_step_hint_reads_submit_unverified_status_without_telemetry() -> None:
    assert (
        decision_next_step_hint(
            queue_status="waiting_input",
            autopilot_status="failed(submit_unverified)",
            cycle_telemetry={},
        )
        == "manual send required; validate submit trace before any redrive"
    )


def test_repeated_idle_decision_is_persisted_without_repeated_human_log(tmp_path) -> None:
    lines: list[str] = []

    record_decision_trace(
        project=tmp_path,
        cycle=7,
        queue_result=SimpleNamespace(last_status="idle", waiting_ticket=None),
        diag_result=SimpleNamespace(status="skipped"),
        wup_health=SimpleNamespace(status="skipped"),
        autopilot_status="skipped",
        autopilot_ide="local",
        autopilot_backend=None,
        autopilot_drive_kind=None,
        cycle_telemetry={},
        stagnation_streak=2,
        hp=lines.append,
    )

    assert lines == []
    assert load_recent_decisions(tmp_path)[-1]["cycle"] == 7


def test_append_ticket_markdown_log(tmp_path) -> None:
    ticket_dir = tmp_path / "project" / "ticket-101"
    ticket_dir.mkdir(parents=True)

    lines: list[str] = []
    record_decision_trace(
        project=tmp_path,
        cycle=1,
        queue_result=SimpleNamespace(
            last_status="waiting_input",
            waiting=["ticket-101"],
            waiting_ticket="ticket-101",
        ),
        diag_result=SimpleNamespace(status="ok"),
        wup_health=SimpleNamespace(status="ok"),
        autopilot_status="ok",
        autopilot_ide="cursor",
        autopilot_backend="plugin",
        autopilot_drive_kind="ticket_prompt",
        cycle_telemetry={},
        stagnation_streak=0,
        hp=lines.append,
    )

    log_file = ticket_dir / "koru.log.md"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "# Koru Autonomy Log: `ticket-101`" in content
    assert "```yaml" in content
    assert "uri: koru://cycle/1/decision/submit_verified" in content
    assert "decided: ticket_prompt" in content
