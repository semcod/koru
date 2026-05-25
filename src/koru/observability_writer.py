"""Persistence helpers for Koru observability events."""

from __future__ import annotations

import os
from pathlib import Path

from koru.cqrs.event_store import JsonlEventStore, StoredEvent, project_event_store_path
from koru.observability_dsl import OBSERVABILITY_CONTEXT, KoruObsEvent

DEFAULT_OBSERVABILITY_EVENT_FILE = "events/observability.jsonl"
DEFAULT_OBSERVABILITY_DSL_FILE = "events/observability.dsl.log"


def observability_event_store_path(project: Path) -> Path:
    return project_event_store_path(project, file_name=DEFAULT_OBSERVABILITY_EVENT_FILE)


def observability_dsl_log_path(project: Path) -> Path:
    return project.resolve() / ".koru" / DEFAULT_OBSERVABILITY_DSL_FILE


def write_observability_event(
    event: KoruObsEvent,
    *,
    project: Path | None = None,
    store: JsonlEventStore | None = None,
    write_dsl_log: bool | None = None,
) -> StoredEvent:
    """Append an observability event and optionally mirror it as DSL text."""
    active_project = (project or Path.cwd()).resolve()
    active_store = store or JsonlEventStore(observability_event_store_path(active_project))
    stored = active_store.append(
        context=OBSERVABILITY_CONTEXT,
        event_type=event.kind,
        payload=event.payload(),
        metadata={"dsl_version": "koru.obs.v1"},
        aggregate_id=event.corr,
    )
    should_write_dsl = (
        os.environ.get("KORU_OBSERVABILITY_DSL_LOG", "").strip().lower()
        not in {"0", "false", "no", "off"}
        if write_dsl_log is None
        else write_dsl_log
    )
    if should_write_dsl:
        path = observability_dsl_log_path(active_project)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.to_dsl() + "\n\n")
    return stored


def try_write_observability_event(
    event: KoruObsEvent,
    *,
    project: Path | None = None,
    write_dsl_log: bool | None = None,
) -> StoredEvent | None:
    """Best-effort variant for daemon paths where observability must not break delivery."""
    try:
        return write_observability_event(
            event,
            project=project,
            write_dsl_log=write_dsl_log,
        )
    except OSError:
        return None


__all__ = [
    "DEFAULT_OBSERVABILITY_DSL_FILE",
    "DEFAULT_OBSERVABILITY_EVENT_FILE",
    "observability_dsl_log_path",
    "observability_event_store_path",
    "try_write_observability_event",
    "write_observability_event",
]
