"""CLI actions for autopilot daemon management."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.autopilot.client import AutopilotClient
from koru.autopilot.daemon import AutopilotDaemon
from koru.autopilot.ide import detect_focused_ide_id, detect_running_ides
from koru.autopilot.local_manager import (
    autopilot_local_manager_session,
    lifecycle_decision_action,
    start_autopilot_manager_heartbeat,
)
from koru.autopilot.utils.client_helpers import call_daemon_method
from koruide.audit import AuditLog


def action_daemon(
    args: argparse.Namespace,
    *,
    default_socket_fn: Callable[[], Path] = default_socket_path,
) -> int:
    socket_path = args.socket or default_socket_fn()
    if args.idempotent:
        probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
        if probe.is_running():
            print(f"koru autopilot: daemon already running on {socket_path}")
            return 0
    project = args.project.resolve() if args.handoff else None
    manager = autopilot_local_manager_session(socket_path=socket_path)
    if manager is not None:
        manager.start(
            project=project,
            metadata={"socket": str(socket_path), "handoff": args.handoff},
        )
        if manager.should_stop():
            action = lifecycle_decision_action(manager.last_reply)
            print(f"koru autopilot daemon: local manager decision={action}; not starting")
            return 1 if action == "quarantine" else 0
    audit = AuditLog(enabled=True)
    daemon = AutopilotDaemon(
        socket_path=socket_path,
        log=print,
        project=project,
        handoff_cooldown=args.handoff_cooldown,
        audit=audit,
    )
    if audit.enabled:
        print(f"koru autopilot daemon: audit log at {audit.path}")
    try:
        daemon.start()
    except (OSError, RuntimeError) as exc:
        if manager is not None:
            manager.heartbeat(
                health="bad",
                metadata={"socket": str(socket_path), "error": str(exc)},
            )
        print(f"koru autopilot daemon: {exc}", file=sys.stderr)
        return 1
    heartbeat = start_autopilot_manager_heartbeat(
        manager,
        daemon,
        socket_path=socket_path,
        project=project,
    )
    if args.handoff:
        print(f"koru autopilot daemon: handoff enabled for project={project}")
    else:
        print("koru autopilot daemon: handoff disabled (--no-handoff)")
    try:
        daemon.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru autopilot daemon: interrupted")
    finally:
        if heartbeat is not None:
            stop, thread = heartbeat
            stop.set()
            thread.join(timeout=2.0)
        if manager is not None:
            manager.complete(status="completed", result={"socket": str(socket_path)})
    return 0


def action_shutdown(args: argparse.Namespace, *, client_fn: Callable) -> int:
    client = client_fn(args)
    return call_daemon_method(
        client,
        "shutdown",
        "koru autopilot shutdown",
        not_running_return_code=0,
    )


def action_ide_list(_args: argparse.Namespace) -> int:
    ides = detect_running_ides()
    if not ides:
        print("koru autopilot: no IDE processes detected")
        return 0
    focused = detect_focused_ide_id()
    for ide in ides:
        suffix = "  [focused]" if focused is not None and ide.id == focused else ""
        print(f"  {ide.id:<10} pid={ide.pid:<7} {ide.label}  ({ide.exe}){suffix}")
    return 0
