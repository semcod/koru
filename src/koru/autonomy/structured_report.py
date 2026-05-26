"""Structured cycle report for ``koru auto`` shell output.

Replaces the verbose OBS flood with a clean three-section report::

    [10:38:14] koru ▸ ══════ cycle 38 ══════
    [10:38:14] koru ▸ DIAG: queue=waiting_input ticket=PLF-013 wup=ok streak=2
    [10:38:14] koru ▸ DIAG: blocker=plugin_missing ide=antigravity
    [10:38:14] koru ▸ PLAN: skip drive → wait for plugin reconnect
    [10:38:14] koru ▸ ACTION: koru replay 'ide reload-window antigravity'
    [10:38:14] koru ▸ ACTION: koru replay 'trace show-decisions'
    [10:38:14] koru ▸ ──────────────────────

Each ACTION line is a valid shell command that can be copy-pasted to execute.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from koru.autonomy.replay_actions import (
    ReplayAction,
    autopilot_retry_drive,
    ide_connect_plugin,
    ide_reload_window,
    scan_force,
    ticket_input,
    ticket_open,
    trace_show_decisions,
    trace_show_interfaces,
    wup_show_health,
)

# Header/footer decoration constants.
_CYCLE_HEADER = "══════"
_CYCLE_FOOTER = "──────────────────────"


# ---------------------------------------------------------------------------
# Diagnosis section builders
# ---------------------------------------------------------------------------


def _diag_status_line(
    *,
    cycle: int,
    queue_status: str,
    waiting_ticket: str,
    wup_status: str,
    diag_status: str,
    stagnation_streak: int,
) -> str:
    """Primary status line: queue/ticket/health in one glance."""
    parts = [f"queue={queue_status}"]
    if waiting_ticket and waiting_ticket != "-":
        parts.append(f"ticket={waiting_ticket}")
    parts.append(f"wup={wup_status}")
    if diag_status not in ("skipped", "off", ""):
        parts.append(f"diagnostics={diag_status}")
    if stagnation_streak > 0:
        parts.append(f"streak={stagnation_streak}")
    return " ".join(parts)


def _diag_blocker_line(
    *,
    autopilot_status: str,
    autopilot_ide: str,
) -> str | None:
    """Secondary line: blocker detail (only if blocked)."""
    blocker = _extract_blocker(autopilot_status)
    if not blocker:
        return None
    parts = [f"blocker={blocker}"]
    if autopilot_ide:
        parts.append(f"ide={autopilot_ide}")
    return " ".join(parts)


def _diag_blocker_detail(autopilot_status: str) -> str | None:
    """Tertiary line: compact blocker reason (mismatch hashes, etc.)."""
    raw = (autopilot_status or "").strip()
    if "rejected:" not in raw:
        return None
    # Extract the "rejected: ..." portion and compact it
    _, _, detail = raw.partition("rejected:")
    detail = detail.strip()
    if not detail:
        return None
    # Shorten hash pairs for readability
    compact = detail
    for token in detail.split():
        if "=" in token and len(token.split("=", 1)[-1]) > 12:
            key, _, val = token.partition("=")
            compact = compact.replace(token, f"{key}={val[:7]}")
    return compact[:120]


def _extract_blocker(autopilot_status: str) -> str:
    """Extract the blocker name from an autopilot status like ``skipped(plugin_missing)``."""
    status = (autopilot_status or "").strip().lower()
    if status.startswith("skipped("):
        return status[len("skipped("):].rstrip(")").strip()
    if status.startswith("failed"):
        if "submit_unverified" in status or "submit_failed" in status:
            return "manual_send_required"
        return "drive_failed"
    return ""


# ---------------------------------------------------------------------------
# Plan section builders
# ---------------------------------------------------------------------------


def _plan_lines(
    *,
    queue_status: str,
    autopilot_status: str,
    waiting_ticket: str,
    sleep_seconds: float,
) -> list[str]:
    """Human-readable plan lines (what koru intends to do next)."""
    blocker = _extract_blocker(autopilot_status)
    lines: list[str] = []

    if blocker == "plugin_missing":
        lines.append("skip drive → wait for plugin reconnect")
        lines.append(f"sleep {sleep_seconds:g}s, then recheck queue for {waiting_ticket}")
    elif blocker == "chat_activity":
        lines.append(f"skip drive → chat cooldown active for {waiting_ticket}")
        lines.append(f"sleep {sleep_seconds:g}s, then reconsider redrive")
    elif blocker == "drive_failed":
        lines.append("drive failed → retry next cycle")
        lines.append(f"sleep {sleep_seconds:g}s, then rerun queue")
    elif blocker == "manual_send_required":
        lines.append("submit not verified → do not redrive blindly")
        lines.append(f"sleep {sleep_seconds:g}s, then validate trace for {waiting_ticket}")
    elif queue_status == "idle":
        lines.append("queue idle → all tickets done")
        lines.append("strategy: scan/discovery for new work")
    elif queue_status == "waiting_input":
        lines.append(f"waiting on {waiting_ticket} → operator input needed")
        lines.append(f"sleep {sleep_seconds:g}s, then recheck")
    elif queue_status in ("completed", "failed"):
        lines.append(f"queue {queue_status} → pick next ticket")
    else:
        lines.append(f"continue cycle → queue={queue_status}")

    return lines


# ---------------------------------------------------------------------------
# Action section builders
# ---------------------------------------------------------------------------


def _build_cycle_actions(
    *,
    queue_status: str,
    autopilot_status: str,
    autopilot_ide: str,
    waiting_ticket: str,
    base_url: str = "http://127.0.0.1:8765",
) -> list[ReplayAction]:
    """Build the set of ReplayActions relevant to the current cycle state."""
    blocker = _extract_blocker(autopilot_status)
    actions: list[ReplayAction] = []

    # Always include trace inspection
    actions.append(trace_show_decisions(base_url))

    # Blocker-specific actions
    if blocker == "plugin_missing":
        actions.append(ide_reload_window(autopilot_ide or "auto"))
        actions.append(ide_connect_plugin(autopilot_ide or "auto"))
        actions.append(trace_show_interfaces(base_url))

    elif blocker == "drive_failed" and waiting_ticket and waiting_ticket != "-":
        actions.append(autopilot_retry_drive(autopilot_ide or "auto", waiting_ticket))

    # Queue-specific actions
    if queue_status == "waiting_input" and waiting_ticket and waiting_ticket != "-":
        actions.append(ticket_input(waiting_ticket))
        actions.append(ticket_open(waiting_ticket, base_url))

    if queue_status == "idle":
        actions.append(scan_force())

    # WUP health if diagnostics failed
    if "diagnostics_fail" in (autopilot_status or "").lower():
        actions.append(wup_show_health())

    return actions


# ---------------------------------------------------------------------------
# Full report renderer
# ---------------------------------------------------------------------------


def emit_structured_cycle_report(
    *,
    cycle: int,
    queue_status: str,
    waiting_ticket: str,
    wup_status: str,
    diag_status: str,
    autopilot_status: str,
    autopilot_ide: str,
    stagnation_streak: int,
    sleep_seconds: float,
    base_url: str = "http://127.0.0.1:8765",
    activity_fn: Callable[[str, str], None],
    idle_context: str = "",
) -> list[ReplayAction]:
    """Emit the full structured cycle report and return the actions list.

    ``activity_fn(category, message)`` is called for each line.  The caller
    is expected to forward to ``activity_log.activity()``.

    Returns the list of ``ReplayAction`` objects so the caller can persist
    them as observability control-command events.
    """
    # Header
    activity_fn("KORUAUTONOMOUS", f"{_CYCLE_HEADER} cycle {cycle} {_CYCLE_HEADER}")

    # DIAG section
    status_line = _diag_status_line(
        cycle=cycle,
        queue_status=queue_status,
        waiting_ticket=waiting_ticket,
        wup_status=wup_status,
        diag_status=diag_status,
        stagnation_streak=stagnation_streak,
    )
    activity_fn("DIAG", status_line)

    blocker_line = _diag_blocker_line(
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
    )
    if blocker_line:
        activity_fn("DIAG", blocker_line)

    blocker_detail = _diag_blocker_detail(autopilot_status)
    if blocker_detail:
        activity_fn("DIAG", blocker_detail)

    # PLAN section
    for line in _plan_lines(
        queue_status=queue_status,
        autopilot_status=autopilot_status,
        waiting_ticket=waiting_ticket,
        sleep_seconds=sleep_seconds,
    ):
        activity_fn("PLAN", line)

    # ACTION section
    actions = _build_cycle_actions(
        queue_status=queue_status,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        waiting_ticket=waiting_ticket,
        base_url=base_url,
    )
    for action in actions:
        if action.replayable:
            activity_fn("ACTION", action.to_shell())
        else:
            activity_fn("ACTION", f"[manual] {action.label}: {action.to_dsl()}")

    if idle_context:
        activity_fn("DIAG", idle_context)

    # Footer
    activity_fn("KORUAUTONOMOUS", _CYCLE_FOOTER)

    return actions


__all__ = [
    "emit_structured_cycle_report",
]
