"""Autonomous IDE plugin wait/reload orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru import autonomous_plugin_runtime as plugin_runtime


def prepare_plugin_wait(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    *,
    project: Path | None,
    stdio_info: Any,
    ensure_trusted_publisher: Any = plugin_runtime.ensure_trusted_publisher_for_plugin,
    extension_active: Any = plugin_runtime.extension_active_in_latest_session,
    emit_reload_lines: Any = plugin_runtime.emit_reload_required_lines,
) -> tuple[bool, Any | None]:
    skip_plugin_wait = False
    reload_after_install = None
    if plugin_install_status not in {"installed", "already_installed"}:
        return skip_plugin_wait, reload_after_install

    ensure_trusted_publisher(
        autopilot_ide,
        stdio_info=stdio_info,
        emit_fmt=args.emit_events,
    )
    active = extension_active(autopilot_ide)
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
            emit_reload_lines(
                autopilot_ide,
                emit_fmt=args.emit_events,
                stdio_info=stdio_info,
            )
    else:
        emit_reload_lines(
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


def force_reload_if_extension_host_stale(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
    detect_stale_extension_host: Any = plugin_runtime.detect_stale_extension_host,
    live_plugin_version: Any = plugin_runtime.live_plugin_version,
) -> None:
    """Reload IDE window when on-disk VSIX is newer than the running plugin."""
    stale, installed, live = detect_stale_extension_host(autopilot_ide, client)
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
        new_live = live_plugin_version(client, autopilot_ide)
        stdio_info(
            "koru autonomous: autopilot plugin reconnected with fresh VSIX "
            f"ide={autopilot_ide} version={new_live or '?'}",
            fmt=args.emit_events,
        )


def retry_plugin_wait_after_reload(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
    reload_retry_wait: Any = plugin_runtime.reload_retry_wait_seconds,
) -> bool | None:
    from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

    reload = try_reload_vscode_family_ide(autopilot_ide, project=project)
    if reload.attempted and reload.ok:
        retry_wait = reload_retry_wait(wait_seconds)
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


def wait_for_plugin_connection(
    args: Any,
    autopilot_ide: str,
    plugin_install_status: str,
    reload_after_install: Any | None,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
    plugin_status_reason: Any = plugin_runtime.plugin_status_reason,
    plugin_blocker_line: Any = plugin_runtime.plugin_blocker_line,
    plugin_reason_requires_reload: Any = plugin_runtime.plugin_reason_requires_reload,
    force_reload_if_stale: Any = force_reload_if_extension_host_stale,
    retry_after_reload: Any = retry_plugin_wait_after_reload,
    emit_reload_lines: Any = plugin_runtime.emit_reload_required_lines,
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
            force_reload_if_stale(
                args,
                autopilot_ide,
                wait_seconds,
                client=client,
                project=project,
                wait_for_plugin=wait_for_plugin,
                stdio_info=stdio_info,
            )
        return True

    reason = plugin_status_reason(client, autopilot_ide)
    stdio_info(
        plugin_blocker_line(reason, autopilot_ide),
        fmt=args.emit_events,
    )
    if (
        plugin_install_status in {"installed", "already_installed"}
        and plugin_reason_requires_reload(reason)
    ):
        reloaded_ready = retry_after_reload(
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
        emit_reload_lines(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=stdio_info,
        )
    return False


__all__ = [
    "force_reload_if_extension_host_stale",
    "prepare_plugin_wait",
    "retry_plugin_wait_after_reload",
    "wait_for_plugin_connection",
]
