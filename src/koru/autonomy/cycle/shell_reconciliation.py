"""Project shell finalization into the current cycle using live Planfile state."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from koru.autonomy.cycle_queue_scan import _update_stagnation_state
from koru.autonomy.post_run_verify import fetch_ticket_status
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult, run_process


def reconcile_shell_cycle(
    project: Path,
    state: AutoloopState,
    queue: QueueLoopResult,
    drive_status: str,
    telemetry: dict[str, Any],
) -> tuple[QueueLoopResult, str]:
    """A successful transport cannot override a failed or unresolved finalization."""
    action = str(telemetry.get("shell_drive_finalize") or "")
    if action.startswith("verify_failed:") or action in {"noted_unsuccessful", "done_failed"}:
        drive_status = f"failed(shell_finalize:{action})"
        state.last_autopilot_status = drive_status
        return queue, drive_status
    if action not in {"done_verified", "done", "already_resolved"}:
        return queue, drive_status
    ticket_id = queue.last_ticket_id
    if not ticket_id or ticket_id not in queue.waiting:
        return queue, drive_status
    live_status = fetch_ticket_status(project, ticket_id, runner=run_process)
    telemetry["shell_ticket_live_status"] = live_status or "unknown"
    if live_status not in {"done", "canceled"}:
        return queue, drive_status
    waiting = [item for item in queue.waiting if item != ticket_id]
    completed = list(queue.completed)
    if live_status == "done" and ticket_id not in completed:
        completed.append(ticket_id)
    queue = replace(
        queue,
        waiting=waiting,
        completed=completed,
        last_status="waiting_input" if waiting else ("completed" if live_status == "done" else "idle"),
        last_ticket_id=waiting[-1] if waiting else ticket_id,
        last_message=f"Shell finalization reconciled: {ticket_id} is {live_status}",
    )
    _update_stagnation_state(state, queue)
    telemetry["shell_cycle_reconciled"] = True
    return queue, drive_status
