"""Tests for koru.autonomy.cycle.cycle_post_drive.

Targets the pure/near-pure helper functions directly (effect computation,
verdict override, snapshot reconstruction, drive-count bookkeeping, and the
emit-gating conditions) rather than the full orchestrator, which mostly
wires these together and calls out to verification_engine/planning_llm.
"""

from __future__ import annotations

from koru.autonomy.cycle.cycle_post_drive import (
    _drive_effect_payload,
    _emit_drive_effect_if_needed,
    _maybe_emit_improved_prompt,
    _post_drive_ticket_id,
    _snapshot_before_drive,
    _submitted_but_no_effect,
    _update_drive_count,
)
from koru.autonomy.state import AutoloopState
from koru.autonomy.verification_engine import Evidence, GitEvidence, Verdict
from koru.queue import QueueLoopResult


def _evidence(**overrides) -> Evidence:
    defaults = dict(
        git=GitEvidence(files_changed=0),
    )
    defaults.update(overrides)
    return Evidence(**defaults)


class TestDriveEffectPayload:
    def test_prompt_submitted_and_work_applied(self) -> None:
        evidence = _evidence(git=GitEvidence(files_changed=2, insertions=10, deletions=1))
        effect = _drive_effect_payload(
            ticket_id="STARTER-1",
            queue_status="completed",
            evidence=evidence,
            drive_status="ok",
        )
        assert effect["prompt_submitted"] is False  # no chat evidence supplied
        assert effect["work_applied"] is True
        assert effect["git_delta"]["files_changed"] == 2

    def test_prompt_submitted_flag_requires_ok_status_and_message_sent(self) -> None:
        from koru.autonomy.verification_engine import ChatEvidence

        evidence = _evidence(chat=ChatEvidence(has_message_sent=True))
        effect = _drive_effect_payload(
            ticket_id="STARTER-1",
            queue_status="waiting_input",
            evidence=evidence,
            drive_status="ok",
        )
        assert effect["prompt_submitted"] is True

        effect_not_ok = _drive_effect_payload(
            ticket_id="STARTER-1",
            queue_status="waiting_input",
            evidence=evidence,
            drive_status="failed",
        )
        assert effect_not_ok["prompt_submitted"] is False

    def test_ticket_still_waiting_when_queue_waiting_and_no_git_changes(self) -> None:
        effect = _drive_effect_payload(
            ticket_id="STARTER-1",
            queue_status="waiting_input",
            evidence=_evidence(),
            drive_status="ok",
        )
        assert effect["ticket_after"] == "STARTER-1"
        assert effect["planfile_delta"] == "still_waiting_input"
        assert effect["work_applied"] is False

    def test_ticket_not_waiting_when_no_ticket_id(self) -> None:
        effect = _drive_effect_payload(
            ticket_id="",
            queue_status="waiting_input",
            evidence=_evidence(),
            drive_status="ok",
        )
        assert effect["ticket_after"] == "-"
        assert effect["work_applied"] is True  # not ticket_still_waiting -> True


class TestSubmittedButNoEffect:
    def test_overrides_outcome_and_confidence(self) -> None:
        original = Verdict(outcome="no_change", confidence=0.4, reason="orig")
        effect = {
            "git_delta": {"files_changed": 0},
            "planfile_delta": "still_waiting_input",
            "test_delta": "unknown",
        }
        overridden = _submitted_but_no_effect(original, effect)
        assert overridden.outcome == "submitted_but_no_effect"
        assert overridden.confidence == 0.95
        assert "planfile_delta=still_waiting_input" in overridden.reason
        assert overridden.evidence is original.evidence
        assert overridden.ticket_id == original.ticket_id


class TestSnapshotBeforeDrive:
    def test_returns_none_when_no_prior_snapshot(self) -> None:
        state = AutoloopState()
        assert _snapshot_before_drive(state) is None

    def test_reconstructs_snapshot_from_stored_dict(self) -> None:
        state = AutoloopState()
        state.last_drive_snapshot = {
            "git_head": "abc123",
            "git_dirty_count": 3,
            "test_status": "ok",
            "timestamp": 100.5,
        }
        snap = _snapshot_before_drive(state)
        assert snap is not None
        assert snap.git_head == "abc123"
        assert snap.git_dirty_count == 3
        assert snap.test_status == "ok"
        assert snap.timestamp == 100.5


class TestPostDriveTicketId:
    def test_returns_empty_string_when_no_waiting_ticket(self) -> None:
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        assert _post_drive_ticket_id(result) == ""

    def test_returns_last_waiting_ticket(self) -> None:
        result = QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=["STARTER-1", "STARTER-2"],
            last_status="waiting_input",
        )
        assert _post_drive_ticket_id(result) == "STARTER-2"


class TestUpdateDriveCount:
    def test_noop_for_empty_ticket_id(self) -> None:
        state = AutoloopState()
        _update_drive_count(state, "")
        assert state.drive_count_for_ticket == 0
        assert state.last_driven_ticket_for_count == ""

    def test_first_drive_of_a_ticket_starts_count_at_one(self) -> None:
        state = AutoloopState()
        _update_drive_count(state, "STARTER-1")
        assert state.drive_count_for_ticket == 1
        assert state.last_driven_ticket_for_count == "STARTER-1"

    def test_repeated_drive_of_same_ticket_increments(self) -> None:
        state = AutoloopState()
        _update_drive_count(state, "STARTER-1")
        _update_drive_count(state, "STARTER-1")
        _update_drive_count(state, "STARTER-1")
        assert state.drive_count_for_ticket == 3

    def test_drive_of_different_ticket_resets_count(self) -> None:
        state = AutoloopState()
        _update_drive_count(state, "STARTER-1")
        _update_drive_count(state, "STARTER-1")
        _update_drive_count(state, "STARTER-2")
        assert state.drive_count_for_ticket == 1
        assert state.last_driven_ticket_for_count == "STARTER-2"


