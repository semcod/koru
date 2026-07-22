"""Thin bridge from Gillm recovery diagnostics to Koru operator replies."""

from __future__ import annotations

from typing import Any

from gillm.recovery import diagnose_drive_reply, probe_environment, recovery_hints_for_reload


def recovery_hints_from_drive_reply(reply: dict[str, Any]) -> list[str]:
    return diagnose_drive_reply(reply).recovery


def recovery_hints_for_ide_reload(
    *,
    wayland: bool | None = None,
    focus_failed: bool = False,
) -> list[str]:
    if wayland is None:
        wayland = probe_environment().wayland
    return recovery_hints_for_reload(wayland=wayland, focus_failed=focus_failed)


def enrich_drive_reply_with_recovery(reply: dict[str, Any]) -> dict[str, Any]:
    """Attach structured Gillm recovery hints to a drive reply in-place."""
    ctx = diagnose_drive_reply(reply)
    reply.setdefault("diagnostics", {})
    if isinstance(reply["diagnostics"], dict):
        reply["diagnostics"]["recovery"] = ctx.recovery
    reply["recovery"] = ctx.recovery
    reply["failure_kind"] = ctx.kind
    reply["retryable"] = ctx.retryable
    return reply
