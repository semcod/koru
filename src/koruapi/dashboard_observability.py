"""Observability trace payloads for the dashboard HTTP API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.cqrs.event_store import JsonlEventStore, StoredEvent
from koru.observability_dsl import (
    OBSERVABILITY_CONTEXT,
    render_observability_path,
    stored_event_to_compact_line,
    stored_event_to_dsl,
)
from koru.observability_writer import observability_event_store_path


def dashboard_observability_trace_payload(
    project: Path,
    *,
    corr: str | None = None,
    ticket: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return canonical JSON plus replayable DSL renderings for one trace."""
    store = JsonlEventStore(observability_event_store_path(project))
    events = [
        event
        for event in store.all_events(context=OBSERVABILITY_CONTEXT)
        if _trace_event_matches(event.payload, corr=corr, ticket=ticket)
    ]
    if limit > 0:
        events = events[-limit:]
    return {
        "project": str(project),
        "count": len(events),
        "filters": {
            "corr": corr,
            "ticket": ticket,
            "limit": limit,
        },
        "path": render_observability_path(events),
        "events": [_stored_event_payload(event) for event in events],
        "compact": [stored_event_to_compact_line(event) for event in events],
        "dsl": [stored_event_to_dsl(event) for event in events],
    }


def _trace_event_matches(
    payload: dict[str, object],
    *,
    corr: str | None,
    ticket: str | None,
) -> bool:
    if corr and str(payload.get("corr") or "") != corr:
        return False
    if ticket and str(payload.get("ticket") or "") != ticket:
        return False
    return True


def _stored_event_payload(event: StoredEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "event_id": event.event_id,
        "context": event.context,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "aggregate_id": event.aggregate_id,
        "payload": event.payload,
        "metadata": event.metadata,
    }


__all__ = ["dashboard_observability_trace_payload"]
