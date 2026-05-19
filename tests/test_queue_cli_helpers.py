"""Tests for queue CLI helpers."""

from types import SimpleNamespace

from koru.queue_cli_helpers import (
    queue_loop_exit_code,
    queue_status_marker,
    single_task_ticket_lists,
)


def test_queue_status_marker_known_status():
    assert queue_status_marker("completed") == "✓"


def test_queue_loop_exit_code_success():
    assert queue_loop_exit_code("waiting_input") == 0
    assert queue_loop_exit_code("failed") == 1


def test_single_task_ticket_lists():
    result = SimpleNamespace(status="completed", ticket_id="PLF-1")
    assert single_task_ticket_lists(result) == (["PLF-1"], [], [])


def test_emit_queue_run_started_does_not_raise() -> None:
    from koru.queue_cli_helpers import emit_queue_run_started

    args = SimpleNamespace(
        loop=False,
        queue_name="default",
        project=".",
        actor="koru-shell",
        dry_run=False,
        interactive=False,
    )
    emit_queue_run_started(args)
