"""Local-manager integration for the autopilot daemon."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from koru.autopilot.daemon import AutopilotDaemon
from koru.local_manager_client import (
    LocalManagerClient,
    LocalManagerSession,
    lifecycle_decision_action,
)


def autopilot_local_manager_session(
    *,
    socket_path: Path,
) -> LocalManagerSession | None:
    client = LocalManagerClient.from_env()
    if not client.enabled:
        return None
    return LocalManagerSession(
        client=client,
        worker_id=f"koru.autopilot:{os.getpid()}:{socket_path}",
        worker_kind="koru.autopilot.daemon",
        capabilities=["koru.autopilot", "autopilot.daemon", "ide.rpc"],
        action_types=["koru.autopilot", "koru.autopilot.daemon"],
    )


def start_autopilot_manager_heartbeat(
    manager: LocalManagerSession | None,
    daemon: AutopilotDaemon,
    *,
    socket_path: Path,
    project: Path | None,
) -> tuple[threading.Event, threading.Thread] | None:
    if manager is None:
        return None
    stop = threading.Event()

    def _run() -> None:
        while not stop.wait(10.0):
            manager.heartbeat(
                metadata={
                    "socket": str(socket_path),
                    "project": str(project) if project is not None else None,
                },
            )
            if manager.should_stop():
                action = lifecycle_decision_action(manager.last_reply)
                print(f"koru autopilot daemon: local manager decision={action}; stopping")
                daemon.stop()
                return

    thread = threading.Thread(target=_run, name="koru-autopilot-local-manager", daemon=True)
    thread.start()
    return stop, thread


__all__ = [
    "autopilot_local_manager_session",
    "lifecycle_decision_action",
    "start_autopilot_manager_heartbeat",
]