"""Local-manager integration for the planfile queue CLI."""

from __future__ import annotations

import os
from argparse import Namespace
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from koru.local_manager_client import (
    LocalManagerClient,
    LocalManagerSession,
    lifecycle_decision_action,
)
from koru.queue.types import QueueRunResult

QUEUE_LOCAL_MANAGER_ACTION_TYPES = ["koru.queue", "koru.queue.run", "planfile.queue.run"]
QUEUE_LOCAL_MANAGER_CAPABILITIES = [
    "koru.queue",
    "planfile.queue",
    "queue.runner",
    "shell.executor",
    "api.executor",
    "llm.executor",
]


@dataclass(frozen=True)
class QueueManagerEarlyExit:
    exit_code: int
    status: str
    message: str
    details: dict[str, Any]


def queue_local_manager_session(args: Namespace) -> LocalManagerSession | None:
    client = LocalManagerClient.from_env()
    if not client.enabled:
        return None
    capabilities = list(QUEUE_LOCAL_MANAGER_CAPABILITIES)
    if args.interactive:
        capabilities.append("human.input")
    return LocalManagerSession(
        client=client,
        worker_id=f"koru.queue:{os.getpid()}:{args.actor}",
        worker_kind="koru.queue",
        capabilities=capabilities,
        action_types=list(QUEUE_LOCAL_MANAGER_ACTION_TYPES),
    )


def queue_manager_start(
    args: Namespace,
    manager: LocalManagerSession | None,
) -> QueueManagerEarlyExit | None:
    if manager is None:
        return None
    manager.start(
        project=args.project,
        metadata={
            "mode": "loop" if args.loop else "single",
            "actor": args.actor,
            "queue_name": args.queue_name,
            "dry_run": args.dry_run,
            "interactive": args.interactive,
        },
    )
    if not manager.should_stop():
        return None
    action = lifecycle_decision_action(manager.last_reply)
    exit_code = 1 if action == "quarantine" else 0
    message = f"local manager decision={action}; exiting before queue work"
    return QueueManagerEarlyExit(
        exit_code=exit_code,
        status=action,
        message=message,
        details={"local_manager_decision": manager.last_reply},
    )


def queue_manager_health(result: QueueRunResult) -> str:
    return "bad" if result.status == "planfile_error" else "ok"


def queue_manager_decision_action(reply: dict[str, Any] | None) -> str:
    return lifecycle_decision_action(reply)


def queue_manager_stop_callback(
    manager: LocalManagerSession | None,
) -> Callable[[QueueRunResult, int], bool] | None:
    if manager is None:
        return None

    def _stop(result: QueueRunResult, iteration: int) -> bool:
        manager.heartbeat(
            health=queue_manager_health(result),
            metadata={
                "iteration": iteration,
                "status": result.status,
                "ticket_id": result.ticket_id,
                "executor_kind": result.executor_kind,
            },
        )
        if not manager.should_stop():
            return False
        action = lifecycle_decision_action(manager.last_reply)
        print(f"koru queue: local manager decision={action}; stopping after current iteration")
        return True

    return _stop


def queue_manager_complete(
    manager: LocalManagerSession | None,
    *,
    exit_code: int,
    result: dict[str, Any],
) -> None:
    if manager is None:
        return
    manager.complete(status="completed" if exit_code == 0 else "failed", result=result)


__all__ = [
    "QUEUE_LOCAL_MANAGER_ACTION_TYPES",
    "QUEUE_LOCAL_MANAGER_CAPABILITIES",
    "QueueManagerEarlyExit",
    "queue_local_manager_session",
    "queue_manager_complete",
    "queue_manager_decision_action",
    "queue_manager_health",
    "queue_manager_start",
    "queue_manager_stop_callback",
]