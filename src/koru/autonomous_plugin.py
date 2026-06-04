"""Autopilot plugin status helpers for ``koru autonomous``."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from typing import Any

from koru.ide_client import IDEControlClient
from koruide.drive_policy import DrivePolicy as DriveOrchestrator
from koruide.ide import canonical_autopilot_ide_id


def enable_autonomous_strict_plugin_policy(
    args: Any,
    *,
    environ: Mapping[str, str] | None = None,
    set_env: Callable[[str, str], None] | None = None,
    stdio_info: Callable[..., Any] | None = None,
) -> None:
    """Default autonomous runs to fail-closed on plugin drift and weak ACKs."""
    if not args.enable_autopilot:
        return
    env = environ or os.environ
    setter = set_env or os.environ.__setitem__
    version_set = False
    if (
        env.get("KORU_STRICT_PLUGIN_VERSION") is None
        and env.get("KORU_PLUGIN_VERSION_POLICY") is None
    ):
        setter("KORU_STRICT_PLUGIN_VERSION", "1")
        version_set = True

    ack_set = False
    if env.get("KORU_STRICT_PLUGIN_ACK") is None:
        setter("KORU_STRICT_PLUGIN_ACK", "1")
        ack_set = True

    if version_set or ack_set:
        details = []
        if version_set:
            details.append("version")
        if ack_set:
            details.append("ack")
        if stdio_info is not None:
            stdio_info(
                f"koru autonomous: strict plugin {'/'.join(details)} policy enabled by default",
                fmt=args.emit_events,
            )


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
    return f"[{', '.join(parts)}]"


def plugin_skip_code(reason: str) -> str:
    """Classify plugin-gate failures into actionable blocker codes."""
    text = (reason or "").strip().lower()
    if not text:
        return "plugin_missing"
    if (
        "version mismatch" in text
        or "build mismatch" in text
        or "protocol mismatch" in text
        or "protocol missing" in text
    ):
        return "plugin_version_mismatch"
    if "daemon status unavailable" in text:
        return "plugin_status_unavailable"
    if (
        "plugin list is empty" in text
        or "no plugin row matched" in text
        or "has no plugin list" in text
    ):
        return "plugin_not_connected"
    return "plugin_missing"


def _plugin_rows(status: Mapping[str, Any]) -> tuple[list[Any] | None, str | None]:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return None, "daemon status has no plugin list"
    if not plugins:
        return plugins, "daemon status plugin list is empty"
    return plugins, None


def _latest_rejected_plugin(status: Mapping[str, Any], wanted: str) -> Mapping[str, Any] | None:
    rejected = status.get("rejected_plugins")
    if not isinstance(rejected, list):
        return None
    for row in reversed(rejected):
        if not isinstance(row, Mapping):
            continue
        plugin_ide = str(row.get("ide") or "").strip().lower()
        if wanted not in {"", "auto"} and plugin_ide != wanted:
            continue
        return row
    return None


def _rejected_plugin_reason(row: Mapping[str, Any]) -> str:
    plugin_ide = str(row.get("ide") or "").strip().lower()
    version = row.get("version")
    expected = row.get("expected_version")
    message = str(row.get("message") or "").strip()
    if "version mismatch" in message.lower():
        return f"{_plugin_row_label(plugin_ide, version)} blocked: {message}"
    if version and expected and version != expected:
        return (
            f"{_plugin_row_label(plugin_ide, version)} blocked: connected autopilot "
            f"plugin version mismatch: connected={version} expected={expected}; "
            "reload the IDE window after installing the current VSIX, then run "
            "`koru: Connect autopilot daemon`."
        )
    if message:
        return f"{_plugin_row_label(plugin_ide, version)} rejected: {message}"
    return f"{_plugin_row_label(plugin_ide, version)} rejected"


def _wanted_plugin_ide(ide: str) -> str:
    return canonical_autopilot_ide_id((ide or "auto").strip().lower())


def _plugin_row_label(plugin_ide: str, version: object) -> str:
    version_label = version if isinstance(version, str) and version else "-"
    return f"ide={plugin_ide or '-'} version={version_label}"


def _plugin_row_ignored_reason(plugin: object, wanted: str) -> str | None:
    if not isinstance(plugin, Mapping):
        return "invalid plugin row"
    plugin_ide = str(plugin.get("ide") or "").strip().lower()
    if wanted in {"", "auto"} or plugin_ide == wanted:
        return None
    return f"{_plugin_row_label(plugin_ide, plugin.get('version'))} ignored: wanted ide={wanted}"


def _plugin_protocol_version(plugin: Mapping[str, Any]) -> int | None:
    value = plugin.get("protocolVersion")
    return value if isinstance(value, int) else None


def _plugin_capabilities(plugin: Mapping[str, Any]) -> list[Any] | None:
    value = plugin.get("capabilities")
    return value if isinstance(value, list) else None


def _plugin_version_info(plugin: Mapping[str, Any], plugin_ide: str) -> Mapping[str, Any]:
    version = plugin.get("version")
    build_sha = plugin.get("buildSha")
    return DriveOrchestrator.plugin_version_info(
        plugin_ide=plugin_ide or None,
        connected_version=version if isinstance(version, str) else None,
        connected_build_sha=build_sha if isinstance(build_sha, str) else None,
        protocol_version=_plugin_protocol_version(plugin),
        capabilities=_plugin_capabilities(plugin),
    )


def _accepted_plugin_reason(row_label: str, version_info: Mapping[str, Any]) -> str:
    expected = version_info.get("expected_plugin_version") or "-"
    expected_build = version_info.get("expected_plugin_build_sha") or "-"
    policy = version_info.get("plugin_version_policy") or "warn"
    return f"{row_label} accepted: expected={expected} expected_build={expected_build} policy={policy}"


def _matching_plugin_decision(plugin: Mapping[str, Any]) -> tuple[bool, str]:
    plugin_ide = str(plugin.get("ide") or "").strip().lower()
    row_label = _plugin_row_label(plugin_ide, plugin.get("version"))
    version_info = _plugin_version_info(plugin, plugin_ide)
    if DriveOrchestrator.should_block_plugin_version(version_info):
        reason = DriveOrchestrator.plugin_version_block_message(version_info)
        return False, f"{row_label} blocked: {reason}"
    return True, _accepted_plugin_reason(row_label, version_info)


def plugin_status_decision(status: Mapping[str, Any], ide: str) -> tuple[bool, str]:
    wanted = _wanted_plugin_ide(ide)
    plugins, invalid_reason = _plugin_rows(status)
    if invalid_reason is not None:
        if plugins == []:
            rejected = _latest_rejected_plugin(status, wanted)
            if rejected is not None:
                return False, _rejected_plugin_reason(rejected)
        return False, invalid_reason
    if plugins is None:
        return False, "daemon status has no plugin list"
    ignored: list[str] = []
    for plugin in plugins:
        ignored_reason = _plugin_row_ignored_reason(plugin, wanted)
        if ignored_reason is not None:
            ignored.append(ignored_reason)
            continue
        return _matching_plugin_decision(plugin)
    return False, "; ".join(ignored) if ignored else f"no plugin row matched ide={wanted}"


def status_has_autopilot_plugin(status: Mapping[str, Any], ide: str) -> bool:
    return plugin_status_decision(status, ide)[0]


def _probe_plugin_status(client: IDEControlClient, ide: str) -> tuple[bool, str]:
    try:
        return plugin_status_decision(client.status(), ide)
    except (OSError, RuntimeError, TimeoutError) as exc:
        return False, f"daemon status unavailable: {exc}"


def _emit_plugin_wait_decision(
    *,
    emit: Callable[[str], None],
    ide: str,
    reason: str,
    last_reason: str | None,
) -> str:
    if reason != last_reason:
        emit(f"koru autonomous: plugin decision ide={ide}: {reason}")
    return reason


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
        ready, reason = _probe_plugin_status(client, ide)
        last_reason = _emit_plugin_wait_decision(
            emit=emit,
            ide=ide,
            reason=reason,
            last_reason=last_reason,
        )
        if ready:
            return True
        sleep(interval_seconds)
    ready, reason = _probe_plugin_status(client, ide)
    _emit_plugin_wait_decision(
        emit=emit,
        ide=ide,
        reason=reason,
        last_reason=last_reason,
    )
    return ready


__all__ = [
    "enable_autonomous_strict_plugin_policy",
    "plugin_skip_code",
    "plugin_rows_log_summary",
    "plugin_status_decision",
    "status_has_autopilot_plugin",
    "wait_for_autopilot_plugin",
]
