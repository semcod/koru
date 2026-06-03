"""Repair application service — CQRS command handler with event sourcing."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from coru.repair.commands import RecordDiagnosisCommand, RunRepairSessionCommand
from coru.repair.domain import RepairPlan, RepairProblem
from coru.repair.events import RepairEvent, aggregate_id_for
from coru.repair.pipeline import (
    IdeConnectFn,
    IdeReloadFn,
    ReplayFn,
    RunKoru,
    StatusPayloadFn,
    StrictHandshakeFn,
    run_repair_pipeline,
)
from coru.repair.store import RepairEventStore


class RepairService:
    """Write-side facade: dispatches repair commands and persists events."""

    def __init__(self, store: RepairEventStore) -> None:
        self._store = store

    @classmethod
    def for_project(cls, project_root: Path) -> RepairService:
        return cls(RepairEventStore.for_project(project_root))

    @property
    def store_path(self) -> Path:
        return self._store.path

    def record_diagnosis(self, command: RecordDiagnosisCommand) -> None:
        aggregate = aggregate_id_for(command.ide, command.instance)
        self._store.append(
            RepairEvent(
                event_type="repair.diagnosis.recorded",
                aggregate_id=aggregate,
                payload={
                    "session_id": uuid.uuid4().hex,
                    "ide": command.ide,
                    "instance": command.instance,
                    "trigger": command.trigger,
                    "problems": [
                        {
                            "code": p.code,
                            "severity": p.severity,
                            "message": p.message,
                            "fix_hint": p.fix_hint,
                            "context": dict(p.context),
                        }
                        for p in command.problems
                    ],
                    "snapshot": command.snapshot,
                },
            )
        )

    def run_session(
        self,
        command: RunRepairSessionCommand,
        *,
        repo_root: Path | None,
        run_koru: RunKoru,
        replay: ReplayFn,
        fetch_status: StatusPayloadFn,
        ensure_daemon: Callable[[], int] | None = None,
        ide_reload: IdeReloadFn | None = None,
        ide_connect: IdeConnectFn | None = None,
        strict_handshake: StrictHandshakeFn | None = None,
        max_rounds: int = 3,
    ) -> RepairPlan:
        aggregate = aggregate_id_for(command.ide, command.instance)
        pending: list[RepairEvent] = []

        def on_event(event_type: str, payload: Mapping[str, Any]) -> None:
            pending.append(
                RepairEvent(
                    event_type=event_type,  # type: ignore[arg-type]
                    aggregate_id=aggregate,
                    payload=dict(payload),
                )
            )

        plan = run_repair_pipeline(
            session_id=command.session_id,
            ide=command.ide,
            instance=command.instance,
            repo_root=repo_root,
            problems=command.problems,
            run_koru=run_koru,
            replay=replay,
            fetch_status=fetch_status,
            ensure_daemon=ensure_daemon,
            ide_reload=ide_reload,
            ide_connect=ide_connect,
            strict_handshake=strict_handshake,
            max_rounds=max_rounds,
            trigger=command.trigger,
            on_event=on_event,
        )
        self._store.append_many(pending)
        return plan


def run_repair_with_events(
    *,
    project_root: Path | None,
    ide: str,
    instance: str,
    problems: Sequence[RepairProblem],
    trigger: str,
    run_koru: RunKoru,
    replay: ReplayFn,
    fetch_status: StatusPayloadFn,
    ensure_daemon: Callable[[], int] | None = None,
    ide_reload: IdeReloadFn | None = None,
    ide_connect: IdeConnectFn | None = None,
    strict_handshake: StrictHandshakeFn | None = None,
    max_rounds: int = 3,
) -> RepairPlan:
    session_id = uuid.uuid4().hex
    if project_root is not None and project_root.is_dir():
        service = RepairService.for_project(project_root)
        return service.run_session(
            RunRepairSessionCommand(
                ide=ide,
                instance=instance,
                problems=tuple(problems),
                trigger=trigger,
                session_id=session_id,
            ),
            repo_root=project_root,
            run_koru=run_koru,
            replay=replay,
            fetch_status=fetch_status,
            ensure_daemon=ensure_daemon,
            ide_reload=ide_reload,
            ide_connect=ide_connect,
            strict_handshake=strict_handshake,
            max_rounds=max_rounds,
        )
    return run_repair_pipeline(
        session_id=session_id,
        ide=ide,
        instance=instance,
        repo_root=project_root,
        problems=problems,
        run_koru=run_koru,
        replay=replay,
        fetch_status=fetch_status,
        ensure_daemon=ensure_daemon,
        ide_reload=ide_reload,
        ide_connect=ide_connect,
        strict_handshake=strict_handshake,
        max_rounds=max_rounds,
        trigger=trigger,
    )
