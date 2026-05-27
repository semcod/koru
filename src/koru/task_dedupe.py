"""Task dedupe helpers for scanner and plugin-created tickets."""

import re
from pathlib import Path
from typing import Any

from koru.task_models import CreatedTask


def _normalize_dedupe_part(value: object) -> str:
    return re.sub(r"[^a-z0-9._/-]+", "-", str(value).strip().lower()).strip("-")


def _source_context(scaffold: dict[str, Any]) -> dict[str, Any]:
    ctx = scaffold.get("source_context")
    return ctx if isinstance(ctx, dict) else {}


def _explicit_dedupe_key(scaffold: dict[str, Any]) -> str | None:
    explicit = _source_context(scaffold).get("dedupe_key")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return None


def _build_implicit_dedupe_key(scaffold: dict[str, Any], name: str) -> str | None:
    source_tool = str(scaffold.get("source_tool") or "koru-cli-nl")
    signal = _source_context(scaffold).get("signal")
    files = [str(v) for v in (scaffold.get("files") or []) if str(v).strip()]
    if source_tool == "koru-cli-nl" and not signal and not files:
        return None
    parts = [source_tool]
    if signal:
        parts.append(str(signal))
    parts.extend(files[:3])
    if not files:
        parts.append(name)
    return ":".join(_normalize_dedupe_part(part) for part in parts if str(part).strip())


def _dedupe_key_from_scaffold(scaffold: dict[str, Any], name: str) -> str | None:
    explicit = _explicit_dedupe_key(scaffold)
    if explicit is not None:
        return explicit
    return _build_implicit_dedupe_key(scaffold, name)


def _status_allows_dedupe_reuse(status: object) -> bool:
    return str(status or "").strip().lower() not in {"canceled", "cancelled", "closed"}


def _iter_ticket_entries(tickets: object) -> Any:
    if isinstance(tickets, dict):
        return tickets.items()
    if isinstance(tickets, list):
        return (
            (str(entry.get("id") or ""), entry)
            for entry in tickets
            if isinstance(entry, dict)
        )
    return iter([])


def _ticket_dedupe_key(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    context = source.get("context") if isinstance(source, dict) else None
    return context.get("dedupe_key") if isinstance(context, dict) else None


def _find_existing_task_by_dedupe_key(
    tickets: object,
    *,
    dedupe_key: str,
    sprint: str,
    path: Path,
) -> CreatedTask | None:
    for ticket_id, ticket in _iter_ticket_entries(tickets):
        if not isinstance(ticket, dict) or not _status_allows_dedupe_reuse(ticket.get("status")):
            continue
        if _ticket_dedupe_key(ticket) != dedupe_key:
            continue
        return CreatedTask(
            ticket_id=str(ticket.get("id") or ticket_id),
            sprint=sprint,
            path=path,
            name=str(ticket.get("name") or ticket.get("title") or ticket_id),
            reused=True,
        )
    return None


def _maybe_reuse_existing_task(
    tickets: object,
    scaffold: dict[str, Any],
    name: str,
    sprint: str,
    path: Path,
) -> tuple[CreatedTask | None, dict[str, Any]]:
    dedupe_key = _dedupe_key_from_scaffold(scaffold, name)
    if not dedupe_key:
        return None, scaffold
    existing = _find_existing_task_by_dedupe_key(
        tickets,
        dedupe_key=dedupe_key,
        sprint=sprint,
        path=path,
    )
    if existing is not None:
        return existing, scaffold
    source_context = (
        dict(scaffold.get("source_context"))
        if isinstance(scaffold.get("source_context"), dict)
        else {}
    )
    source_context["dedupe_key"] = dedupe_key
    return None, {**scaffold, "source_context": source_context}
