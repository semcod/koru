"""Submit-strategy rotation when IDE submit verification fails repeatedly."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult

_CURSOR_RISKY_PASTE_MARKERS = (
    "composer.startcomposerprompt",
    "composer.startcomposerprompt2",
)


def risky_paste_winner(reply: Mapping[str, Any]) -> str | None:
    """Return paste command id when drive used a new-composer opener (Cursor)."""
    paste = str(reply.get("winning_paste") or "").strip()
    if not paste:
        return None
    lower = paste.lower()
    if any(marker in lower for marker in _CURSOR_RISKY_PASTE_MARKERS):
        return paste
    return None


def submit_alt_attempt_limit() -> int:
    raw = os.environ.get("KORU_SUBMIT_UNVERIFIED_ALT_ATTEMPTS", "").strip()
    if not raw:
        return 2
    try:
        return max(0, min(int(raw), 5))
    except ValueError:
        return 2


def submit_strategy_hint_for_streak(streak: int) -> str:
    if streak <= 0:
        return "submit_alt_registered"
    if streak == 1:
        return "submit_alt_glass_first"
    return "submit_alt_registered"


def record_submit_drive_outcome(
    state: AutoloopState,
    *,
    queue_result: QueueLoopResult,
    reply: dict[str, Any],
    ok: bool,
    autopilot_status: str,
    failure_signature: str,
) -> None:
    waiting_ticket = _waiting_ticket_id(queue_result)
    if ok:
        state.submit_unverified_streak = 0
        state.last_submit_failure_signature = ""
        state.pending_submit_strategy_hint = ""
        return

    status = parse_autopilot_status(autopilot_status)
    verification = str(reply.get("verification") or "").strip().lower()
    if not (status.submit_unverified or verification in {"submit_unverified", "submit_failed"}):
        return

    signature = failure_signature.strip()
    same_ticket = (
        waiting_ticket
        and waiting_ticket == str(state.last_submit_unverified_ticket_id or "")
    )
    risky_paste = risky_paste_winner(reply)
    if same_ticket and signature and signature == state.last_submit_failure_signature:
        state.submit_unverified_streak += 1
    else:
        state.submit_unverified_streak = 1
        state.last_submit_failure_signature = signature
    if risky_paste:
        state.submit_unverified_streak = max(state.submit_unverified_streak, 1)
        state.pending_submit_strategy_hint = "submit_alt_glass_first"
    else:
        state.pending_submit_strategy_hint = submit_strategy_hint_for_streak(
            state.submit_unverified_streak - 1
        )


def consume_pending_submit_strategy_hint(state: AutoloopState) -> str | None:
    hint = str(state.pending_submit_strategy_hint or "").strip()
    if not hint:
        return None
    state.pending_submit_strategy_hint = ""
    return hint


def should_block_manual_send(state: AutoloopState) -> bool:
    streak = int(getattr(state, "submit_unverified_streak", 0) or 0)
    status = parse_autopilot_status(getattr(state, "last_autopilot_status", "") or "")
    if streak <= 0 and status.submit_unverified:
        return True
    return streak >= submit_alt_attempt_limit()


def _waiting_ticket_id(queue_result: QueueLoopResult) -> str:
    ticket_id = getattr(queue_result, "last_ticket_id", None) or ""
    if ticket_id:
        return str(ticket_id)
    from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label

    label = _queue_loop_waiting_ticket_label(queue_result)
    return "" if label == "-" else label


__all__ = [
    "consume_pending_submit_strategy_hint",
    "record_submit_drive_outcome",
    "risky_paste_winner",
    "should_block_manual_send",
    "submit_alt_attempt_limit",
    "submit_strategy_hint_for_streak",
]
