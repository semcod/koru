"""Autopilot plugin status helpers for ``koru autonomous``."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from koru.ide_client import IDEControlClient
from koruide.drive_orchestrator import DriveOrchestrator


def plugin_rows_log_summary(rows: object) -> str:
    if not isinstance(rows, list) or not rows:
        return "[]"
    parts: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            parts.append("<invalid>")
            continue
        ide = str(row.get("ide") or "-")
        version_label = str(row.get("version") or "-")
        fd = row.get("fd")
        fd_part = f" fd={fd}" if fd is not None else ""
        parts.append(f"{ide}@{version_label}{fd_part}")
    return "[" + ", ".join(parts) + "]"


def plugin_status_decision(status: Mapping[str, Any], ide: str) -> tuple[bool, str]:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False, "daemon status has no plugin list"
    if not plugins:
        return False, "daemon status plugin list is empty"
    wanted = (ide or "auto").strip().lower()
    ignored: list[str] = []
    for plugin in plugins:
        if not isinstance(plugin, Mapping):
            ignored.append("invalid plugin row")
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        version = plugin.get("version")
        version_label = version if isinstance(version, str) and version else "-"
        row_label = f"ide={plugin_ide or '-'} version={version_label}"
        if wanted not in {"", "auto"} and plugin_ide != wanted:
            ignored.append(f"{row_label} ignored: wanted ide={wanted}")
            continue
        version_info = DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin_ide or None,
            connected_version=version if isinstance(version, str) else None,
            protocol_version=(
                plugin.get("protocolVersion")
                if isinstance(plugin.get("protocolVersion"), int)
                else None
            ),
            capabilities=(
                plugin.get("capabilities")
                if isinstance(plugin.get("capabilities"), list)
                else None
            ),
        )
        if DriveOrchestrator.should_block_plugin_version(version_info):
            return False, (
                f"{row_label} blocked: "
                f"{DriveOrchestrator.plugin_version_block_message(version_info)}"
            )
        expected = version_info.get("expected_plugin_version") or "-"
        policy = version_info.get("plugin_version_policy") or "warn"
        return True, f"{row_label} accepted: expected={expected} policy={policy}"
    return False, "; ".join(ignored) if ignored else f"no plugin row matched ide={wanted}"


def status_has_autopilot_plugin(status: Mapping[str, Any], ide: str) -> bool:
    return plugin_status_decision(status, ide)[0]


def wait_for_autopilot_plugin(
    client: IDEControlClient,
    ide: str,
    *,
    timeout_seconds: float,
    interval_seconds: float = 0.25,
    stdio_info: Callable[..., Any] | None = None,
    stdio_format: str | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    def emit(message: str) -> None:
        if stdio_info is not None and stdio_format is not None:
            stdio_info(message, fmt=stdio_format)

    if timeout_seconds <= 0:
        emit(f"koru autonomous: plugin wait disabled for ide={ide} (timeout=0)")
        return False
    emit(
        f"koru autonomous: waiting for autopilot plugin ide={ide} "
        f"timeout={timeout_seconds:.1f}s interval={interval_seconds:.2f}s"
    )
    deadline = monotonic() + timeout_seconds
    last_reason: str | None = None
    while monotonic() < deadline:
        try:
            ready, reason = plugin_status_decision(client.status(), ide)
            if reason != last_reason:
                emit(f"koru autonomous: plugin decision ide={ide}: {reason}")
                last_reason = reason
            if ready:
                return True
        except (OSError, RuntimeError, TimeoutError) as exc:
            reason = f"daemon status unavailable: {exc}"
            if reason != last_reason:
                emit(f"koru autonomous: plugin decision ide={ide}: {reason}")
                last_reason = reason
        sleep(interval_seconds)
    try:
        ready, reason = plugin_status_decision(client.status(), ide)
        if reason != last_reason:
            emit(f"koru autonomous: plugin decision ide={ide}: {reason}")
        return ready
    except (OSError, RuntimeError, TimeoutError) as exc:
        emit(f"koru autonomous: plugin decision ide={ide}: daemon status unavailable: {exc}")
        return False


__all__ = [
    "plugin_rows_log_summary",
    "plugin_status_decision",
    "status_has_autopilot_plugin",
    "wait_for_autopilot_plugin",
]
