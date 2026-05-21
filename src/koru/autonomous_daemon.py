"""Daemon management utilities for autonomous mode.

Handles autopilot daemon lifecycle: starting, stopping, reusing,
and checking compatibility.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from koru.ide_client import IDEControlClient, build_ide_client
from koruide.daemon import AutopilotDaemon
from koruide.drive_orchestrator import DriveOrchestrator


def _stdio_info(msg: str, *, fmt: str) -> None:
    """Human-oriented status; jsonl mode routes to stderr so stdout stays NDJSON-only."""
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def _current_koru_version() -> str | None:
    try:
        return version("koru")
    except PackageNotFoundError:
        return None


def _daemon_status_version(status: Mapping[str, Any] | None) -> str | None:
    if not status:
        return None
    raw = status.get("daemon_version")
    if isinstance(raw, str) and raw:
        return raw
    daemon = status.get("daemon")
    if isinstance(daemon, Mapping):
        raw = daemon.get("version")
        if isinstance(raw, str) and raw:
            return raw
    return None


def _daemon_status_compatible(status: Mapping[str, Any] | None) -> tuple[bool, str]:
    expected = _current_koru_version()
    actual = _daemon_status_version(status)
    if expected is None:
        return True, "current koru package version unknown"
    if actual is None:
        return False, f"daemon did not report version; expected {expected}"
    if actual != expected:
        return False, f"daemon version {actual} != current koru {expected}"
    return True, f"daemon version {actual}"


def _stop_reused_daemon(
    client: IDEControlClient,
    socket_path: Path,
    *,
    stdio_format: str,
    timeout_seconds: float = 2.0,
) -> bool:
    try:
        client.shutdown()
    except (OSError, RuntimeError, TimeoutError) as exc:
        _stdio_info(
            f"koru autonomous: stale autopilot daemon shutdown failed ({exc})",
            fmt=stdio_format,
        )
    deadline = time.monotonic() + timeout_seconds
    probe = build_ide_client(socket_path=socket_path, timeout=0.2)
    while time.monotonic() < deadline:
        if not probe.is_running():
            return True
        time.sleep(0.1)
    return not probe.is_running()


def start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
    stdio_format: str = "human",
) -> tuple[IDEControlClient, AutopilotDaemon | None, threading.Thread | None]:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    probe = build_ide_client(socket_path=socket_path, timeout=0.5)
    if probe.is_running():
        status: Mapping[str, Any] | None = None
        try:
            status = probe.status()
        except (OSError, RuntimeError, TimeoutError) as exc:
            _stdio_info(
                f"koru autonomous: autopilot daemon status failed ({exc}); restarting",
                fmt=stdio_format,
            )
        compatible, reason = _daemon_status_compatible(status)
        if compatible:
            _stdio_info(
                f"koru autonomous: reusing autopilot daemon on {socket_path} ({reason})",
                fmt=stdio_format,
            )
            return build_ide_client(socket_path=socket_path), None, None
        _stdio_info(
            f"koru autonomous: restarting stale autopilot daemon on {socket_path} ({reason})",
            fmt=stdio_format,
        )
        if not _stop_reused_daemon(probe, socket_path, stdio_format=stdio_format):
            _stdio_info(
                "koru autonomous: stale autopilot daemon did not stop; reusing existing socket",
                fmt=stdio_format,
            )
            return build_ide_client(socket_path=socket_path), None, None

    daemon = AutopilotDaemon(
        socket_path=socket_path,
        project=project,
        log=lambda m: _stdio_info(m, fmt=stdio_format),
    )
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    _stdio_info(f"koru autonomous: started autopilot daemon on {socket_path}", fmt=stdio_format)
    return build_ide_client(socket_path=socket_path), daemon, thread


def _status_has_autopilot_plugin(status: Mapping[str, Any], ide: str) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    for plugin in plugins:
        if not isinstance(plugin, Mapping):
            continue
        plugin_ide = plugin.get("ide")
        if plugin_ide == ide or ide == "auto":
            version = plugin.get("version")
            version_info = DriveOrchestrator.plugin_version_info(
                plugin_ide=str(plugin_ide) if plugin_ide else None,
                connected_version=version if isinstance(version, str) else None,
            )
            if DriveOrchestrator.should_block_plugin_version(version_info):
                continue
            return True
    return False


def wait_for_autopilot_plugin(
    client: IDEControlClient,
    ide: str,
    *,
    timeout_seconds: float,
    interval_seconds: float = 0.25,
) -> bool:
    if timeout_seconds <= 0:
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if _status_has_autopilot_plugin(client.status(), ide):
                return True
        except OSError:
            pass
        time.sleep(interval_seconds)
    try:
        return _status_has_autopilot_plugin(client.status(), ide)
    except OSError:
        return False


def _stop_process(proc: subprocess.Popen | None, kind: str, *, stdio_format: str) -> None:
    if proc is None:
        return
    _stdio_info(f"koru autonomous: stopping {kind} (pid={proc.pid})", fmt=stdio_format)
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except (OSError, subprocess.TimeoutExpired):
            pass


def restart_daemon_if_needed(
    args: argparse.Namespace,
    client: IDEControlClient | None,
    socket_path: Path | None,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    autopilot_socket_observed_at_boot: bool,
    project: Path,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None]:
    """Restart daemon if socket is missing."""
    if (
        args.enable_autopilot
        and client is not None
        and socket_path is not None
        and not socket_path.exists()
        and (autopilot_socket_observed_at_boot or daemon is not None or thread is not None)
    ):
        _stdio_info(
            f"koru autonomous: autopilot socket missing at {socket_path}; "
            "restarting or taking over daemon…",
            fmt=args.emit_events,
        )
        if daemon is not None:
            with contextlib.suppress(OSError):
                daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        client, daemon, thread = start_or_reuse_daemon(
            project=project,
            socket_path=socket_path,
            stdio_format=args.emit_events,
        )
    return client, daemon, thread


def cleanup_autonomous_session(
    previous_stdio_format_env: str | None,
    previous_sigterm: Any,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    wup_process: Any,
    stdio_format: str,
) -> None:
    """Clean up autonomous session resources."""
    if previous_stdio_format_env is None:
        os.environ.pop("KORU_STDIO_FORMAT", None)
    else:
        os.environ["KORU_STDIO_FORMAT"] = previous_stdio_format_env
    signal.signal(signal.SIGTERM, previous_sigterm)
    if daemon is not None:
        daemon.stop()
    if thread is not None:
        thread.join(timeout=2.0)
    _stop_process(wup_process, "WUP watcher", stdio_format=stdio_format)


__all__ = [
    "start_or_reuse_daemon",
    "wait_for_autopilot_plugin",
    "restart_daemon_if_needed",
    "cleanup_autonomous_session",
    "_daemon_status_compatible",
    "_status_has_autopilot_plugin",
]
