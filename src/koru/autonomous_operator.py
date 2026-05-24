"""Operator and pre-check helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_VSCODE_FAMILY_PLUGIN_IDES = frozenset(
    {"antigravity", "cursor", "vscode", "vscodium", "windsurf"},
)


def run_mcp_provision(
    project: Path,
    stdio_format: str,
    *,
    stdio_info: Any,
) -> bool:
    """Run MCP workspace provision and return True if it ran."""
    mcp_provision_ran = False
    try:
        from koru.mcp_provision import ensure_koru_mcp_not_disabled

        for row in ensure_koru_mcp_not_disabled(project):
            mcp_provision_ran = True
            stdio_info(
                f"koru autonomous: {row['action']} -> {row['path']}",
                fmt=stdio_format,
            )
    except (OSError, TypeError, ValueError) as exc:
        stdio_info(
            f"koru autonomous: mcp workspace refresh skipped ({exc})",
            fmt=stdio_format,
        )
    return mcp_provision_ran


def _ensure_trusted_publisher_for_plugin(
    autopilot_ide: str,
    *,
    stdio_info: Any,
    emit_fmt: str,
) -> None:
    if autopilot_ide not in _VSCODE_FAMILY_PLUGIN_IDES:
        return
    from koru.ide_adapters import shared

    if shared.publisher_trusted(autopilot_ide) is not False:
        return
    if shared.add_trusted_publisher(autopilot_ide):
        stdio_info(
            f"koru autonomous: dodano „{shared.PUBLISHER_ID}” do "
            f"extensions.trustedPublishers ({autopilot_ide}) — wymagany Reload Window",
            fmt=emit_fmt,
        )


def _extension_active_in_latest_session(autopilot_ide: str) -> bool | None:
    if autopilot_ide not in _VSCODE_FAMILY_PLUGIN_IDES:
        return None
    from koru.ide_adapters import shared

    return shared.extension_activated_in_exthost(autopilot_ide)


def setup_autopilot_plugin(
    args: Any,
    autopilot_ide: str,
    socket_path: Path | None,
    client: Any | None,
    *,
    project: Path | None = None,
    install_plugin_for_ide: Any,
    format_plugin_install_result: Any,
    allow_keyboard_fallback: Any,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool | None:
    """Install and wait for autopilot plugin if enabled."""
    plugin_connected: bool | None = None
    if not args.enable_autopilot or socket_path is None:
        return plugin_connected

    plugin_result = install_plugin_for_ide(ide=autopilot_ide, socket_path=socket_path)
    stdio_info(format_plugin_install_result(plugin_result), fmt=args.emit_events)
    plugin_install_status = str(getattr(plugin_result, "status", "") or "")
    if plugin_result.status == "unsupported":
        plugin_connected = False
        stdio_info(
            "koru autonomous: autopilot plugin unsupported for "
            f"ide={autopilot_ide}; using keyboard/OS-injector path",
            fmt=args.emit_events,
        )
        import os as _os

        env_lane = _os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
        if env_lane and env_lane.lower() == str(autopilot_ide).lower():
            stdio_info(
                "koru autonomous: ⚠ KORU_AUTOPILOT_INSTANCE="
                f"{env_lane} forces an unsupported IDE. "
                "Plugin-mode is unavailable; the OS injector path is unreliable on Wayland. "
                "To switch the autopilot lane to a supported IDE, run one of:\n"
                "  unset KORU_AUTOPILOT_INSTANCE             # auto-pick from running IDEs\n"
                "  export KORU_AUTOPILOT_INSTANCE=cursor     # or vscode / vscodium / windsurf\n"
                "Supported lanes: cursor, vscode, vscodium, windsurf "
                "(see docs: docs/IDE_PROTOCOL.md).",
                fmt=args.emit_events,
            )
    elif client is not None and not allow_keyboard_fallback():
        skip_plugin_wait = False
        reload_after_install = None
        if plugin_install_status in {"installed", "already_installed"}:
            _ensure_trusted_publisher_for_plugin(
                autopilot_ide,
                stdio_info=stdio_info,
                emit_fmt=args.emit_events,
            )
            active = _extension_active_in_latest_session(autopilot_ide)
            if active is False:
                from koru.ide_adapters import shared
                from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

                reload_after_install = try_reload_vscode_family_ide(
                    autopilot_ide,
                    project=project,
                )
                reload = reload_after_install
                if reload.attempted:
                    if reload.ok:
                        stdio_info(
                            "koru autonomous: automatyczny Reload Window "
                            f"({reload.method}) — czekam na plugin…",
                            fmt=args.emit_events,
                        )
                    else:
                        stdio_info(
                            "koru autonomous: automatyczny reload IDE nie powiódł się "
                            f"({reload.method or '-'}: {reload.detail or 'unknown'})",
                            fmt=args.emit_events,
                        )
                        for line in shared.extension_reload_required_lines(
                            autopilot_ide,
                            color=args.emit_events == "human",
                        ):
                            stdio_info(line, fmt=args.emit_events)
                else:
                    for line in shared.extension_reload_required_lines(
                        autopilot_ide,
                        color=args.emit_events == "human",
                    ):
                        stdio_info(line, fmt=args.emit_events)

                if not reload.ok:
                    from koru.autonomy.env import keyboard_fallback_when_plugin_missing

                    if keyboard_fallback_when_plugin_missing(autopilot_ide):
                        stdio_info(
                            "koru autonomous: plugin nieaktywny — włączam fallback "
                            "klawiatury/OS-injectora (Wayland); ustaw profil: "
                            "task koru:ide-os:calibrate IDE=cursor",
                            fmt=args.emit_events,
                        )
                        skip_plugin_wait = True
                    else:
                        stdio_info(
                            "koru autonomous: pomijam oczekiwanie na plugin "
                            "(wtyczka nie załadowana w extension host)",
                            fmt=args.emit_events,
                        )
                        skip_plugin_wait = True
                # When reload succeeded, fall through to wait_for_plugin below.

        if skip_plugin_wait:
            plugin_connected = False
        else:
            wait_seconds = max(0.0, args.autopilot_plugin_wait_seconds)
            if (
                reload_after_install is not None
                and reload_after_install.ok
            ):
                wait_seconds = max(wait_seconds, 30.0)
            plugin_ready = wait_for_plugin(
                client,
                autopilot_ide,
                timeout_seconds=wait_seconds,
                stdio_format=args.emit_events,
            )
            plugin_connected = plugin_ready
            if plugin_ready:
                stdio_info(
                    f"koru autonomous: autopilot plugin connected ide={autopilot_ide}",
                    fmt=args.emit_events,
                )
            else:
                stdio_info(
                    "koru autonomous: no connected autopilot plugin "
                    f"for ide={autopilot_ide} after {wait_seconds:.1f}s; "
                    "autopilot drive will be skipped until it connects",
                    fmt=args.emit_events,
                )
                if plugin_install_status in {"installed", "already_installed"}:
                    from koru.ide_adapters import shared

                    for line in shared.extension_reload_required_lines(
                        autopilot_ide,
                        color=args.emit_events == "human",
                    ):
                        stdio_info(line, fmt=args.emit_events)
    return plugin_connected


def run_operator_pipeline(
    args: Any,
    project: Path,
    startup_probe: Any,
    plugin_connected: bool | None,
    mcp_provision_ran: bool,
    correlation_id: str,
    *,
    format_hints: Any,
    run_pipeline: Any,
    stdio_info: Any,
) -> None:
    """Run operator pipeline if enabled."""
    for hint in format_hints(startup_probe, plugin_connected=plugin_connected):
        stdio_info(hint, fmt=args.emit_events)

    if args.operator_pipeline:
        run_pipeline(
            project=project,
            probe=startup_probe,
            plugin_connected=plugin_connected,
            stdio_format=args.emit_events,
            create_tickets=args.operator_tickets,
            ticket_queue=args.operator_ticket_queue,
            ticket_priority=args.operator_ticket_priority,
            mcp_already_bootstrapped=mcp_provision_ran,
            correlation_id=correlation_id,
        )


def unblock_queue_if_needed(
    project: Path,
    stdio_format: str,
    *,
    release_in_progress_tickets: Any,
    runner: Any,
    stdio_info: Any,
) -> None:
    """Release in-progress tickets if KORU_QUEUE_UNBLOCK is set."""
    if os.environ.get("KORU_QUEUE_UNBLOCK", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    released = release_in_progress_tickets(project, runner=runner)
    if released:
        stdio_info(
            f"koru autonomous: queue unblock - reopened {released} in_progress ticket(s)",
            fmt=stdio_format,
        )


__all__ = [
    "run_mcp_provision",
    "setup_autopilot_plugin",
    "run_operator_pipeline",
    "unblock_queue_if_needed",
]
