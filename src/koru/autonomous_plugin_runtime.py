"""Runtime helpers for autonomous IDE plugin state."""

from __future__ import annotations

import os
from typing import Any

VSCODE_FAMILY_PLUGIN_IDES = frozenset(
    {"antigravity", "cursor", "vscode", "vscodium", "windsurf"},
)


def ensure_trusted_publisher_for_plugin(
    autopilot_ide: str,
    *,
    stdio_info: Any,
    emit_fmt: str,
) -> None:
    if autopilot_ide not in VSCODE_FAMILY_PLUGIN_IDES:
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


def extension_active_in_latest_session(autopilot_ide: str) -> bool | None:
    if autopilot_ide not in VSCODE_FAMILY_PLUGIN_IDES:
        return None
    from koru.ide_adapters import shared

    return shared.extension_activated_in_exthost(autopilot_ide)


def live_plugin_version(client: Any, autopilot_ide: str) -> str | None:
    """Best-effort lookup of the connected plugin's reported version."""
    status_fn = getattr(client, "status", None)
    if not callable(status_fn):
        return None
    try:
        status = status_fn()
    except (OSError, TimeoutError, RuntimeError):
        return None
    plugins = status.get("plugins") if isinstance(status, dict) else None
    if not isinstance(plugins, list):
        return None
    ide_lower = (autopilot_ide or "").lower()
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        if str(plugin.get("ide") or "").lower() == ide_lower:
            version = plugin.get("version")
            return str(version) if version else None
    return None


def detect_stale_extension_host(
    autopilot_ide: str,
    client: Any,
    *,
    live_version: Any = live_plugin_version,
) -> tuple[bool, str | None, str | None]:
    """Return ``(stale, installed_version, live_version)``."""
    if autopilot_ide not in VSCODE_FAMILY_PLUGIN_IDES:
        return False, None, None
    try:
        from koruide.plugin_installer import installed_extension_version_for_ide
    except ImportError:
        return False, None, None
    installed = installed_extension_version_for_ide(autopilot_ide)
    live = live_version(client, autopilot_ide)
    if not installed or not live:
        return False, installed, live
    if installed == live:
        return False, installed, live
    return True, installed, live


def plugin_status_reason(client: Any, autopilot_ide: str) -> str:
    try:
        from koru.autonomous_plugin import plugin_status_decision

        _ready, reason = plugin_status_decision(client.status(), autopilot_ide)
        return reason
    except (OSError, RuntimeError, TimeoutError) as exc:
        return f"daemon status unavailable: {exc}"


def plugin_reason_requires_reload(reason: str) -> bool:
    text = reason.lower()
    return (
        "plugin version mismatch" in text
        or "plugin build mismatch" in text
        or "plugin protocol" in text
        or "plugin list is empty" in text
    )


def plugin_blocker_line(reason: str, autopilot_ide: str) -> str:
    from koru.autonomous_plugin import plugin_skip_code

    blocker = plugin_skip_code(reason)
    recovery_actions = {
        "plugin_version_mismatch": "reload IDE window after current VSIX install, then reconnect plugin",
        "plugin_status_unavailable": "check daemon socket and run `koru autopilot status --explain`",
        "plugin_not_connected": "run `Developer: Reload Window`, then `koru: Connect autopilot daemon`",
    }
    action = recovery_actions.get(blocker, "reload/reconnect the autopilot plugin")
    return (
        "koru autonomous: plugin blocker "
        f"blocked_by={blocker} ide={autopilot_ide} reason={reason or '-'}; "
        f"recovery={action}"
    )


def reload_retry_wait_seconds(base_wait_seconds: float) -> float:
    raw = os.environ.get("KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS", "").strip()
    if raw:
        try:
            configured = float(raw)
        except ValueError:
            configured = 12.0
    else:
        configured = 12.0
    configured = min(max(configured, 3.0), 30.0)
    return max(base_wait_seconds, configured)


def report_unsupported_plugin_result(
    autopilot_ide: str,
    *,
    emit_fmt: str,
    stdio_info: Any,
) -> bool:
    stdio_info(
        "koru autonomous: autopilot plugin unsupported for "
        f"ide={autopilot_ide}; using keyboard/OS-injector path",
        fmt=emit_fmt,
    )

    env_lane = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
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
            fmt=emit_fmt,
        )
    return False


def emit_reload_required_lines(
    autopilot_ide: str,
    *,
    emit_fmt: str,
    stdio_info: Any,
) -> None:
    from koru.ide_adapters import shared

    for line in shared.extension_reload_required_lines(
        autopilot_ide,
        color=emit_fmt == "human",
    ):
        stdio_info(line, fmt=emit_fmt)


__all__ = [
    "VSCODE_FAMILY_PLUGIN_IDES",
    "detect_stale_extension_host",
    "emit_reload_required_lines",
    "ensure_trusted_publisher_for_plugin",
    "extension_active_in_latest_session",
    "live_plugin_version",
    "plugin_blocker_line",
    "plugin_reason_requires_reload",
    "plugin_status_reason",
    "reload_retry_wait_seconds",
    "report_unsupported_plugin_result",
]
