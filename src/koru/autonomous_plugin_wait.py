"""Autonomous IDE plugin wait/reload orchestration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from koru import autonomous_plugin_runtime as plugin_runtime
from koru.control_commands import desktop_gui_command, shell_command
from koru.observability_events import (
    emit_blocker,
    emit_decision,
    emit_failure,
    emit_intent,
    emit_next,
)
from koru.observability_writer import emit_terminal_observability_path


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
    extension_is_active = extension_active(autopilot_ide)
    if extension_is_active is not False:
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
    reload_retry_wait: Any = plugin_runtime.reload_retry_wait_seconds,
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
    retry_wait = reload_retry_wait(wait_seconds)
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
    from koru.ide_adapters.ide_reload import (
        try_open_vscode_family_ide_new_window,
        try_reload_vscode_family_ide,
    )

    reload = try_reload_vscode_family_ide(autopilot_ide, project=project)
    if reload.attempted and reload.ok:
        return _wait_after_successful_reload(
            args,
            autopilot_ide,
            wait_seconds,
            reload=reload,
            client=client,
            project=project,
            wait_for_plugin=wait_for_plugin,
            stdio_info=stdio_info,
            reload_retry_wait=reload_retry_wait,
            open_fresh_window=try_open_vscode_family_ide_new_window,
        )
    if reload.attempted:
        _report_reload_failure(args, reload, stdio_info)
    return None


def _wait_after_successful_reload(
    args: Any,
    autopilot_ide: str,
    wait_seconds: float,
    *,
    reload: Any,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
    reload_retry_wait: Any,
    open_fresh_window: Any,
) -> bool:
    retry_wait = reload_retry_wait(wait_seconds)
    _report_reload_retry_wait(args, autopilot_ide, reload, retry_wait, stdio_info)
    if _plugin_reconnected_after_wait(args, autopilot_ide, retry_wait, client, wait_for_plugin, stdio_info):
        return True
    if reload.method != "reuse_window":
        return False
    return _try_fresh_window_after_reuse_reload(
        args,
        autopilot_ide,
        retry_wait,
        client=client,
        project=project,
        wait_for_plugin=wait_for_plugin,
        stdio_info=stdio_info,
        open_fresh_window=open_fresh_window,
    )


def _report_reload_retry_wait(
    args: Any,
    autopilot_ide: str,
    reload: Any,
    retry_wait: float,
    stdio_info: Any,
) -> None:
    reload_label = "reuse-window workspace reopen" if reload.method == "reuse_window" else f"Reload Window ({reload.method})"
    stdio_info(
        "koru autonomous: plugin wymaga przeładowania IDE; "
        f"automatyczny {reload_label} — "
        f"czekam ponownie {retry_wait:.1f}s…",
        fmt=args.emit_events,
    )


def _plugin_reconnected_after_wait(
    args: Any,
    autopilot_ide: str,
    retry_wait: float,
    client: Any,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool:
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
    return bool(plugin_ready)


def _try_fresh_window_after_reuse_reload(
    args: Any,
    autopilot_ide: str,
    retry_wait: float,
    *,
    client: Any,
    project: Path | None,
    wait_for_plugin: Any,
    stdio_info: Any,
    open_fresh_window: Any,
) -> bool:
    fresh_window = open_fresh_window(autopilot_ide, project=project)
    if not (fresh_window.attempted and fresh_window.ok):
        _report_fresh_window_failure(args, fresh_window, stdio_info)
        return False
    stdio_info(
        "koru autonomous: reuse-window nie uruchomił pluginu; "
        f"otwieram świeże okno IDE ({fresh_window.method}) — "
        f"czekam ponownie {retry_wait:.1f}s…",
        fmt=args.emit_events,
    )
    return _plugin_connected_after_fresh_window(
        args,
        autopilot_ide,
        retry_wait,
        client,
        wait_for_plugin,
        stdio_info,
    )


def _plugin_connected_after_fresh_window(
    args: Any,
    autopilot_ide: str,
    retry_wait: float,
    client: Any,
    wait_for_plugin: Any,
    stdio_info: Any,
) -> bool:
    plugin_ready = wait_for_plugin(
        client,
        autopilot_ide,
        timeout_seconds=retry_wait,
        stdio_format=args.emit_events,
    )
    if plugin_ready:
        stdio_info(
            "koru autonomous: autopilot plugin connected "
            f"after fresh IDE window ide={autopilot_ide}",
            fmt=args.emit_events,
        )
    return bool(plugin_ready)


def _report_fresh_window_failure(args: Any, fresh_window: Any, stdio_info: Any) -> None:
    if not fresh_window.attempted:
        return
    stdio_info(
        "koru autonomous: fresh IDE window fallback nie powiódł się "
        f"({fresh_window.method or '-'}: "
        f"{fresh_window.detail or 'unknown'})",
        fmt=args.emit_events,
    )


def _report_reload_failure(args: Any, reload: Any, stdio_info: Any) -> None:
    stdio_info(
        "koru autonomous: automatyczny Reload Window po mismatch "
        f"nie powiódł się ({reload.method or '-'}: "
        f"{reload.detail or 'unknown'})",
        fmt=args.emit_events,
    )


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
        reload_env = _temporary_reuse_window_reload_if_same_workspace(
            client,
            autopilot_ide,
            project,
            reason,
        )
        try:
            reloaded_ready = retry_after_reload(
                args,
                autopilot_ide,
                wait_seconds,
                client=client,
                project=project,
                wait_for_plugin=wait_for_plugin,
                stdio_info=stdio_info,
            )
        finally:
            _restore_reuse_window_reload(reload_env)
        if reloaded_ready is not None:
            return reloaded_ready

    stdio_info(
        "koru autonomous: no connected autopilot plugin "
        f"for ide={autopilot_ide} after {wait_seconds:.1f}s; "
        "autopilot drive will be skipped until it connects",
        fmt=args.emit_events,
    )
    emitted_trace = _emit_plugin_bootstrap_blocker_trace(
        project,
        autopilot_ide=autopilot_ide,
        reason=reason,
        wait_seconds=wait_seconds,
        plugin_install_status=plugin_install_status,
    )
    if plugin_install_status in {"installed", "already_installed"} and not emitted_trace:
        emit_reload_lines(
            autopilot_ide,
            emit_fmt=args.emit_events,
            stdio_info=stdio_info,
        )
    return False


def _temporary_reuse_window_reload_if_same_workspace(
    client: Any,
    autopilot_ide: str,
    project: Path | None,
    reason: str,
) -> tuple[bool, str | None] | None:
    if project is None or not _reason_is_connected_plugin_mismatch(reason):
        return None
    if os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"):
        return None
    try:
        status = client.status()
    except (OSError, RuntimeError, TimeoutError):
        return None
    if not _status_has_plugin_workspace(status, autopilot_ide, project):
        return None
    previous = os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD")
    os.environ["KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"] = "1"
    return True, previous


def _restore_reuse_window_reload(snapshot: tuple[bool, str | None] | None) -> None:
    if snapshot is None:
        return
    _changed, previous = snapshot
    if previous is None:
        os.environ.pop("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", None)
    else:
        os.environ["KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"] = previous


def _reason_is_connected_plugin_mismatch(reason: str) -> bool:
    text = reason.lower()
    return "connected autopilot plugin" in text and (
        "build mismatch" in text or "version mismatch" in text
    )


def _status_has_plugin_workspace(status: Any, autopilot_ide: str, project: Path) -> bool:
    if not isinstance(status, dict):
        return False
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    wanted = autopilot_ide.strip().lower()
    project_path = str(project.resolve())
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if wanted not in {"", "auto"} and plugin_ide != wanted:
            continue
        folders = plugin.get("workspaceFolders")
        if not isinstance(folders, list):
            continue
        for folder in folders:
            if not isinstance(folder, str):
                continue
            try:
                if str(Path(folder).resolve()) == project_path:
                    return True
            except OSError:
                continue
    return False


def _emit_plugin_bootstrap_blocker_trace(
    project: Path | None,
    *,
    autopilot_ide: str,
    reason: str,
    wait_seconds: float,
    plugin_install_status: str,
) -> bool:
    if project is None:
        return False
    corr = f"bootstrap-plugin-{autopilot_ide}"
    events = [
        emit_intent(
            project,
            corr=corr,
            goal="prepare_ide_autopilot_plugin",
            target=autopilot_ide,
            ide=autopilot_ide,
            require_plugin=True,
        ),
        emit_decision(
            project,
            corr=corr,
            name="plugin_bootstrap_gate",
            chosen="skip",
            because="plugin_not_connected",
            ide=autopilot_ide,
            wait_seconds=wait_seconds,
            install_status=plugin_install_status,
        ),
        emit_failure(
            project,
            corr=corr,
            code="plugin_not_connected",
            message=reason,
            verification="plugin_connected",
            ide=autopilot_ide,
        ),
        emit_blocker(
            project,
            corr=corr,
            name="plugin_not_connected",
            because=reason,
            ide=autopilot_ide,
            status="bootstrap_skipped",
        ),
        emit_next(
            project,
            corr=corr,
            action="reload_reconnect_plugin",
            ide=autopilot_ide,
            decision_kind="plugin_bootstrap_gate",
        ),
        desktop_gui_command(
            project,
            corr=corr,
            operation="command_palette_sequence",
            backend="command_palette",
            target=autopilot_ide,
            payload={
                "commands": [
                    "Developer: Reload Window",
                    "koru: Connect autopilot daemon",
                ],
                "reason": "plugin_not_connected",
            },
            actor="operator-guidance",
            replayable=False,
        ),
        shell_command(
            project,
            corr=corr,
            argv=["koru", "autopilot", "status", "--explain"],
            actor="operator-guidance",
            replayable=True,
        ),
    ]
    emit_terminal_observability_path(events)
    return True


__all__ = [
    "_emit_plugin_bootstrap_blocker_trace",
    "force_reload_if_extension_host_stale",
    "prepare_plugin_wait",
    "retry_plugin_wait_after_reload",
    "wait_for_plugin_connection",
]
