"""Thin shim — route dsl2koru verbs through control bus."""

from __future__ import annotations

_DSL2KORU_VERBS = frozenset({"QUERY_REPAIR_HISTORY", "QUERY_LANE_STATUS", "VALIDATE_LANE", "RESOLVE", "REPAIR_RUN"})


def is_dsl2koru_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return stripped.split()[0].upper() in _DSL2KORU_VERBS


def dispatch_line(line: str, *, default_project: str | None = None) -> dict:
    from dsl2koru.bus import dispatch

    return dispatch(line, default_project=default_project).to_dict()
