"""Runtime session setup helpers for ``koru autonomous``."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path
from typing import Any


def setup_autonomous_session(
    args: Any,
    *,
    apply_env_defaults: Any,
    uuid_factory: Any,
    guard_existing_processes: Any,
    ensure_init: Any,
    write_event: Any,
) -> tuple[str, Path, int]:
    apply_env_defaults(args)
    correlation_id = str(uuid_factory())
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    guard_rc = guard_existing_processes(args, project)
    os.environ["KORU_STDIO_FORMAT"] = args.emit_events
    if args.emit_events == "jsonl":
        write_event(
            sys.stdout,
            event_type="SessionStarted",
            correlation_id=correlation_id,
            payload={
                "project": str(project),
                "ticket_sources": args.ticket_sources,
                "max_cycles": args.max_cycles,
                "max_iterations": args.max_iterations,
                "sleep_seconds": args.sleep_seconds,
            },
        )
    ensure_init(project, force=args.force_init, stdio_format=args.emit_events)
    return correlation_id, project, guard_rc


def setup_autopilot_daemon(
    args: Any,
    project: Path,
    *,
    apply_agent_lane_environ: Any,
    resolve_autopilot_ide: Any,
    resolve_ide_route_fn: Any,
    default_socket_path: Any,
    start_or_reuse_daemon: Any,
    stdio_info: Any,
) -> tuple[Any | None, Any | None, Any | None, Path | None]:
    client = None
    daemon = None
    thread = None
    socket_path: Path | None = None
    if not args.enable_autopilot:
        return client, daemon, thread, socket_path

    lane = apply_agent_lane_environ(project, args.agent_lane)
    autopilot_ide, _ = resolve_autopilot_ide(
        args.autopilot_ide,
        lane,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    env_socket = (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    env_instance_before = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    socket_source = "cli --socket" if args.socket else "default socket"
    if env_socket and not args.socket:
        socket_source = "env:KORU_AUTOPILOT_SOCKET"
    elif env_instance_before and not args.socket:
        socket_source = f"env:KORU_AUTOPILOT_INSTANCE={env_instance_before}"
    if (
        autopilot_ide
        and "KORU_AUTOPILOT_INSTANCE" not in os.environ
        and "KORU_AUTOPILOT_SOCKET" not in os.environ
    ):
        os.environ["KORU_AUTOPILOT_INSTANCE"] = autopilot_ide
        socket_source = f"autopilot ide={autopilot_ide} -> KORU_AUTOPILOT_INSTANCE"
    socket_path = (args.socket or default_socket_path()).resolve()
    stdio_info(
        "koru autonomous: autopilot socket decision: "
        f"lane={lane} ide={autopilot_ide} source={socket_source} path={socket_path}",
        fmt=args.emit_events,
    )
    client, daemon, thread = start_or_reuse_daemon(
        project=project,
        socket_path=socket_path,
        stdio_format=args.emit_events,
    )
    return client, daemon, thread, socket_path


def cleanup_autonomous_session(
    previous_stdio_format_env: str | None,
    previous_sigterm: Any,
    daemon: Any | None,
    thread: Any | None,
    wup_process: Any,
    stdio_format: str,
    *,
    stop_process: Any,
) -> None:
    if previous_stdio_format_env is None:
        os.environ.pop("KORU_STDIO_FORMAT", None)
    else:
        os.environ["KORU_STDIO_FORMAT"] = previous_stdio_format_env
    signal.signal(signal.SIGTERM, previous_sigterm)
    if daemon is not None:
        daemon.stop()
    if thread is not None:
        thread.join(timeout=2.0)
    stop_process(wup_process, "WUP watcher", stdio_format=stdio_format)


__all__ = [
    "setup_autonomous_session",
    "setup_autopilot_daemon",
    "cleanup_autonomous_session",
]
