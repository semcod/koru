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
    assert 'NL: "Cykl 1: ticket_prompt' in content
    assert 'DSL: "action: submit_verified' in content


def test_find_ticket_dir(tmp_path) -> None:
    from koru.autonomy.cycle_trace import find_ticket_dir

    # No project directory
    assert find_ticket_dir(tmp_path, "PLF-031") is None

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create ticket directories
    (project_dir / "ticket-031").mkdir()
    (project_dir / "ticket-102--feature-test").mkdir()

    # Other namespaces never identify a Wellmanifest ticket
    assert find_ticket_dir(tmp_path, "PLF-031") is None
    assert find_ticket_dir(tmp_path, "plf-31") is None
    assert find_ticket_dir(tmp_path, "31") is None

    # Direct ticket names and slugged directories
    assert find_ticket_dir(tmp_path, "ticket-031") == project_dir / "ticket-031"
    assert find_ticket_dir(tmp_path, "ticket-102") == project_dir / "ticket-102--feature-test"

    # Unmapped
    assert find_ticket_dir(tmp_path, "PLF-999") is None
    assert find_ticket_dir(tmp_path, "-") is None
    assert find_ticket_dir(tmp_path, "") is None


def test_append_ticket_markdown_log_with_plf_identifier(tmp_path) -> None:
    ticket_dir = tmp_path / "project" / "ticket-031"
    ticket_dir.mkdir(parents=True)

    lines: list[str] = []
    record_decision_trace(
        project=tmp_path,
        cycle=42,
        queue_result=SimpleNamespace(
            last_status="waiting_input",
            waiting=["PLF-031"],
            waiting_ticket="PLF-031",
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

    assert not (ticket_dir / "koru.log.md").exists()
    # The normal decision trace is still emitted.
    assert lines


def test_find_ticket_dir_rejects_ambiguous_and_unsafe_ids(tmp_path):
    from koru.autonomy.cycle_trace import find_ticket_dir

    project = tmp_path / "project"
    for name in ("ticket-031--one", "ticket-031--two"):
        (project / name).mkdir(parents=True)
    assert find_ticket_dir(tmp_path, "ticket-031") is None
    assert find_ticket_dir(tmp_path, "ticket-031--one") == project / "ticket-031--one"
    for value in ("issue-031", "../ticket-031", "ticket-031/../../outside", "ticket-031*"):
        assert find_ticket_dir(tmp_path, value) is None
