"""Tests for submit-unverified streak and alternate submit strategy hints."""

from __future__ import annotations

from types import SimpleNamespace

from koru.autonomous_submit_strategy import (
    consume_pending_submit_strategy_hint,
    record_submit_drive_outcome,
    risky_paste_winner,
    should_block_manual_send,
    submit_alt_attempt_limit,
    submit_strategy_hint_for_streak,
)
from koru.autonomy.state import AutoloopState
from koruide.command_picker import HeuristicPicker, _reorder_submit_for_hint


def _queue_result(*, ticket_id: str = "T-1", status: str = "waiting_input"):
    return SimpleNamespace(last_status=status, last_ticket_id=ticket_id)


def test_submit_strategy_hint_rotation() -> None:
    assert submit_strategy_hint_for_streak(0) == "submit_alt_registered"
    assert submit_strategy_hint_for_streak(1) == "submit_alt_glass_first"
    assert submit_strategy_hint_for_streak(2) == "submit_alt_registered"


def test_risky_paste_winner_detects_start_composer() -> None:
    assert risky_paste_winner({"winning_paste": "composer.startComposerPrompt"}) == (
        "composer.startComposerPrompt"
    )
    assert risky_paste_winner({"winning_paste": "workbench.action.chat.paste"}) is None


def test_record_submit_drive_outcome_sets_hint() -> None:
    state = AutoloopState()
    queue = _queue_result()
    record_submit_drive_outcome(
        state,
        queue_result=queue,
        reply={"verification": "submit_unverified", "delivered": True},
        ok=False,
        autopilot_status="failed(submit_unverified)",
        failure_signature="submit_unverified|cursor-bubble",
    )
    assert state.submit_unverified_streak == 1
    assert state.pending_submit_strategy_hint == "submit_alt_registered"


def test_record_submit_drive_outcome_prefers_glass_after_risky_paste() -> None:
    state = AutoloopState()
    record_submit_drive_outcome(
        state,
        queue_result=_queue_result(),
        reply={
            "verification": "submit_unverified",
            "winning_paste": "composer.startComposerPrompt2",
        },
        ok=False,
        autopilot_status="failed(submit_unverified)",
        failure_signature="submit_unverified",
    )
    assert state.pending_submit_strategy_hint == "submit_alt_glass_first"


def test_consume_pending_submit_strategy_hint() -> None:
    state = AutoloopState(pending_submit_strategy_hint="submit_alt_glass_first")
    assert consume_pending_submit_strategy_hint(state) == "submit_alt_glass_first"
    assert state.pending_submit_strategy_hint == ""
    assert consume_pending_submit_strategy_hint(state) is None


def test_should_block_manual_send_after_limit() -> None:
    state = AutoloopState(submit_unverified_streak=submit_alt_attempt_limit())
    assert should_block_manual_send(state) is True
    state.submit_unverified_streak = submit_alt_attempt_limit() - 1
    assert should_block_manual_send(state) is False


def test_should_block_manual_send_for_legacy_submit_failure_state() -> None:
    state = AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        submit_unverified_streak=0,
    )
    assert should_block_manual_send(state) is True


def test_reorder_submit_registered_before_glass() -> None:
    commands = [
        "composer.sendToAgent",
        "workbench.action.chat.submit",
    ]
    registered = _reorder_submit_for_hint("cursor", commands, "submit_alt_registered")
    assert registered[0] == "workbench.action.chat.submit"
    glass = _reorder_submit_for_hint("cursor", commands, "submit_alt_glass_first")
    assert glass[0] == "composer.sendToAgent"


def test_heuristic_picker_applies_submit_hint() -> None:
    picker = HeuristicPicker()
    ordered = picker.pick(
        "cursor",
        "submit",
        catalog={
            "submit": [
                "composer.sendToAgent",
                "workbench.action.chat.submit",
            ]
        },
        hint="submit_alt_registered",
    )
    assert ordered[0] == "workbench.action.chat.submit"
