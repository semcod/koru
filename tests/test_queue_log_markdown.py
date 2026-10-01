from __future__ import annotations

from types import SimpleNamespace

from koru.autonomy.cycle_trace import append_queue_ticket_markdown_log


def test_append_queue_ticket_markdown_log(tmp_path) -> None:
    ticket_dir = tmp_path / "project" / "ticket-031"
    ticket_dir.mkdir(parents=True)

    result = SimpleNamespace(
        ticket_id="ticket-031",
        status="completed",
        executor_kind="human",
        exit_code=0,
        message="Refactored build_context function cleanly.",
    )

    append_queue_ticket_markdown_log(tmp_path, result)

    log_file = ticket_dir / "koru.log.md"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "# Koru Autonomy Log: `ticket-031`" in content
    assert "uri: koru://queue/task/ticket-031/completed" in content
    assert "ticket: ticket-031" in content
    assert "executor: human" in content
    assert "status: completed" in content
    assert "Refactored build_context function cleanly." in content


def test_append_queue_ticket_markdown_log_unmapped(tmp_path) -> None:
    # Project with no project/ directory
    result = SimpleNamespace(
        ticket_id="PLF-999",
        status="completed",
        executor_kind="human",
        exit_code=0,
        message="Done",
    )
    append_queue_ticket_markdown_log(tmp_path, result)
    assert not (tmp_path / "project").exists()


def test_planfile_result_does_not_pollute_closed_wellmanifest_ticket(tmp_path):
    ticket_dir = tmp_path / "project" / "ticket-001"
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "README.md").write_text("- **Status**: DONE\n")
    log = ticket_dir / "koru.log.md"
    log.write_text("Historical evidence\n")
    result = SimpleNamespace(ticket_id="PLF-001", status="waiting_input",
                             executor_kind="human", exit_code=None, message="NO_LICENSE")
    for _ in range(3):
        append_queue_ticket_markdown_log(tmp_path, result)
    assert log.read_text() == "Historical evidence\n"
