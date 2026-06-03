"""Factory functions for known replay actions."""

from __future__ import annotations

import shlex

from koru.autonomy.replay_types import ReplayAction


def ide_reload_window(ide: str) -> ReplayAction:
    """IDE: Developer -> Reload Window."""
    return ReplayAction(
        domain="ide",
        verb="reload-window",
        positional=(ide,),
        label=f"Reload {ide} IDE window",
        replayable=False,
        validate_cmd=f"koru ide doctor --ide {shlex.quote(ide)}",
        safe=False,
        requires_active_window=True,
    )


def ide_connect_plugin(ide: str) -> ReplayAction:
    """IDE: koru -> Connect autopilot daemon."""
    return ReplayAction(
        domain="ide",
        verb="connect-plugin",
        positional=(ide,),
        label=f"Connect autopilot plugin for {ide}",
        replayable=False,
        validate_cmd=f"koru autopilot status --ide {shlex.quote(ide)}",
        safe=False,
        requires_active_window=True,
    )


def trace_show_decisions(base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Show the autonomy decision trace via dashboard API."""
    cmd = f"curl -s {base_url}/api/autonomy/trace | jq .decisions"
    return ReplayAction(
        domain="trace",
        verb="show-decisions",
        label="Show autonomy decision trace",
        args={"url": base_url},
        validate_cmd=cmd,
    )


def trace_show_interfaces(base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Show interface families and blockers via dashboard API."""
    cmd = f"curl -s {base_url}/api/interfaces | jq '.families, .blockers'"
    return ReplayAction(
        domain="trace",
        verb="show-interfaces",
        label="Show interface families and blockers",
        args={"url": base_url},
        validate_cmd=cmd,
    )


def ticket_input(ticket_id: str, prompt: str = "", note: str = "") -> ReplayAction:
    """Mark a planfile ticket as needing input."""
    args: dict[str, str] = {}
    if prompt:
        args["prompt"] = prompt
    if note:
        args["note"] = note
    return ReplayAction(
        domain="ticket",
        verb="input",
        positional=(ticket_id,),
        args=args,
        label=f"Mark {ticket_id} as needing input",
    )


def ticket_open(ticket_id: str, base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Open a ticket in the dashboard."""
    return ReplayAction(
        domain="ticket",
        verb="open",
        positional=(ticket_id,),
        args={"url": base_url},
        label=f"Open {ticket_id} in dashboard",
    )


def scan_force() -> ReplayAction:
    """Force a fresh koru scan (clear project cache first)."""
    return ReplayAction(
        domain="scan",
        verb="force",
        label="Force fresh project scan",
        validate_cmd="ls -d project/ 2>/dev/null && echo 'project dir exists' || echo 'clean'",
    )


def wup_show_health() -> ReplayAction:
    """Show WUP service health."""
    return ReplayAction(
        domain="wup",
        verb="show-health",
        label="Show WUP service health",
        validate_cmd="cat .wup/service-health.json 2>/dev/null | jq . || echo 'no health file'",
    )


def autopilot_retry_drive(ide: str, ticket_id: str) -> ReplayAction:
    """Retry an autopilot drive for a specific ticket."""
    return ReplayAction(
        domain="autopilot",
        verb="retry-drive",
        positional=(ticket_id,),
        args={"ide": ide},
        label=f"Retry autopilot drive for {ticket_id}",
        safe=False,
    )


__all__ = [
    "autopilot_retry_drive",
    "ide_connect_plugin",
    "ide_reload_window",
    "scan_force",
    "ticket_input",
    "ticket_open",
    "trace_show_decisions",
    "trace_show_interfaces",
    "wup_show_health",
]
