"""Text DSL grammar → validated command dict."""

from __future__ import annotations

import shlex
from typing import Any


def _flag(rest: list[str], name: str) -> str | None:
    key = name.upper()
    if key in rest:
        idx = rest.index(key)
        if idx + 1 < len(rest):
            return rest[idx + 1]
    return None


def _parse_query_repair_history(rest: list[str], default_project: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload["project"] = _flag(rest, "PROJECT") or default_project or "."
    limit = _flag(rest, "LIMIT")
    payload["limit"] = int(limit) if limit else 20
    code = _flag(rest, "CODE")
    if code:
        payload["code"] = code
    return payload


def _parse_query_lane_status(rest: list[str], _default_project: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload["ide"] = (_flag(rest, "IDE") or rest[0]) if rest else "auto"
    payload["instance"] = _flag(rest, "INSTANCE") or "default"
    return payload


def _parse_validate_lane(rest: list[str], _default_project: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload["ide"] = (_flag(rest, "IDE") or rest[0]) if rest else "auto"
    payload["instance"] = _flag(rest, "INSTANCE") or "default"
    return payload


def _parse_resolve(rest: list[str], default_project: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if rest and rest[0].startswith('"'):
        payload["prompt"] = " ".join(rest).strip('"')
    else:
        payload["prompt"] = " ".join(rest)
    project = _flag(rest, "PROJECT") or default_project
    if project:
        payload["project"] = project
    return payload


def _parse_repair_run(rest: list[str], default_project: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    payload["ide"] = _flag(rest, "IDE") or (rest[0] if rest else "auto")
    payload["instance"] = _flag(rest, "INSTANCE") or "default"
    payload["project"] = _flag(rest, "PROJECT") or default_project or "."
    payload["trigger"] = _flag(rest, "TRIGGER") or "manual"
    return payload


_PARSERS: dict[str, Any] = {
    "QUERY_REPAIR_HISTORY": _parse_query_repair_history,
    "QUERY_LANE_STATUS": _parse_query_lane_status,
    "VALIDATE_LANE": _parse_validate_lane,
    "RESOLVE": _parse_resolve,
    "REPAIR_RUN": _parse_repair_run,
}


def parse_line(line: str, *, default_project: str | None = None) -> dict[str, Any]:
    line = line.strip()
    if not line or line.startswith("#"):
        return {}
    tokens = shlex.split(line, posix=True)
    if not tokens:
        return {}
    verb = tokens[0].upper()
    parser = _PARSERS.get(verb)
    if not parser:
        raise ValueError(f"unknown DSL verb: {verb}")
    payload = parser(tokens[1:], default_project)
    payload["verb"] = verb
    return payload


def _serialize_query_repair_history(payload: dict[str, Any]) -> str:
    parts = ["QUERY_REPAIR_HISTORY", f"PROJECT {payload.get('project', '.')}"]
    if payload.get("limit") not in (None, 20):
        parts.extend(["LIMIT", str(payload["limit"])])
    if payload.get("code"):
        parts.extend(["CODE", str(payload["code"])])
    return " ".join(parts)


def _serialize_query_lane_status(payload: dict[str, Any]) -> str:
    return f"QUERY_LANE_STATUS IDE {payload.get('ide', 'auto')} INSTANCE {payload.get('instance', 'default')}"


def _serialize_validate_lane(payload: dict[str, Any]) -> str:
    return f"VALIDATE_LANE IDE {payload.get('ide', 'auto')} INSTANCE {payload.get('instance', 'default')}"


def _serialize_resolve(payload: dict[str, Any]) -> str:
    return f'RESOLVE "{payload.get("prompt", "")}"'


def _serialize_repair_run(payload: dict[str, Any]) -> str:
    return (
        f"REPAIR_RUN IDE {payload.get('ide', 'auto')} "
        f"INSTANCE {payload.get('instance', 'default')} "
        f"PROJECT {payload.get('project', '.')}"
    )


_SERIALIZERS: dict[str, Any] = {
    "QUERY_REPAIR_HISTORY": _serialize_query_repair_history,
    "QUERY_LANE_STATUS": _serialize_query_lane_status,
    "VALIDATE_LANE": _serialize_validate_lane,
    "RESOLVE": _serialize_resolve,
    "REPAIR_RUN": _serialize_repair_run,
}


def to_text(payload: dict[str, Any]) -> str:
    verb = str(payload.get("verb", "")).upper()
    serializer = _SERIALIZERS.get(verb)
    if not serializer:
        raise ValueError(f"cannot serialize verb: {verb}")
    return serializer(payload)
