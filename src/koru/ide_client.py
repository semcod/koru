"""IDE control client abstraction for `koru` runtime paths.

This module is the anti-corruption boundary between orchestration code
(`autonomous`, agent backends, future queue runners) and the concrete
legacy autopilot socket client.
"""


from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


class IDEControlClient(Protocol):
    """Minimal interface `koru` runtime code expects from an IDE client."""

    def is_running(self) -> bool: ...

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
        strategy_hint: str | None = None,
    ) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    def shutdown(self) -> dict[str, Any]: ...


def _semantic_drive_operator_lines(reply: dict[str, Any], *, ide: str) -> list[str]:
    if isinstance(reply.get("drive_dsl_operator"), list):
        return []
    try:
        from koru.autonomy.ide_operator_guidance import classify_drive_failure_guidance
    except Exception:
        return []
    lines = classify_drive_failure_guidance(reply, ide=ide)
    return list(lines or [])


@dataclass
class LegacyAutopilotClientAdapter:
    """Expose legacy :class:`AutopilotClient` through :class:`IDEControlClient`."""

    client: AutopilotClient

    def is_running(self) -> bool:
        return bool(self.client.is_running())

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
        strategy_hint: str | None = None,
    ) -> dict[str, Any]:
        from koru.activity_log import activity

        activity(
            "CHAT",
            f"drive → ide={ide} submit={submit} require_plugin={require_plugin} "
            f"strategy_hint={strategy_hint or '-'} "
            f"({len(text)} znaków)",
            preview=text,
            data={
                "ide": ide,
                "submit": submit,
                "require_plugin": require_plugin,
                "strategy_hint": strategy_hint or "",
                "chars": len(text),
            },
        )
        reply = self.client.drive(
            text,
            submit=submit,
            ide=ide,
            require_plugin=require_plugin,
            strategy_hint=strategy_hint,
        )
        backend = reply.get("backend", "?")
        ok = bool(reply.get("ok", True))
        verification = reply.get("verification", "-")
        summary_bits = [f"verification={verification}"]
        for key in ("winning_focus_open", "winning_paste", "winning_submit", "event"):
            value = reply.get(key)
            if value:
                summary_bits.append(f"{key}={value}")
        activity(
            "CHAT",
            (
                f"drive wynik: ok={ok} backend={backend} "
                f"tool_id={reply.get('tool_id', '-')} {' '.join(summary_bits)}"
            ),
            data={
                "ide": ide,
                "ok": ok,
                "backend": backend,
                "verification": verification,
                "tool_id": reply.get("tool_id", "-"),
                "message": reply.get("message", ""),
                "details": reply.get("details", ""),
                "event": reply.get("event", ""),
                "winning_focus_open": reply.get("winning_focus_open", ""),
                "winning_paste": reply.get("winning_paste", ""),
                "winning_submit": reply.get("winning_submit", ""),
                "diagnostics": reply.get("diagnostics", {}),
            },
        )
        # Surface the Koru Drive DSL — one line per integration step.
        # This is the transparent decision log the operator asked for:
        # it explains exactly which routes the plugin tried for focus /
        # paste / submit, whether each one succeeded, and why the
        # failing step failed (instead of the older "drive wynik: ok=False"
        # one-liner that hid everything in opaque ack fields).
        dsl_lines = reply.get("drive_dsl")
        if isinstance(dsl_lines, list):
            for raw_line in dsl_lines:
                line = str(raw_line).strip()
                if not line:
                    continue
                activity("DSL", line, data={"ide": ide, "phase": "step"})
        outcome_line = reply.get("drive_dsl_outcome")
        if outcome_line:
            activity(
                "DSL",
                str(outcome_line),
                data={"ide": ide, "phase": "outcome"},
            )
        operator_lines = reply.get("drive_dsl_operator")
        if isinstance(operator_lines, list):
            for raw_line in operator_lines:
                line = str(raw_line).strip()
                if not line:
                    continue
                activity("DSL", line, data={"ide": ide, "phase": "operator"})
        else:
            for line in _semantic_drive_operator_lines(reply, ide=ide):
                activity("DSL", str(line), data={"ide": ide, "phase": "operator"})
        return reply

    def status(self) -> dict[str, Any]:
        return self.client.status()

    def shutdown(self) -> dict[str, Any]:
        return self.client.shutdown()


def adapt_legacy_autopilot_client(client: AutopilotClient) -> IDEControlClient:
    """Wrap an existing legacy autopilot client as :class:`IDEControlClient`."""

    return LegacyAutopilotClientAdapter(client=client)


def build_legacy_ide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
) -> IDEControlClient:
    """Construct :class:`IDEControlClient` backed by legacy autopilot socket client."""

    from koru.autopilot.client import AutopilotClient

    return adapt_legacy_autopilot_client(
        AutopilotClient(socket_path=socket_path, timeout=timeout),
    )


def build_koruide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
) -> IDEControlClient:
    """Construct :class:`IDEControlClient` backed by the `koruide` package client."""

    from koruide.client import build_client as build_koruide_package_client

    return build_koruide_package_client(socket_path=socket_path, timeout=timeout)


def build_ide_client(
    *,
    socket_path: Path | None = None,
    timeout: float = 5.0,
    backend: str | None = None,
) -> IDEControlClient:
    """Construct an IDE client for the selected backend.

    Selection order:

    1. Explicit ``backend`` argument.
    2. ``KORU_IDE_BACKEND`` environment variable.
    3. Fallback to ``legacy``.
    """

    choice = (backend or os.environ.get("KORU_IDE_BACKEND", "legacy")).strip().lower()
    if choice == "gillm":
        from koru.ide_adapters.gillm_client import build_gillm_ide_client

        return build_gillm_ide_client()
    if choice == "koruide":
        return build_koruide_client(socket_path=socket_path, timeout=timeout)
    return build_legacy_ide_client(socket_path=socket_path, timeout=timeout)


__all__ = [
    "IDEControlClient",
    "LegacyAutopilotClientAdapter",
    "adapt_legacy_autopilot_client",
    "build_legacy_ide_client",
    "build_koruide_client",
    "build_ide_client",
]
