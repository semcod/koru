"""CLI actions for autopilot daemon management."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.dotenv_loader import load_dotenv

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


def _daemon_already_running(args: argparse.Namespace, socket_path: Path) -> bool:
    if not args.idempotent:
        return False
    probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
    if not probe.is_running():
        return False
    print(f"koru autopilot: daemon already running on {socket_path}")
    return True


def _start_local_manager(
    *,
    socket_path: Path,
    project: Path | None,
    handoff: bool,
) -> tuple[Any | None, int | None]:
    manager = autopilot_local_manager_session(socket_path=socket_path)
    if manager is None:
        return None, None
    manager.start(project=project, metadata={"socket": str(socket_path), "handoff": handoff})
    if not manager.should_stop():
        return manager, None
    decision = lifecycle_decision_action(manager.last_reply)
    print(f"koru autopilot daemon: local manager decision={decision}; not starting")
    return manager, 1 if decision == "quarantine" else 0


def _record_daemon_start_failure(
    manager: Any | None,
    *,
    socket_path: Path,
    error: Exception,
) -> None:
    if manager is not None:
        manager.heartbeat(health="bad", metadata={"socket": str(socket_path), "error": str(error)})


def _stop_heartbeat(heartbeat: Any | None) -> None:
    if heartbeat is None:
        return
    stop, thread = heartbeat
    stop.set()
    thread.join(timeout=2.0)


def run_daemon_command(
    args: argparse.Namespace,
    *,
    default_socket_fn: Callable[[], Path] = default_socket_path,
) -> int:
    socket_path = args.socket or default_socket_fn()
    from koru.ide_adapters.bridge import gc_stale_sockets_for_lane

    for path in gc_stale_sockets_for_lane(socket_path):
        print(f"koru autopilot daemon: removed stale socket {path}")
    if _daemon_already_running(args, socket_path):
        return 0
    from koru.autonomous_runtime import normalize_project_root

    raw_project = args.project.resolve() if args.handoff else None
    project = normalize_project_root(raw_project) if raw_project is not None else None
    load_dotenv(Path.cwd())
    if project is not None:
        load_dotenv(project)
        os.environ.setdefault("VDISPLAY_METADATA_DIR", str(project.resolve() / ".vdisplay"))
        os.environ.setdefault("KORU_PROJECT_ROOT", str(project.resolve()))
    instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip().lower()
    if instance:
        from koru.autonomous_vdisplay_defaults import apply_vdisplay_drive_defaults

        applied = apply_vdisplay_drive_defaults(ide=instance)
        if applied:
            print(
                "koru autopilot daemon: vdisplay defaults applied "
                f"({len(applied)} unset keys for {instance})"
            )
    manager, stop_rc = _start_local_manager(
        socket_path=socket_path,
        project=project,
        handoff=args.handoff,
    )
    if stop_rc is not None:
        return stop_rc
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
        _record_daemon_start_failure(manager, socket_path=socket_path, error=exc)
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
        _stop_heartbeat(heartbeat)
        if manager is not None:
            manager.complete(status="completed", result={"socket": str(socket_path)})
    return 0


def shutdown_daemon_command(args: argparse.Namespace, *, client_fn: Callable) -> int:
    client = client_fn(args)
    return call_daemon_method(
        client,
        "shutdown",
        "koru autopilot shutdown",
        not_running_return_code=0,
    )


def list_detected_ides_command(_args: argparse.Namespace) -> int:
    ides = detect_running_ides()
    if not ides:
        print("koru autopilot: no IDE processes detected")
        return 0
    focused = detect_focused_ide_id()
    for ide in ides:
        suffix = "  [focused]" if focused is not None and ide.id == focused else ""
        print(f"  {ide.id:<10} pid={ide.pid:<7} {ide.label}  ({ide.exe}){suffix}")
    return 0


action_daemon = run_daemon_command
action_shutdown = shutdown_daemon_command
action_ide_list = list_detected_ides_command
