"""Bridge gillm recovery diagnostics into Koru operator surfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

try:
    from gillm.recovery import diagnose_drive_reply, probe_environment, recovery_hints_for_reload
except ImportError:
    @dataclass(frozen=True)
    class EnvironmentDiagnostics:
        session: str
        wayland: bool
        backends: dict[str, bool]
        selected_backend: str | None

        def to_dict(self) -> dict[str, Any]:
            return {
                "session": self.session,
                "wayland": self.wayland,
                "backends": dict(self.backends),
                "selected_backend": self.selected_backend,
            }

    @dataclass
    class DriveFailureContext:
        kind: str
        reason: str = ""
        message: str = ""
        backend: str | None = None
        retryable: bool = False
        recovery: list[str] = field(default_factory=list)
        environment: EnvironmentDiagnostics | None = None

    def _is_wayland_session() -> bool:
        return (
            os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
            or bool(os.environ.get("WAYLAND_DISPLAY"))
        )

    def probe_environment() -> EnvironmentDiagnostics:
        session = os.environ.get("XDG_SESSION_TYPE", "").strip() or "unknown"
        return EnvironmentDiagnostics(
            session=session,
            wayland=_is_wayland_session(),
            backends={},
            selected_backend=None,
        )

    def recovery_hints_for_reload(*, wayland: bool, focus_failed: bool = False) -> list[str]:
        if wayland and focus_failed:
            return [
                "Install ydotool and ensure your user is in the input group",
                "Run koru from a terminal inside the IDE",
                "Manually reload the IDE: Developer: Reload Window",
                "Set KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to allow window reuse reload",
            ]
        if wayland:
            return [
                "Install wtype or ydotool for Wayland keyboard injection",
                "Prefer the koru autopilot VSIX plugin over keyboard fallback on Wayland",
                "Calibrate submit: koru: Capture submit button position in the IDE",
            ]
        return [
            "Install wmctrl or xdotool for X11 window focus",
            "Run koru from the IDE integrated terminal when possible",
            "Developer: Reload Window after installing a new VSIX",
        ]

    def _classify_failure(
        *,
        ok: bool,
        reason: str = "",
        message: str = "",
        backend: str | None = None,
    ) -> str:
        if ok:
            return "ok"
        blob = f"{reason} {message}".lower()
        if "no connected autopilot plugin" in blob:
            return "plugin_unavailable"
        if "version mismatch" in blob or "build mismatch" in blob:
            return "plugin_version_mismatch"
        if "submit" in blob and ("unverified" in blob or "could not be verified" in blob):
            return "submit_unverified"
        if "input_busy" in blob or "chat_input_not_empty" in blob or "unrelated draft" in blob:
            return "input_busy"
        if "focus" in blob and ("failed" in blob or "not focused" in blob):
            return "focus_failed"
        if (
            "brak kalibracji" in blob
            or "no calibrated profile" in blob
            or "missing profile" in blob
        ):
            return "no_calibrated_profile"
        if "wayland" in blob and ("blocked" in blob or "without ydotool" in blob):
            return "wayland_injection_blocked"
        if "no keyboard injection backend" in blob or "xdotool missing" in blob:
            return "no_keyboard_backend"
        if backend and "wayland" in blob:
            return "wayland_injection_blocked"
        return "unknown"

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _hints_for_kind(kind: str, ctx: DriveFailureContext) -> list[str]:
        if kind == "plugin_unavailable":
            return [
                "Reload the IDE window (Developer: Reload Window)",
                "Run koru: Connect autopilot daemon in the IDE command palette",
                "Verify the daemon socket: koru autopilot status",
            ]
        if kind == "plugin_version_mismatch":
            return [
                "Run koru autopilot manage --ide <ide> --fix",
                "Developer: Reload Window so the extension host loads the installed VSIX",
                "Run koru: Connect autopilot daemon after reload",
            ]
        if kind == "submit_unverified":
            return [
                "Ensure the chat input is focused before submit",
                "Calibrate submit click: koru: Capture submit button position",
                "On Cursor/Wayland prefer plugin bridge over keyboard fallback",
                "Clear stale composer draft and retry the drive",
            ]
        if kind == "input_busy":
            return [
                "Clear the IDE chat composer draft manually",
                "Retry the drive after the input is empty",
            ]
        if kind == "focus_failed":
            return recovery_hints_for_reload(
                wayland=bool(ctx.environment and ctx.environment.wayland),
                focus_failed=True,
            )
        if kind == "no_calibrated_profile":
            return [
                "Calibrate chat anchor: koru autopilot calibrate --ide <ide>",
                "Or install the koru autopilot plugin and use plugin_socket backend",
            ]
        if kind == "wayland_injection_blocked":
            return recovery_hints_for_reload(wayland=True)
        if kind == "no_keyboard_backend":
            if ctx.environment and ctx.environment.wayland:
                return [
                    "Install wtype or ydotool for Wayland keyboard injection",
                    "Add your user to the input/uinput group for ydotool",
                ]
            return [
                "Install xdotool on X11",
                "Use the koru autopilot VSIX plugin instead of keyboard fallback",
            ]
        if ctx.message or ctx.reason:
            return [f"Investigate drive failure: {ctx.reason or ctx.message}".strip()]
        return ["Retry the drive or inspect koru autopilot status"]

    def diagnose_drive_reply(reply: dict[str, Any]) -> DriveFailureContext:
        ok = bool(reply.get("ok", False))
        reason = str(reply.get("reason") or reply.get("submit_failure_reason") or "")
        message = str(reply.get("message") or "")
        backend = reply.get("backend")
        backend_str = str(backend) if backend is not None else None
        diagnostics = reply.get("diagnostics")
        embedded_recovery = (
            diagnostics.get("recovery")
            if isinstance(diagnostics, dict)
            else None
        )
        kind = _classify_failure(ok=ok, reason=reason, message=message, backend=backend_str)
        ctx = DriveFailureContext(
            kind=kind,
            reason=reason,
            message=message,
            backend=backend_str,
            retryable=kind
            not in {
                "plugin_version_mismatch",
                "plugin_unavailable",
                "no_calibrated_profile",
            },
            environment=probe_environment(),
        )
        if isinstance(embedded_recovery, list) and embedded_recovery:
            ctx.recovery = [str(item) for item in embedded_recovery]
        else:
            hints = _hints_for_kind(kind, ctx)
            if ctx.environment and ctx.environment.wayland:
                hints = _dedupe([*hints, *recovery_hints_for_reload(wayland=True)])
            ctx.recovery = hints
        return ctx


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
    """Attach structured recovery hints to a drive reply dict in-place."""
    ctx = diagnose_drive_reply(reply)
    reply.setdefault("diagnostics", {})
    if isinstance(reply["diagnostics"], dict):
        reply["diagnostics"]["recovery"] = ctx.recovery
    reply["recovery"] = ctx.recovery
    reply["failure_kind"] = ctx.kind
    reply["retryable"] = ctx.retryable
    return reply
