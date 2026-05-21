"""Tests for queue CLI helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

import koru.queue.local_manager as queue_local_manager
import koru.queue_cli_helpers as helpers
from koru.queue.types import QueueLoopResult, QueueRunResult
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


class FakeLocalManagerClient:
    enabled = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def register_worker(self, **payload):  # noqa: ANN003, ANN201
        self.calls.append(("register", payload))
        return {"decision": {"action": "continue"}}

    def claim_action(self, **payload):  # noqa: ANN003, ANN201
        self.calls.append(("claim", payload))
        return {"status": "leased", "item": {"id": "ACT-1"}}

    def heartbeat_worker(self, **payload):  # noqa: ANN003, ANN201
        self.calls.append(("heartbeat", payload))
        return {"decision": {"action": "drain-and-exit"}}

    def complete_action(self, **payload):  # noqa: ANN003, ANN201
        self.calls.append(("complete", payload))
        return {"status": payload["status"]}


def test_run_queue_loop_mode_stops_after_local_manager_drain(monkeypatch) -> None:
    fake_client = FakeLocalManagerClient()
    monkeypatch.setattr(
        queue_local_manager.LocalManagerClient,
        "from_env",
        Mock(return_value=fake_client),
    )

    def fake_loop(**kwargs):  # noqa: ANN003, ANN202
        result = QueueRunResult(status="completed", ticket_id="PLF-1", executor_kind="shell")
        kwargs["progress_callback"](result, 1)
        assert kwargs["stop_callback"](result, 1) is True
        return QueueLoopResult(
            iterations=1,
            completed=["PLF-1"],
            failed=[],
            waiting=[],
            last_status="completed",
            last_ticket_id="PLF-1",
        )

    monkeypatch.setattr(helpers, "run_planfile_queue_loop", fake_loop)
    monkeypatch.setattr(helpers, "emit_management_event", Mock())
    args = SimpleNamespace(
        loop=True,
        queue_name="default",
        project=".",
        actor="koru-shell",
        dry_run=False,
        interactive=False,
        max_iterations=10,
    )

    rc = helpers.run_queue_loop_mode(
        args,
        run_log=None,
        planfile_runner=Mock(),
        shell_runner=Mock(),
        api_runner=Mock(),
        llm_runner=Mock(),
        prompt_runner=Mock(),
    )

    assert rc == 0
    assert [name for name, _payload in fake_client.calls] == [
        "register",
        "claim",
        "heartbeat",
        "complete",
    ]
    complete_payload = fake_client.calls[-1][1]
    assert complete_payload["action_id"] == "ACT-1"
    assert complete_payload["status"] == "completed"
