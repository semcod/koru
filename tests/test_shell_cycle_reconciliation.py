from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.autonomy.cycle import shell_reconciliation as reconciliation
from koru.autonomy.phases.contexts import DrivePhaseInputs, DrivePhaseResult
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def waiting_queue():
    return QueueLoopResult(1, ["OLD"], [], ["PLF-1"], "waiting_input", last_ticket_id="PLF-1")


@pytest.mark.parametrize("action", ["done_verified", "done", "already_resolved"])
def test_terminal_readback_clears_waiting_and_scan_suppression(monkeypatch, action):
    monkeypatch.setattr(reconciliation, "fetch_ticket_status", lambda *a, **k: "done")
    state = AutoloopState(previous_signature="waiting_input:PLF-1", stagnation_streak=8)
    original = waiting_queue()
    telemetry = {"shell_drive_finalize": action}
    queue, status = reconciliation.reconcile_shell_cycle(Path("."), state, original, "ok", telemetry)
    assert queue.waiting == [] and queue.completed == ["OLD", "PLF-1"]
    assert queue.last_status == "completed" and status == "ok"
    assert original.waiting == ["PLF-1"] and original.completed == ["OLD"]
    assert not state.previous_signature.startswith("waiting_input:")
    assert state.stagnation_streak == 0 and telemetry["shell_cycle_reconciled"]


@pytest.mark.parametrize("live", [None, "open", "blocked", "in_progress"])
def test_unresolved_or_unreadable_ticket_is_not_completion(monkeypatch, live):
    monkeypatch.setattr(reconciliation, "fetch_ticket_status", lambda *a, **k: live)
    queue = waiting_queue()
    updated, _ = reconciliation.reconcile_shell_cycle(
        Path("."), AutoloopState(), queue, "ok", {"shell_drive_finalize": "done_verified"}
    )
    assert updated is queue


@pytest.mark.parametrize("action", ["verify_failed:reopened", "noted_unsuccessful", "done_failed"])
def test_failed_finalization_overrides_transport_status(action):
    state = AutoloopState()
    queue = waiting_queue()
    updated, status = reconciliation.reconcile_shell_cycle(
        Path("."), state, queue, "ok", {"shell_drive_finalize": action}
    )
    assert updated is queue
    assert status.startswith("failed(") and state.last_autopilot_status == status


def test_canceled_ticket_does_not_count_as_delivered(monkeypatch):
    monkeypatch.setattr(reconciliation, "fetch_ticket_status", lambda *a, **k: "canceled")
    queue, _ = reconciliation.reconcile_shell_cycle(
        Path("."), AutoloopState(), waiting_queue(), "ok", {"shell_drive_finalize": "already_resolved"}
    )
    assert queue.completed == ["OLD"] and not queue.waiting
    assert queue.last_status == "idle"


def test_async_drive_does_not_read_or_mutate_queue(monkeypatch):
    def unexpected(*a, **k):
        pytest.fail("Async drive must not reconcile shell tickets")

    monkeypatch.setattr(reconciliation, "fetch_ticket_status", unexpected)
    original = waiting_queue()
    queue, _ = reconciliation.reconcile_shell_cycle(Path("."), AutoloopState(), original, "ok", {})
    assert queue is original


def test_same_cycle_emission_and_return_use_reconciled_queue(monkeypatch):
    import koru.autonomous_cycle as facade
    from koru.autonomy.cycle.cycle import _run_drive_and_finalize

    monkeypatch.setattr(reconciliation, "fetch_ticket_status", lambda *a, **k: "done")
    monkeypatch.setattr(
        facade, "_run_drive_phase", lambda *a, **k: DrivePhaseResult("ok", "tillm_shell", "ticket_prompt")
    )
    emitted = []
    monkeypatch.setattr(
        facade, "_run_post_drive_phase", lambda ctx, cfg, inputs, result, **k: emitted.append(inputs.queue_result)
    )
    context = SimpleNamespace(project=Path("."), state=AutoloopState())
    inputs = DrivePhaseInputs(waiting_queue(), None, None, {"shell_drive_finalize": "done_verified"})
    status, queue = _run_drive_and_finalize(context, None, inputs)
    assert status == "ok" and queue.last_status == "completed"
    assert emitted == [queue] and emitted[0].waiting == []
