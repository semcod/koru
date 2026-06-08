"""Text DSL grammar → validated command dict."""

from __future__ import annotations

import shlex
from typing import Any


def parse_line(line: str, *, default_project: str | None = None) -> dict[str, Any]:
    line = line.strip()
    if not line or line.startswith("#"):
        return {}
    tokens = shlex.split(line, posix=True)
    if not tokens:
        return {}
    verb = tokens[0].upper()
    rest = tokens[1:]
    payload: dict[str, Any] = {"verb": verb}

    def _flag(name: str) -> str | None:
        key = name.upper()
        if key in rest:
            idx = rest.index(key)
            if idx + 1 < len(rest):
                return rest[idx + 1]
        return None

    if verb == "QUERY_REPAIR_HISTORY":
        payload["project"] = _flag("PROJECT") or default_project or "."
        limit = _flag("LIMIT")
        payload["limit"] = int(limit) if limit else 20
        code = _flag("CODE")
        if code:
            payload["code"] = code
        return payload

    if verb == "QUERY_LANE_STATUS":
        payload["ide"] = _flag("IDE") or rest[0] if rest else "auto"
        payload["instance"] = _flag("INSTANCE") or "default"
        return payload

    if verb == "VALIDATE_LANE":
        payload["ide"] = _flag("IDE") or rest[0] if rest else "auto"
        payload["instance"] = _flag("INSTANCE") or "default"
        return payload

    if verb == "RESOLVE":
        if rest and rest[0].startswith('"'):
            payload["prompt"] = " ".join(rest).strip('"')
        else:
            payload["prompt"] = " ".join(rest)
        project = _flag("PROJECT") or default_project
        if project:
            payload["project"] = project
        return payload

    if verb == "REPAIR_RUN":
        payload["ide"] = _flag("IDE") or (rest[0] if rest else "auto")
        payload["instance"] = _flag("INSTANCE") or "default"
        payload["project"] = _flag("PROJECT") or default_project or "."
        payload["trigger"] = _flag("TRIGGER") or "manual"
        return payload

    raise ValueError(f"unknown DSL verb: {verb}")


def to_text(payload: dict[str, Any]) -> str:
    verb = str(payload.get("verb", "")).upper()
    if verb == "QUERY_REPAIR_HISTORY":
        parts = ["QUERY_REPAIR_HISTORY", f"PROJECT {payload.get('project', '.')}"]
        if payload.get("limit") not in (None, 20):
            parts.extend(["LIMIT", str(payload["limit"])])
        if payload.get("code"):
            parts.extend(["CODE", str(payload["code"])])
        return " ".join(parts)
    if verb == "QUERY_LANE_STATUS":
        return f"QUERY_LANE_STATUS IDE {payload.get('ide', 'auto')} INSTANCE {payload.get('instance', 'default')}"
    if verb == "VALIDATE_LANE":
        return f"VALIDATE_LANE IDE {payload.get('ide', 'auto')} INSTANCE {payload.get('instance', 'default')}"
    if verb == "RESOLVE":
        return f'RESOLVE "{payload.get("prompt", "")}"'
    if verb == "REPAIR_RUN":
        return (
            f"REPAIR_RUN IDE {payload.get('ide', 'auto')} "
            f"INSTANCE {payload.get('instance', 'default')} "
            f"PROJECT {payload.get('project', '.')}"
        )
    raise ValueError(f"cannot serialize verb: {verb}")
