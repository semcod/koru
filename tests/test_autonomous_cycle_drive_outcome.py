from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomous_cycle_drive_outcome import apply_autopilot_drive_outcome
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def test_apply_drive_outcome_tracks_submit_failed_status(monkeypatch) -> None:
    import koru.autonomous_cycle_drive_outcome as outcome
    import koru.autonomous_cycle_orchestrator as orchestrator

    state = AutoloopState()
    queue = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-1"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-1",
    )
    monkeypatch.setattr(outcome.time, "time", lambda: 123.0)
    monkeypatch.setattr(outcome, "_log_autopilot_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "_emit_autopilot_observability_outcome", lambda **kwargs: None)

    apply_autopilot_drive_outcome(
        project=Path("/tmp/project"),
        state=state,
        queue_result=queue,
        reply={"ok": False, "delivered": True, "verification": "submit_failed"},
        ok=False,
        decision_kind="ticket_prompt",
        idle_prompt_kind=None,
        autopilot_status="failed(submit_failed)",
        autopilot_ide="cursor",
        cycle=1,
        cycle_telemetry={},
        _hp=lambda *args, **kwargs: None,
    )

    assert state.last_submit_unverified_ts == 123.0
    assert state.last_submit_unverified_ticket_id == "STARTER-1"


def test_failed_drive_routes_provider_exhaustion_to_waiting_ticket(monkeypatch) -> None:
    import koru.autonomous_cycle_drive_outcome as outcome
    import koru.autonomous_cycle_orchestrator as orchestrator
    import koru.autonomy.shell_drive_finalize as finalize

    queue = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-2"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-2",
    )
    captured: dict[str, object] = {}

    def fake_note_provider_exhaustion(**kwargs):
        captured.update(kwargs)
        return "noted_exhaustion"

    monkeypatch.setattr(finalize, "note_provider_exhaustion", fake_note_provider_exhaustion)
    monkeypatch.setattr(outcome, "_log_autopilot_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "_emit_autopilot_observability_outcome", lambda **kwargs: None)
    telemetry: dict[str, object] = {}

    apply_autopilot_drive_outcome(
        project=Path("/tmp/project"),
        state=AutoloopState(),
        queue_result=queue,
        reply={
            "ok": False,
            "provider_attempts": ["z.ai", "openrouter"],
            "stderr": "429 rate limit",
        },
        ok=False,
        decision_kind="ticket_prompt",
        idle_prompt_kind=None,
        autopilot_status="failed(client_error)",
        autopilot_ide="claude",
        cycle=1,
        cycle_telemetry=telemetry,
        _hp=lambda *args, **kwargs: None,
    )

    assert captured["ticket_id"] == "STARTER-2"
    assert telemetry["shell_drive_finalize"] == "noted_exhaustion"


def test_failed_drive_learns_agent_usage_limit(monkeypatch) -> None:
    import koru.autonomous_cycle_drive_outcome as outcome
    import koru.autonomous_cycle_orchestrator as orchestrator
    from koru.agent_availability import get_agent_availability

    queue = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
    )
    monkeypatch.setattr(outcome, "_log_autopilot_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "_emit_autopilot_observability_outcome", lambda **kwargs: None)
    telemetry: dict[str, object] = {}

    apply_autopilot_drive_outcome(
        project=Path("/tmp/project"),
        state=AutoloopState(),
        queue_result=queue,
        reply={
            "ok": False,
            "message": "drive failed",
            "stderr": "You have 0 weighted tokens left.",
        },
        ok=False,
        decision_kind="ticket_prompt",
        idle_prompt_kind=None,
        autopilot_status="failed(client_error)",
        autopilot_ide="qoder",
        cycle=1,
        cycle_telemetry=telemetry,
        _hp=lambda *args, **kwargs: None,
    )

    assert get_agent_availability("qoder").blocked is True
    assert telemetry["agent_unavailability_learned"] == "usage_limit_exhausted"


@pytest.mark.parametrize("ok", [True, False])
@pytest.mark.parametrize("action", ["done_verified", "skipped", "error"])
def test_finalization_contract_and_exception_isolation(monkeypatch, tmp_path, ok, action):
    import koru.agent_availability as availability
    import koru.autonomous_cycle_drive_outcome as outcome
    import koru.autonomous_cycle_orchestrator as orchestrator
    import koru.autonomy.shell_drive_finalize as finalize

    monkeypatch.setattr(availability, "learn_unavailability_from_reply", lambda *a: None)
    monkeypatch.setattr(outcome, "record_submit_drive_outcome", lambda *a, **k: None)
    monkeypatch.setattr(outcome, "risky_paste_winner", lambda *a: None)
    events = []
    logs = []
    state = AutoloopState()
    queue = QueueLoopResult(1, [], [], ["T-1"], "waiting_input", last_ticket_id="T-1")
    reply = {"backend": "test", "prompt": "implement"}
    telemetry = {"shell_drive_finalize": "prior"}

    def finalize_call(**kwargs):
        assert state.last_autopilot_status == "observed"
        assert kwargs["project"] == tmp_path
        assert kwargs["ticket_id"] == "T-1"
        assert kwargs["reply"] is reply
        assert kwargs["_hp"] == logs.append
        if ok:
            assert kwargs["autopilot_ide"] == "cursor"
            assert kwargs["ok"] is True
            assert kwargs["decision_kind"] == "ticket_prompt"
        events.append("finalize")
        if action == "error":
            raise RuntimeError("finalization unavailable")
        return action

    def unexpected(**kwargs):
        raise AssertionError("Wrong finalization route")

    monkeypatch.setattr(finalize, "finalize_shell_drive_ticket", finalize_call if ok else unexpected)
    monkeypatch.setattr(finalize, "note_provider_exhaustion", unexpected if ok else finalize_call)
    monkeypatch.setattr(outcome, "_log_autopilot_result", lambda *a: events.append("log"))
    monkeypatch.setattr(orchestrator, "_emit_autopilot_observability_outcome", lambda **k: events.append("emit"))
    result = apply_autopilot_drive_outcome(
        project=tmp_path, state=state, queue_result=queue, reply=reply, ok=ok,
        decision_kind="ticket_prompt", idle_prompt_kind=None, autopilot_status="observed",
        autopilot_ide="cursor", cycle=1, cycle_telemetry=telemetry, _hp=logs.append,
    )
    assert result == ("test", "ticket_prompt")
    assert events == ["finalize", "log", "emit"]
    assert telemetry["shell_drive_finalize"] == ("done_verified" if action == "done_verified" else "prior")
    if action == "error":
        assert logs == ["  shell-drive finalize error: finalization unavailable"]
