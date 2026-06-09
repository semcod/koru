"""CQRS dispatch bus for dsl2coru."""

from __future__ import annotations

import json
from typing import Any

from dsl2coru.codec import envelope_from_bytes, parse_text, validate_payload
from dsl2coru.events import EventStore
from dsl2coru.grammar import to_text
from dsl2coru.handlers.runner import Runner
from dsl2coru.result import DslResult
from dsl2coru.schema_registry import COMMAND_VERBS, KORU_DELEGATE_VERBS, QUERY_VERBS, UI_VERBS


def _dispatch_koru(
    line: str,
    *,
    default_file: str | None = None,
) -> DslResult | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    verb = stripped.split()[0].upper()
    if verb not in KORU_DELEGATE_VERBS:
        return None
    from dsl2koru.bus import dispatch as koru_dispatch

    result = koru_dispatch(stripped, default_project=default_file)
    return DslResult(
        ok=result.ok,
        verb=result.verb or verb,
        command=stripped,
        action=(result.verb or verb).lower(),
        output=result.output,
        data=result.data,
        error=result.error,
        event_id=result.event_id,
    )


def dispatch(
    command: str | dict[str, Any] | bytes,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    runner: Runner | None = None,
) -> DslResult:
    raw_line = ""
    ctx = default_file if default_file is not None else default_project
    try:
        if isinstance(command, bytes):
            payload = envelope_from_bytes(command)
            raw_line = json.dumps(payload, ensure_ascii=False)
        elif isinstance(command, dict):
            payload = validate_payload(command)
            raw_line = to_text(payload)
        else:
            raw_line = command.strip()
            delegated = _dispatch_koru(raw_line, default_file=ctx)
            if delegated is not None:
                return delegated
            payload = parse_text(raw_line, default_file=ctx)
            if not payload:
                return DslResult(ok=True, command=raw_line, action="noop")

        verb = str(payload["verb"]).upper()
        if verb in KORU_DELEGATE_VERBS:
            delegated = _dispatch_koru(raw_line, default_file=ctx)
            if delegated is not None:
                return delegated

        if verb in QUERY_VERBS:
            from dsl2coru.handlers import run_query

            return run_query(payload, line=raw_line, runner=runner)

        if verb in UI_VERBS:
            from dsl2coru.handlers.ui import run_ui_command

            return run_ui_command(payload, line=raw_line)

        if verb in COMMAND_VERBS:
            from dsl2coru.handlers import run_command

            result = run_command(payload, line=raw_line, runner=runner)
            event_id = None
            if result.ok:
                store = EventStore.for_default(ctx)
                event_id = store.append_command(payload, result.to_dict())
            return DslResult(
                ok=result.ok,
                verb=verb,
                command=raw_line,
                action=result.action,
                output=result.output,
                data=result.data,
                error=result.error,
                event_id=event_id,
            )

        return DslResult(ok=False, verb=verb, command=raw_line, error=f"unsupported verb: {verb}")
    except Exception as exc:
        return DslResult(ok=False, command=raw_line or str(command), error=str(exc))


def execute_dsl_line(
    line: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    runner: Runner | None = None,
) -> DslResult:
    return dispatch(line, default_file=default_file, default_project=default_project, runner=runner)


def execute_dsl(
    text: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    runner: Runner | None = None,
) -> list[DslResult]:
    ctx = default_file if default_file is not None else default_project
    results: list[DslResult] = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        results.append(execute_dsl_line(line, default_file=ctx, runner=runner))
    return results


def dispatch_text(
    script: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    runner: Runner | None = None,
) -> list[dict[str, Any]]:
    return [result.to_dict() for result in execute_dsl(script, default_file=default_file, default_project=default_project, runner=runner)]
