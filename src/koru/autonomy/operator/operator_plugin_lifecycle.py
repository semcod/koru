"""Autonomous autopilot-plugin lifecycle orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PluginLifecycleHooks:
    install_plugin_for_ide: Callable[..., Any]
    format_plugin_install_result: Callable[[Any], str]
    allow_keyboard_fallback: Callable[[], bool]
    report_unsupported: Callable[..., bool]
    prepare_plugin_wait: Callable[..., tuple[bool, Any | None]]
    wait_for_plugin_connection: Callable[..., bool]
    stdio_info: Callable[..., None]


def setup_autopilot_plugin_lifecycle(
    args: Any,
    autopilot_ide: str,
    socket_path: Path | None,
    client: Any | None,
    *,
    project: Path | None = None,
    wait_for_plugin: Any,
    hooks: PluginLifecycleHooks,
) -> bool | None:
    """Install/reassert the IDE plugin and wait for a usable connection."""
    if not args.enable_autopilot or socket_path is None:
        return None

    plugin_result = hooks.install_plugin_for_ide(
        ide=autopilot_ide,
        socket_path=socket_path,
    )
    hooks.stdio_info(hooks.format_plugin_install_result(plugin_result), fmt=args.emit_events)
    plugin_install_status = str(getattr(plugin_result, "status", "") or "")

    if plugin_install_status == "unsupported":
        return hooks.report_unsupported(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=hooks.stdio_info,
        )
    if plugin_install_status == "skipped":
        return None
    if client is None or hooks.allow_keyboard_fallback():
        return None

    skip_plugin_wait, reload_after_install = hooks.prepare_plugin_wait(
        args,
        autopilot_ide,
        plugin_install_status,
        project=project,
        stdio_info=hooks.stdio_info,
    )
    if skip_plugin_wait:
        return False

    return hooks.wait_for_plugin_connection(
        args,
        autopilot_ide,
        plugin_install_status,
        reload_after_install,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=hooks.stdio_info,
    )


__all__ = ["PluginLifecycleHooks", "setup_autopilot_plugin_lifecycle"]
