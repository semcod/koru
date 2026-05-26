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
import threading
import time
from collections.abc import Callable, Mapping
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from koru import autonomous_plugin
from koru.ide_client import IDEControlClient, build_ide_client
from koruide.daemon import AutopilotDaemon


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


def daemon_status_compatible(
    status: Mapping[str, Any] | None,
    *,
    current_version: Callable[[], str | None] = _current_koru_version,
) -> tuple[bool, str]:
    expected = current_version()
    actual = _daemon_status_version(status)
    if expected is None:
        return True, "current koru package version unknown"
    if actual is None:
        return False, f"daemon did not report version; expected {expected}"
    if actual != expected:
        return False, f"daemon version {actual} != current koru {expected}"
    return True, f"daemon version {actual}"


def daemon_status_log_summary(
    status: Mapping[str, Any] | None,
    *,
    plugin_rows_summary: Callable[[object], str] = autonomous_plugin.plugin_rows_log_summary,
) -> str:
    if not status:
        return "status=unavailable"
    version_label = _daemon_status_version(status) or "-"
    daemon = status.get("daemon") if isinstance(status, Mapping) else {}
    daemon = daemon if isinstance(daemon, Mapping) else {}
    pid = daemon.get("pid") or status.get("daemon_pid")
    sha = daemon.get("git_sha") or "-"
    py = daemon.get("python_executable") or "-"
    plugins = status.get("plugins")
    plugin_label = plugin_rows_summary(plugins if isinstance(plugins, list) else [])
    return f"pid={pid or '-'} version={version_label} sha={sha} python={py} plugins={plugin_label}"


def _stop_reused_daemon(
    client: IDEControlClient,
    socket_path: Path,
    *,
    stdio_format: str,
    stdio_info: Callable[..., Any] = _stdio_info,
    build_client: Callable[..., IDEControlClient] = build_ide_client,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    timeout_seconds: float = 2.0,
) -> bool:
    try:
        client.shutdown()
        stdio_info(
            f"koru autonomous: requested shutdown of stale autopilot daemon on {socket_path}",
            fmt=stdio_format,
        )
    except (OSError, RuntimeError, TimeoutError) as exc:
        stdio_info(
            f"koru autonomous: stale autopilot daemon shutdown failed ({exc})",
            fmt=stdio_format,
        )
    deadline = monotonic() + timeout_seconds
    probe = build_client(socket_path=socket_path, timeout=0.2)
    while monotonic() < deadline:
        if not probe.is_running():
            return True
        sleep(0.1)
    return not probe.is_running()


def start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
    stdio_format: str = "human",
    stdio_info: Callable[..., Any] = _stdio_info,
    build_client: Callable[..., IDEControlClient] = build_ide_client,
    daemon_factory: Callable[..., AutopilotDaemon] = AutopilotDaemon,
    thread_factory: Callable[..., threading.Thread] = threading.Thread,
    current_version: Callable[[], str | None] = _current_koru_version,
    plugin_rows_summary: Callable[[object], str] = autonomous_plugin.plugin_rows_log_summary,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[IDEControlClient, AutopilotDaemon | None, threading.Thread | None]:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    probe = build_client(socket_path=socket_path, timeout=0.5)
    stdio_info(f"koru autonomous: probing autopilot daemon on {socket_path}", fmt=stdio_format)
    if probe.is_running():
        stdio_info(
            f"koru autonomous: autopilot daemon ping ok on {socket_path}; requesting status",
            fmt=stdio_format,
        )
        status: Mapping[str, Any] | None = None
        try:
            status = probe.status()
            stdio_info(
                f"koru autonomous: autopilot daemon status \u2192 {daemon_status_log_summary(status, plugin_rows_summary=plugin_rows_summary)}",
                fmt=stdio_format,
            )
        except (OSError, RuntimeError, TimeoutError) as exc:
            stdio_info(
                f"koru autonomous: autopilot daemon status failed ({exc}); restarting",
                fmt=stdio_format,
            )
        compatible, reason = daemon_status_compatible(status, current_version=current_version)
        if compatible:
            stdio_info(
                f"koru autonomous: reusing autopilot daemon on {socket_path} ({reason})",
                fmt=stdio_format,
            )
            return build_client(socket_path=socket_path), None, None
        stdio_info(
            f"koru autonomous: restarting stale autopilot daemon on {socket_path} ({reason})",
            fmt=stdio_format,
        )
        if not _stop_reused_daemon(
            probe,
            socket_path,
            stdio_format=stdio_format,
            stdio_info=stdio_info,
            build_client=build_client,
            monotonic=monotonic,
            sleep=sleep,
        ):
            stdio_info(
                "koru autonomous: stale autopilot daemon did not stop; reusing existing socket",
                fmt=stdio_format,
            )
            return build_client(socket_path=socket_path), None, None
        stdio_info(
            f"koru autonomous: stale autopilot daemon stopped; starting replacement on {socket_path}",
            fmt=stdio_format,
        )
    else:
        stdio_info(
            f"koru autonomous: no autopilot daemon replied on {socket_path}; starting daemon",
            fmt=stdio_format,
        )

    daemon = daemon_factory(
        socket_path=socket_path,
        project=project,
        enable_project_handoff=False,
        log=lambda m: stdio_info(m, fmt=stdio_format),
    )
    daemon.start()
    thread = thread_factory(target=daemon.serve_forever, daemon=True)
    thread.start()
    sleep(0.05)
    stdio_info(f"koru autonomous: started autopilot daemon on {socket_path}", fmt=stdio_format)
    return build_client(socket_path=socket_path), daemon, thread


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
    *,
    stdio_info: Callable[..., Any] = _stdio_info,
    start_or_reuse_daemon_fn: Callable[
        ...,
        tuple[IDEControlClient, AutopilotDaemon | None, threading.Thread | None],
    ] = start_or_reuse_daemon,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None]:
    """Restart daemon if socket is missing."""
    if (
        args.enable_autopilot
        and client is not None
        and socket_path is not None
        and not socket_path.exists()
        and (autopilot_socket_observed_at_boot or daemon is not None or thread is not None)
    ):
        stdio_info(
            f"koru autonomous: autopilot socket missing at {socket_path}; "
            "restarting or taking over daemon…",
            fmt=args.emit_events,
        )
        if daemon is not None:
            with contextlib.suppress(OSError):
                daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        client, daemon, thread = start_or_reuse_daemon_fn(
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
    "restart_daemon_if_needed",
    "cleanup_autonomous_session",
    "daemon_status_compatible",
    "daemon_status_log_summary",
    "_current_koru_version",
    "_daemon_status_version",
    "_stop_reused_daemon",
]
