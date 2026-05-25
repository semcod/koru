"""Persistence helpers for Koru observability events."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from koru.cqrs.event_store import JsonlEventStore, StoredEvent, project_event_store_path
from koru.observability_dsl import (
    OBSERVABILITY_CONTEXT,
    KoruObsEvent,
    render_compact_observability_line,
    render_observability_path,
    stored_event_to_compact_line,
    stored_event_to_dsl,
)

DEFAULT_OBSERVABILITY_EVENT_FILE = "events/observability.jsonl"
DEFAULT_OBSERVABILITY_DSL_FILE = "events/observability.dsl.log"


def observability_event_store_path(project: Path) -> Path:
    return project_event_store_path(project, file_name=DEFAULT_OBSERVABILITY_EVENT_FILE)


def observability_dsl_log_path(project: Path) -> Path:
    return project.resolve() / ".koru" / DEFAULT_OBSERVABILITY_DSL_FILE


def observability_terminal_enabled() -> bool:
    raw = os.environ.get("KORU_OBSERVABILITY_TERMINAL", "").strip().lower()
    if raw:
        return raw not in {"0", "false", "no", "off"}
    from koru.activity_log import activity_enabled

    return activity_enabled()


def _emit_terminal_observability_line(stored: StoredEvent) -> None:
    print(stored_event_to_compact_line(stored), file=sys.stderr, flush=True)


def _compact_utc_time() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def emit_terminal_observability_path(events: list[KoruObsEvent]) -> None:
    """Emit a one-line terminal summary for an already-persisted trace slice."""
    if not observability_terminal_enabled():
        return
    path = render_observability_path(events)
    if path.startswith("OBS "):
        path = path[len("OBS "):]
    print(f"[{_compact_utc_time()}] koru ▸ OBS-PATH: {path}", file=sys.stderr)


def write_observability_event(
    event: KoruObsEvent,
    *,
    project: Path | None = None,
    store: JsonlEventStore | None = None,
    write_dsl_log: bool | None = None,
    emit_terminal: bool | None = None,
) -> StoredEvent:
    """Append an observability event and optionally mirror it as DSL text."""
    terminal_event = event if event.ts else replace(event, ts=_utc_now())
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
            handle.write(stored_event_to_dsl(stored) + "\n\n")
    should_emit_terminal = (
        observability_terminal_enabled() if emit_terminal is None else emit_terminal
    )
    if should_emit_terminal:
        print(render_compact_observability_line(terminal_event), file=sys.stderr, flush=True)
    return stored


def try_write_observability_event(
    event: KoruObsEvent,
    *,
    project: Path | None = None,
    write_dsl_log: bool | None = None,
    emit_terminal: bool | None = None,
) -> StoredEvent | None:
    """Best-effort variant for daemon paths where observability must not break delivery."""
    try:
        return write_observability_event(
            event,
            project=project,
            write_dsl_log=write_dsl_log,
            emit_terminal=emit_terminal,
        )
    except OSError:
        return None


__all__ = [
    "DEFAULT_OBSERVABILITY_DSL_FILE",
    "DEFAULT_OBSERVABILITY_EVENT_FILE",
    "_compact_utc_time",
    "emit_terminal_observability_path",
    "observability_dsl_log_path",
    "observability_event_store_path",
    "observability_terminal_enabled",
    "try_write_observability_event",
    "write_observability_event",
]
