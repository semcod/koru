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


def _live_plugin_version(client: Any, autopilot_ide: str) -> str | None:
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


def _detect_stale_extension_host(
    autopilot_ide: str,
    client: Any,
) -> tuple[bool, str | None, str | None]:
    """Return ``(stale, installed_version, live_version)``.

    A stale extension host happens when a fresh VSIX is on disk (Koru just
    reasserted it) but the running IDE extension host is still serving the
    previous build. ``installed_extension_version_for_ide`` reads the IDE's
    ``--list-extensions --show-versions`` (i.e. what was installed by ``koru
    autopilot install-plugin`` or by the boot-time reassert). The daemon's
    plugin status reflects what the extension host is *actually running*. A
    mismatch means the user (or autonomous loop) needs ``Developer: Reload
    Window`` before the new code is exercised — exactly the friction
    captured in STARTER-242/STARTER-247 dev iterations.
    """
    if autopilot_ide not in _VSCODE_FAMILY_PLUGIN_IDES:
        return False, None, None
    try:
        from koruide.plugin_installer import installed_extension_version_for_ide
    except ImportError:
        return False, None, None
    installed = installed_extension_version_for_ide(autopilot_ide)
    live = _live_plugin_version(client, autopilot_ide)
    if not installed or not live:
        return False, installed, live
    if installed == live:
        return False, installed, live
    return True, installed, live


def _plugin_status_reason(client: Any, autopilot_ide: str) -> str:
    try:
        from koru.autonomous_plugin import plugin_status_decision

        _ready, reason = plugin_status_decision(client.status(), autopilot_ide)
        return reason
    except (OSError, RuntimeError, TimeoutError) as exc:
        return f"daemon status unavailable: {exc}"


def _plugin_reason_requires_reload(reason: str) -> bool:
    text = reason.lower()
    return (
        "plugin version mismatch" in text
        or "plugin protocol" in text
        or "plugin list is empty" in text
    )


def _plugin_blocker_line(reason: str, autopilot_ide: str) -> str:
    from koru.autonomous_plugin import plugin_skip_code

    blocker = plugin_skip_code(reason)
    if blocker == "plugin_version_mismatch":
        action = "reload IDE window after current VSIX install, then reconnect plugin"
    elif blocker == "plugin_status_unavailable":
        action = "check daemon socket and run `koru autopilot status --explain`"
    elif blocker == "plugin_not_connected":
        action = "run `koru: Connect autopilot daemon` in the IDE"
    else:
        action = "reload/reconnect the autopilot plugin"
    return (
        "koru autonomous: plugin blocker "
        f"blocked_by={blocker} ide={autopilot_ide} reason={reason or '-'}; "
        f"recovery={action}"
    )


