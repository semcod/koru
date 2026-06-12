"""Apply autopilot drive side-effects after a single client drive attempt."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomous_cycle_drive_retry import (
    _drive_failure_signature,
    _log_autopilot_result,
    _update_autopilot_state,
)
from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.state import AutoloopState
from koru.autonomous_submit_strategy import record_submit_drive_outcome, risky_paste_winner
from koru.queue import QueueLoopResult


def apply_autopilot_drive_outcome(
    *,
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    reply: dict[str, Any],
    ok: bool,
    decision_kind: str | None,
    idle_prompt_kind: str | None,
    autopilot_status: str,
    autopilot_ide: str,
    cycle: int,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
) -> tuple[str | None, str | None]:
    """Update loop state, telemetry, and observability after one drive."""
    autopilot_drive_kind = idle_prompt_kind or decision_kind
    autopilot_backend = str(reply.get("backend")) if reply.get("backend") is not None else None
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)

    if ok:
        state.last_message_sent_ts = time.time()
        state.last_message_sent_ide = autopilot_ide
        state.last_driven_ticket_id = waiting_ticket
        state.last_submit_unverified_ts = 0.0
        state.last_submit_unverified_ticket_id = ""
        if autopilot_backend:
            state.last_driven_backend = autopilot_backend
    elif parse_autopilot_status(autopilot_status).submit_unverified and reply.get("delivered") is True:
        state.last_driven_ticket_id = waiting_ticket
        state.last_submit_unverified_ts = time.time()
        state.last_submit_unverified_ticket_id = waiting_ticket

    record_submit_drive_outcome(
        state,
        queue_result=queue_result,
        reply=reply,
        ok=ok,
        autopilot_status=autopilot_status,
        failure_signature=_drive_failure_signature(reply),
    )
    if risky := risky_paste_winner(reply):
        cycle_telemetry["autopilot_risky_paste_winner"] = risky
        _hp(
            "  → risky paste winner detected "
            f"({risky}); next drive will prefer alternate submit strategy"
        )
    state.last_autopilot_status = autopilot_status
    _update_autopilot_state(
        state, ok, decision_kind, autopilot_drive_kind, reply.get("prompt", "")
    )
    _log_autopilot_result(ok, queue_result, autopilot_ide, decision_kind, reply, _hp)
    from koru.autonomous_cycle_orchestrator import _emit_autopilot_observability_outcome

    _emit_autopilot_observability_outcome(
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        reply=reply,
        ok=ok,
        autopilot_status=autopilot_status,
        decision_kind=decision_kind or "",
        autopilot_ide=autopilot_ide,
    )
    return autopilot_backend, autopilot_drive_kind
