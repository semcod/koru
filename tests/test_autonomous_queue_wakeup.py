from types import SimpleNamespace

import pytest

from koru.autonomy.cycle.cycle import _update_stagnation_state
from koru.autonomy.queue_wakeup import sleep_until_queue_ready
from koru.autonomy.state import AutoloopState
from koru.queue.types import QueueLoopResult


class Clock:
    def __init__(self):
        self.time = 0.0
        self.sleeps = []

    def now(self):
        return self.time

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.time += seconds


def idle_context(tmp_path, **changes):
    (tmp_path / ".planfile").mkdir(exist_ok=True)
    fields = dict(
        project=tmp_path,
        queue_result=QueueLoopResult(1, [], [], [], "idle"),
        autopilot_status="skipped(idle_no_ticket)",
        diag_result=SimpleNamespace(status="ok"),
        args=SimpleNamespace(ticket_sources="queue", queue_name="default"),
    )
    fields.update(changes)
    return SimpleNamespace(**fields)


def test_progress_resets_stagnation_even_when_drain_ends_idle():
    state = AutoloopState(previous_signature="idle:-", stagnation_streak=9)
    _update_stagnation_state(state, QueueLoopResult(4, ["A", "B", "C"], [], [], "idle"))
    assert state.stagnation_streak == 0
    _update_stagnation_state(state, QueueLoopResult(1, [], [], [], "idle"))
    assert state.stagnation_streak == 1


def test_partial_progress_does_not_cancel_failure_backoff():
    state = AutoloopState(previous_signature="idle:-", stagnation_streak=9)
    _update_stagnation_state(state, QueueLoopResult(3, ["A"], ["B"], [], "idle"))
    assert state.stagnation_streak == 10


def test_arrival_interrupts_idle_wait_and_keeps_queue_scope(tmp_path):
    clock = Clock()
    probes = []

    def ready(project, queue):
        probes.append((clock.now(), project, queue))
        return clock.now() >= 10

    assert sleep_until_queue_ready(
        idle_context(tmp_path), 900, sleep=clock.sleep, now=clock.now, ready=ready, revision=lambda _: clock.now() >= 10
    )
    assert clock.time == 10
    assert probes == [(0, tmp_path, "default"), (10, tmp_path, "default")]


def test_unchanged_or_unready_queue_retains_backoff_with_bounded_probes(tmp_path):
    clock = Clock()
    probes = []
    assert not sleep_until_queue_ready(
        idle_context(tmp_path),
        125,
        sleep=clock.sleep,
        now=clock.now,
        ready=lambda *_: probes.append(clock.now()) or False,
        revision=lambda _: 1,
    )
    assert clock.time == 125
    assert probes == [0, 60, 120]


@pytest.mark.parametrize(
    "changes",
    [
        {"autopilot_status": "skipped(agent_rate_limited)"},
        {"autopilot_status": "failed"},
        {"diag_result": SimpleNamespace(status="failed")},
        {"queue_result": QueueLoopResult(1, [], ["A"], [], "idle")},
        {"queue_result": QueueLoopResult(1, [], [], ["A"], "waiting_input")},
    ],
)
def test_failure_provider_and_operator_waits_are_not_interrupted(tmp_path, changes):
    clock = Clock()

    def forbidden(*_):
        pytest.fail("must not probe or interrupt a non-idle backoff")

    assert not sleep_until_queue_ready(
        idle_context(tmp_path, **changes), 900, sleep=clock.sleep, now=clock.now, ready=forbidden
    )
    assert clock.sleeps == [900]


def test_explicit_all_queues_scope_is_preserved(tmp_path):
    clock = Clock()
    scopes = []
    context = idle_context(tmp_path, args=SimpleNamespace(ticket_sources="all", queue_name="default"))
    assert sleep_until_queue_ready(
        context, 900, sleep=clock.sleep, now=clock.now, ready=lambda _, queue: scopes.append(queue) or True
    )
    assert scopes == [None]


def test_failed_readiness_probe_does_not_wake(tmp_path, monkeypatch):
    import subprocess

    from koru.autonomy import queue_wakeup

    monkeypatch.setattr(
        queue_wakeup,
        "planfile_command",
        lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("planfile", 5)),
    )
    assert not queue_wakeup.has_ready_machine_work(tmp_path, "default")


def test_metadata_failure_keeps_periodic_readiness(tmp_path):
    clock = Clock()
    probes = []

    def unavailable(_):
        raise PermissionError("metadata unreadable")

    def ready(*_):
        probes.append(clock.now())
        return clock.now() >= 60

    assert sleep_until_queue_ready(
        idle_context(tmp_path), 900, sleep=clock.sleep, now=clock.now, ready=ready, revision=unavailable
    )
    assert probes == [0, 60]


def test_outer_sleep_phase_uses_wakeup_and_reports_it(tmp_path, monkeypatch):
    from koru.autonomy.phases import sleep_phase

    context = idle_context(tmp_path)
    context.args.emit_events = "human"
    context.loop_state = AutoloopState()
    context.waiting_ticket = ""
    context.cycle = 3
    context.correlation_id = "wake-test"
    context.autopilot_ide = "claude-code"
    calls = []
    logs = []
    monkeypatch.setattr(
        sleep_phase, "sleep_until_queue_ready", lambda ctx, duration, **kw: calls.append((ctx, duration)) or True
    )

    def noop(*args, **kwargs):
        return None

    assert not sleep_phase.finish_cycle_with_sleep(
        context,
        cycle_stop_reason=noop,
        emit_cycle_summary=noop,
        emit_idle_no_ticket_warning=noop,
        log_operator_next_steps=noop,
        emit_structured_report=noop,
        handle_exit_conditions=lambda *args: False,
        compute_cycle_sleep=lambda *args: 900,
        stdio_info=lambda message, *, fmt: logs.append((message, fmt)),
        sleep=noop,
    )
    assert calls == [(context, 900)]
    assert "queue wake:" in logs[0][0]
    assert logs[0][1] == "human"