def _report_unsupported_plugin_result(
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


def _emit_reload_required_lines(
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


def _prepare_plugin_wait(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    *,
    project: Path | None,
    stdio_info: Any,
) -> tuple[bool, Any | None]:
    skip_plugin_wait = False
    reload_after_install = None
    if plugin_install_status not in {"installed", "already_installed"}:
        return skip_plugin_wait, reload_after_install

    _ensure_trusted_publisher_for_plugin(
        autopilot_ide,
        stdio_info=stdio_info,
        emit_fmt=args.emit_events,
    )
    active = _extension_active_in_latest_session(autopilot_ide)
    if active is not False:
        return skip_plugin_wait, reload_after_install

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
            _emit_reload_required_lines(
                autopilot_ide,
                emit_fmt=args.emit_events,
                stdio_info=stdio_info,
            )
    else:
        _emit_reload_required_lines(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=stdio_info,
        )

    if reload.ok:
        return skip_plugin_wait, reload_after_install

    from koru.autonomy.env import keyboard_fallback_when_plugin_missing

    if keyboard_fallback_when_plugin_missing(autopilot_ide):
        stdio_info(
            "koru autonomous: plugin nieaktywny — włączam fallback "
            "klawiatury/OS-injectora (Wayland); ustaw profil: "
            "task koru:ide-os:calibrate IDE=cursor",
            fmt=args.emit_events,
        )
    else:
        stdio_info(
            "koru autonomous: pomijam oczekiwanie na plugin "
            "(wtyczka nie załadowana w extension host)",
            fmt=args.emit_events,
        )
    return True, reload_after_install


def _force_reload_if_extension_host_stale(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> None:
    """Reload IDE window when on-disk VSIX is newer than the running plugin.

    Common dev iteration: ``koru auto`` reasserts ``koru-autopilot-X.vsix``
    successfully, but the IDE still serves the previous extension host —
    so the freshly-fixed code never runs. Detect that by comparing the
    installed extension version (``cursor --list-extensions``) against the
    live plugin version reported by the daemon. When they diverge after a
    successful connection, trigger an automatic ``Developer: Reload Window``
    so the next drive picks up the new code.
    """
    stale, installed, live = _detect_stale_extension_host(autopilot_ide, client)
    if not stale:
        return
    from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

    stdio_info(
        "koru autonomous: stale extension host detected "
        f"(installed={installed}, live={live}); attempting Reload Window",
        fmt=args.emit_events,
    )
    reload = try_reload_vscode_family_ide(autopilot_ide, project=project)
    if not (reload.attempted and reload.ok):
        stdio_info(
            "koru autonomous: automatic Reload Window unavailable "
            f"({reload.method or '-'}: {reload.detail or 'manual reload needed'}); "
            f"installed={installed} live={live} — run "
            "`Developer: Reload Window` in the IDE",
            fmt=args.emit_events,
        )
        return
    retry_wait = max(wait_seconds, 30.0)
    stdio_info(
        "koru autonomous: reload after VSIX install "
        f"({reload.method}) — czekam ponownie {retry_wait:.1f}s na świeży plugin…",
        fmt=args.emit_events,
    )
    plugin_ready = wait_for_plugin(
        client,
        autopilot_ide,
        timeout_seconds=retry_wait,
        stdio_format=args.emit_events,
    )
    if plugin_ready:
        new_live = _live_plugin_version(client, autopilot_ide)
        stdio_info(
            "koru autonomous: autopilot plugin reconnected with fresh VSIX "
            f"ide={autopilot_ide} version={new_live or '?'}",
            fmt=args.emit_events,
        )


def _retry_plugin_wait_after_reload(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool | None:
    from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

    reload = try_reload_vscode_family_ide(autopilot_ide, project=project)
    if reload.attempted and reload.ok:
        retry_wait = max(wait_seconds, 30.0)
        stdio_info(
            "koru autonomous: plugin wymaga przeładowania IDE; "
            f"automatyczny Reload Window ({reload.method}) — "
            f"czekam ponownie {retry_wait:.1f}s…",
            fmt=args.emit_events,
        )
        plugin_ready = wait_for_plugin(
            client,
            autopilot_ide,
            timeout_seconds=retry_wait,
            stdio_format=args.emit_events,
        )
        if plugin_ready:
            stdio_info(
                "koru autonomous: autopilot plugin reconnected "
                f"after reload ide={autopilot_ide}",
                fmt=args.emit_events,
            )
        return plugin_ready
    if reload.attempted:
        stdio_info(
            "koru autonomous: automatyczny Reload Window po mismatch "
            f"nie powiódł się ({reload.method or '-'}: "
            f"{reload.detail or 'unknown'})",
            fmt=args.emit_events,
        )
    return None


def _wait_for_plugin_connection(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    reload_after_install: Any | None,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool:
    wait_seconds = max(0.0, args.autopilot_plugin_wait_seconds)
    if reload_after_install is not None and reload_after_install.ok:
        wait_seconds = max(wait_seconds, 30.0)

    plugin_ready = wait_for_plugin(
        client,
        autopilot_ide,
        timeout_seconds=wait_seconds,
        stdio_format=args.emit_events,
    )
    if plugin_ready:
        stdio_info(
            f"koru autonomous: autopilot plugin connected ide={autopilot_ide}",
            fmt=args.emit_events,
        )
        if plugin_install_status in {"installed", "already_installed"}:
            _force_reload_if_extension_host_stale(
                args,
                autopilot_ide,
                wait_seconds,
                client=client,
                project=project,
                wait_for_plugin=wait_for_plugin,
                stdio_info=stdio_info,
            )
        return True

    reason = _plugin_status_reason(client, autopilot_ide)
    stdio_info(
        _plugin_blocker_line(reason, autopilot_ide),
        fmt=args.emit_events,
    )
    if (
        plugin_install_status in {"installed", "already_installed"}
        and _plugin_reason_requires_reload(reason)
    ):
        reloaded_ready = _retry_plugin_wait_after_reload(
            args,
            autopilot_ide,
            wait_seconds,
            client=client,
            project=project,
            wait_for_plugin=wait_for_plugin,
            stdio_info=stdio_info,
        )
        if reloaded_ready is not None:
            return reloaded_ready

    stdio_info(
        "koru autonomous: no connected autopilot plugin "
        f"for ide={autopilot_ide} after {wait_seconds:.1f}s; "
        "autopilot drive will be skipped until it connects",
        fmt=args.emit_events,
    )
    if plugin_install_status in {"installed", "already_installed"}:
        _emit_reload_required_lines(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=stdio_info,
        )
    return False


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
    if not args.enable_autopilot or socket_path is None:
        return None

    plugin_result = install_plugin_for_ide(ide=autopilot_ide, socket_path=socket_path)
    stdio_info(format_plugin_install_result(plugin_result), fmt=args.emit_events)
    plugin_install_status = str(getattr(plugin_result, "status", "") or "")
    if plugin_result.status == "unsupported":
        return _report_unsupported_plugin_result(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=stdio_info,
        )
    if client is None or allow_keyboard_fallback():
        return None

    skip_plugin_wait, reload_after_install = _prepare_plugin_wait(
        args,
        autopilot_ide,
        plugin_install_status,
        project=project,
        stdio_info=stdio_info,
    )
    if skip_plugin_wait:
        return False
    return _wait_for_plugin_connection(
        args,
        autopilot_ide,
        plugin_install_status,
        reload_after_install,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=stdio_info,
    )


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