class TestEmitDriveEffectIfNeeded:
    def test_does_not_emit_when_effect_is_normal(self) -> None:
        calls = []
        effect = {"prompt_submitted": False, "work_applied": True}
        _emit_drive_effect_if_needed(1, "STARTER-1", effect, calls.append, calls.append)
        assert calls == []

    def test_emits_hp_and_event_when_submitted_but_no_effect(self) -> None:
        hp_calls: list[str] = []
        emit_calls: list[tuple[str, dict]] = []
        effect = {
            "prompt_submitted": True,
            "work_applied": False,
            "git_delta": {"files_changed": 0},
            "planfile_delta": "still_waiting_input",
            "test_delta": "unknown",
        }
        _emit_drive_effect_if_needed(
            5, "STARTER-9", effect, hp_calls.append, lambda name, payload: emit_calls.append((name, payload))
        )
        assert len(hp_calls) == 1
        assert "submitted_but_no_effect" in hp_calls[0]
        assert emit_calls == [("DriveEffect", {"cycle": 5, "ticket_id": "STARTER-9", **effect})]


class TestMaybeEmitLlmEvaluation:
    def test_swallows_exceptions_from_llm_call(self, monkeypatch) -> None:
        import koru.autonomy.cycle.cycle_post_drive as mod

        def _boom(*args, **kwargs):
            raise RuntimeError("llm unavailable")

        monkeypatch.setattr(mod, "_llm_evaluate_drive_result", _boom)
        hp_calls: list[str] = []
        emit_calls: list[tuple] = []
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        # Must not raise.
        mod._maybe_emit_llm_evaluation(
            cycle=1,
            ticket_id="STARTER-1",
            queue_result=result,
            state=AutoloopState(),
            verdict=Verdict(outcome="no_change", confidence=0.5, reason="r"),
            evidence=_evidence(),
            hp=hp_calls.append,
            emit=lambda name, payload: emit_calls.append((name, payload)),
        )
        assert hp_calls == []
        assert emit_calls == []

    def test_emits_when_llm_returns_evaluation(self, monkeypatch) -> None:
        import koru.autonomy.cycle.cycle_post_drive as mod

        class _FakeEval:
            outcome = "confirmed"
            confidence = 0.8
            reason = "looks fine"
            suggestion = None

        monkeypatch.setattr(mod, "_llm_evaluate_drive_result", lambda *a, **k: _FakeEval())
        hp_calls: list[str] = []
        emit_calls: list[tuple] = []
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        mod._maybe_emit_llm_evaluation(
            cycle=2,
            ticket_id="STARTER-1",
            queue_result=result,
            state=AutoloopState(),
            verdict=Verdict(outcome="no_change", confidence=0.5, reason="r"),
            evidence=_evidence(),
            hp=hp_calls.append,
            emit=lambda name, payload: emit_calls.append((name, payload)),
        )
        assert len(hp_calls) == 1
        assert emit_calls[0][0] == "LlmEvaluation"
        assert emit_calls[0][1]["outcome"] == "confirmed"


class TestMaybeEmitImprovedPrompt:
    def test_skips_when_verdict_is_not_no_change(self, monkeypatch) -> None:
        import koru.autonomy.cycle.cycle_post_drive as mod

        state = AutoloopState()
        state.drive_count_for_ticket = 3
        state.last_driven_prompt = "do the thing"
        emit_calls: list[tuple] = []
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        mod._maybe_emit_improved_prompt(
            cycle=1,
            ticket_id="STARTER-1",
            queue_result=result,
            state=state,
            verdict=Verdict(outcome="confirmed", confidence=0.9, reason="r"),
            hp=lambda *_: None,
            emit=lambda name, payload: emit_calls.append((name, payload)),
        )
        assert emit_calls == []

    def test_skips_when_drive_count_below_threshold(self) -> None:
        state = AutoloopState()
        state.drive_count_for_ticket = 1
        state.last_driven_prompt = "do the thing"
        emit_calls: list[tuple] = []
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        _maybe_emit_improved_prompt(
            cycle=1,
            ticket_id="STARTER-1",
            queue_result=result,
            state=state,
            verdict=Verdict(outcome="no_change", confidence=0.9, reason="r"),
            hp=lambda *_: None,
            emit=lambda name, payload: emit_calls.append((name, payload)),
        )
        assert emit_calls == []

    def test_emits_improved_prompt_when_conditions_met(self, monkeypatch) -> None:
        import koru.autonomy.cycle.cycle_post_drive as mod

        monkeypatch.setattr(
            mod, "_llm_generate_better_prompt", lambda **kwargs: "a much better prompt"
        )
        state = AutoloopState()
        state.drive_count_for_ticket = 2
        state.last_driven_prompt = "do the thing"
        hp_calls: list[str] = []
        emit_calls: list[tuple] = []
        result = QueueLoopResult(
            iterations=1, completed=[], failed=[], waiting=[], last_status="idle"
        )
        mod._maybe_emit_improved_prompt(
            cycle=3,
            ticket_id="STARTER-1",
            queue_result=result,
            state=state,
            verdict=Verdict(outcome="no_change", confidence=0.9, reason="r"),
            hp=hp_calls.append,
            emit=lambda name, payload: emit_calls.append((name, payload)),
        )
        assert len(hp_calls) == 1
        assert emit_calls[0][0] == "LlmImprovedPrompt"
        assert emit_calls[0][1]["improved_length"] == len("a much better prompt")
