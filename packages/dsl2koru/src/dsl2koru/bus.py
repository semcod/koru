"""CQRS dispatch bus for dsl2koru."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dsl2koru.codec import envelope_from_bytes, parse_text, validate_payload
from dsl2koru.events import EventStore
from dsl2koru.result import DslResult
from dsl2koru.schema_registry import COMMAND_VERBS, QUERY_VERBS


def dispatch(
    command: str | dict[str, Any] | bytes,
    *,
    default_project: str | None = None,
    project_root: Path | None = None,
) -> DslResult:
    raw_line = ""
    try:
        if isinstance(command, bytes):
            payload = envelope_from_bytes(command)
            raw_line = json.dumps(payload, ensure_ascii=False)
        elif isinstance(command, dict):
            payload = validate_payload(command)
            raw_line = json.dumps(payload, ensure_ascii=False)
        else:
            raw_line = command
            payload = parse_text(command, default_project=default_project)
            if not payload:
                return DslResult(ok=True, command=raw_line, verb="noop")

        verb = str(payload["verb"]).upper()
        root = (project_root or Path(payload.get("project", default_project or "."))).expanduser().resolve()

        if verb in QUERY_VERBS:
            from dsl2koru.handlers import run_query

            result = run_query(payload, project_root=root)
            return DslResult(
                ok=result.ok,
                verb=verb,
                command=raw_line,
                output=result.output,
                data=result.data,
                error=result.error,
            )

        if verb in COMMAND_VERBS:
            from dsl2koru.handlers import run_command

            result = run_command(payload, project_root=root)
            event_id = None
            if result.ok:
                store = EventStore.for_project(root)
                event_id = store.append_command(payload, result.to_dict())
            return DslResult(
                ok=result.ok,
                verb=verb,
                command=raw_line,
                output=result.output,
                data=result.data,
                error=result.error,
                event_id=event_id,
            )

        return DslResult(ok=False, verb=verb, command=raw_line, error=f"unsupported verb: {verb}")
    except Exception as exc:
        return DslResult(ok=False, command=raw_line or str(command), error=str(exc))


def execute_dsl_line(line: str, *, default_project: str | None = None) -> DslResult:
    return dispatch(line, default_project=default_project)


def execute_dsl(text: str, *, default_project: str | None = None) -> list[DslResult]:
    results: list[DslResult] = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        results.append(execute_dsl_line(line, default_project=default_project))
    return results
