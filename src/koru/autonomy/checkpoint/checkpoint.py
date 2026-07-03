"""Checkpoint and loop-state helpers for ``koru autonomous``."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from koru.autonomous_cycle import AutoloopState
    from koru.queue import QueueLoopResult


def _stdio_info(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def queue_loop_waiting_ticket_label(queue_result: QueueLoopResult) -> str:
    """Last ticket id in ``waiting`` (terminal queue state), or ``-`` if unknown."""
    waiting = getattr(queue_result, "waiting", None) or []
    return waiting[-1] if waiting else "-"


def current_head(project: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def compute_backoff_sleep(base: float, streak: int, cap: float, enabled: bool) -> float:
    if streak <= 0 or not enabled:
        return base
    candidate = base * (2 ** min(streak, 10))
    if cap > 0:
        return min(candidate, cap)
    return candidate


def _read_checkpoint_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _apply_checkpoint_payload(payload: dict[str, Any], state: AutoloopState) -> int | None:
    try:
        cycle = int(payload.get("cycle", 0))
    except (TypeError, ValueError):
        cycle = 0
    state_payload = payload.get("state")
    if isinstance(state_payload, dict):
        for key in (
            "previous_signature",
            "stagnation_streak",
            "scan_clean_streak",
            "scan_last_head",
            "wup_seen_events",
            "last_driven_prompt",
            "last_llm_reflection_summary",
            "last_llm_reflection_ts",
            "last_operator_needs_input_signature",
            "last_operator_needs_input_ticket_id",
            "last_message_sent_ts",
            "last_message_sent_ide",
            "last_driven_ticket_id",
            "last_autopilot_status",
            "last_submit_unverified_ts",
            "last_submit_unverified_ticket_id",
            "submit_unverified_streak",
            "last_submit_failure_signature",
            "pending_submit_strategy_hint",
            "autopilot_plugin_ready",
            "telemetry_autopilot_idle_streak_skips",
            "telemetry_scan_after_idle_runs",
            "telemetry_scan_after_idle_tickets_applied",
            "last_scan_after_idle_ts",
            "last_scan_create_failed_fingerprint",
            "last_scan_create_failed_ts",
            "last_scan_duplicate_fingerprint",
            "last_scan_duplicate_ts",
        ):
            if key in state_payload:
                setattr(state, key, state_payload[key])
        events = state_payload.get("autopilot_events")
        if isinstance(events, list):
            state.autopilot_events = [ev for ev in events if isinstance(ev, dict)]
    return cycle if cycle > 0 else None


def load_loop_checkpoint(
    path: Path,
    *,
    state: AutoloopState,
    stdio_format: str = "human",
) -> int | None:
    from koru.bounded_contexts.autonomous_checkpoint.application import (
        AutonomousCheckpointCommandService,
    )
    from koru.bounded_contexts.autonomous_checkpoint.commands import (
        RestoreLoopCheckpointCommand,
    )
    from koru.cqrs import runtime_for_storage_dir

    return AutonomousCheckpointCommandService(runtime=runtime_for_storage_dir(path.parent)).restore(
        RestoreLoopCheckpointCommand(path=path, state=state, stdio_format=stdio_format),
    )


def _build_checkpoint_payload(
    *,
    cycle: int,
    state: AutoloopState,
    queue_status: str,
    waiting_ticket: str,
) -> dict[str, Any]:
    return {
        "cycle": cycle,
        "saved_at": time.time(),
        "queue_status": queue_status,
        "waiting_ticket": waiting_ticket,
        "state": {
            "previous_signature": state.previous_signature,
            "stagnation_streak": state.stagnation_streak,
            "scan_clean_streak": state.scan_clean_streak,
            "scan_last_head": state.scan_last_head,
            "wup_seen_events": state.wup_seen_events,
            "autopilot_events": list(state.autopilot_events)[-50:],
            "last_driven_prompt": state.last_driven_prompt,
            "last_llm_reflection_summary": state.last_llm_reflection_summary,
            "last_llm_reflection_ts": state.last_llm_reflection_ts,
            "last_operator_needs_input_signature": state.last_operator_needs_input_signature,
            "last_operator_needs_input_ticket_id": state.last_operator_needs_input_ticket_id,
            "last_message_sent_ts": state.last_message_sent_ts,
            "last_message_sent_ide": state.last_message_sent_ide,
            "last_driven_ticket_id": state.last_driven_ticket_id,
            "last_autopilot_status": state.last_autopilot_status,
            "last_submit_unverified_ts": state.last_submit_unverified_ts,
            "last_submit_unverified_ticket_id": state.last_submit_unverified_ticket_id,
            "submit_unverified_streak": state.submit_unverified_streak,
            "last_submit_failure_signature": state.last_submit_failure_signature,
            "pending_submit_strategy_hint": state.pending_submit_strategy_hint,
            "autopilot_plugin_ready": state.autopilot_plugin_ready,
            "telemetry_autopilot_idle_streak_skips": state.telemetry_autopilot_idle_streak_skips,
            "telemetry_scan_after_idle_runs": state.telemetry_scan_after_idle_runs,
            "telemetry_scan_after_idle_tickets_applied": (
                state.telemetry_scan_after_idle_tickets_applied
            ),
            "last_scan_after_idle_ts": state.last_scan_after_idle_ts,
            "last_scan_create_failed_fingerprint": state.last_scan_create_failed_fingerprint,
            "last_scan_create_failed_ts": state.last_scan_create_failed_ts,
            "last_scan_duplicate_fingerprint": state.last_scan_duplicate_fingerprint,
            "last_scan_duplicate_ts": state.last_scan_duplicate_ts,
        },
    }


def _write_checkpoint_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(f"{json.dumps(payload, ensure_ascii=True, indent=2)}\n", encoding="utf-8")
    tmp.replace(path)


def save_loop_checkpoint(
    path: Path,
    *,
    cycle: int,
    state: AutoloopState,
    queue_status: str,
    waiting_ticket: str,
) -> None:
    from koru.bounded_contexts.autonomous_checkpoint.application import (
        AutonomousCheckpointCommandService,
    )
    from koru.bounded_contexts.autonomous_checkpoint.commands import SaveLoopCheckpointCommand
    from koru.cqrs import runtime_for_storage_dir

    AutonomousCheckpointCommandService(runtime=runtime_for_storage_dir(path.parent)).save(
        SaveLoopCheckpointCommand(
            path=path,
            cycle=cycle,
            state=state,
            queue_status=queue_status,
            waiting_ticket=waiting_ticket,
        ),
    )


def status_in_skip_list(status: str, skip_statuses: str) -> bool:
    return status.lower() in {
        item.strip().lower() for item in skip_statuses.split(",") if item.strip()
    }


__all__ = [
    "compute_backoff_sleep",
    "current_head",
    "load_loop_checkpoint",
    "queue_loop_waiting_ticket_label",
    "save_loop_checkpoint",
    "status_in_skip_list",
]
