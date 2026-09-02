"""Canonical CQRS dispatch bus for both DSL command-name families."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dsl2koru.codec import envelope_from_bytes, parse_text, validate_payload
from dsl2koru.events import EventStore
from dsl2koru.grammar import to_text
from dsl2koru.handlers.runner import Runner
from dsl2koru.result import DslResult
from dsl2koru.schema_registry import COMMAND_VERBS, KORU_DELEGATE_VERBS, QUERY_VERBS, UI_VERBS

_NATIVE_QUERY_VERBS = QUERY_VERBS & KORU_DELEGATE_VERBS
_COMPAT_QUERY_VERBS = QUERY_VERBS - KORU_DELEGATE_VERBS
_NATIVE_COMMAND_VERBS = COMMAND_VERBS & KORU_DELEGATE_VERBS
_COMPAT_COMMAND_VERBS = COMMAND_VERBS - KORU_DELEGATE_VERBS - UI_VERBS


def _normalize_command(
    command: str | dict[str, Any] | bytes,
    context: str | None,
) -> tuple[dict[str, Any], str, DslResult | None]:
    if isinstance(command, bytes):
        payload = envelope_from_bytes(command)
        return payload, json.dumps(payload, ensure_ascii=False), None
    if isinstance(command, dict):
        payload = validate_payload(command)
        return payload, to_text(payload), None
    raw_line = command.strip()
    payload = parse_text(raw_line, default_project=context, default_file=context)
    if not payload:
        return {}, raw_line, DslResult(ok=True, command=raw_line, action="noop")
    return payload, raw_line, None


def _native_result(result: Any, *, verb: str, raw_line: str, event_id: str | None = None) -> DslResult:
    return DslResult(
        ok=result.ok,
        verb=verb,
        command=raw_line,
        action=verb.lower(),
        output=result.output,
        data=result.data,
        error=result.error,
        event_id=event_id,
    )


def _dispatch_native(
    payload: dict[str, Any],
    *,
    verb: str,
    raw_line: str,
    project_root: Path,
) -> DslResult:
    if verb in _NATIVE_QUERY_VERBS:
        from dsl2koru.handlers import run_query

        return _native_result(run_query(payload, project_root=project_root), verb=verb, raw_line=raw_line)

    from dsl2koru.handlers import run_command

    result = run_command(payload, project_root=project_root)
    event_id = None
    if result.ok:
        event_id = EventStore.for_project(project_root).append_command(payload, result.to_dict())
    return _native_result(result, verb=verb, raw_line=raw_line, event_id=event_id)


def _dispatch_compat(
    payload: dict[str, Any],
    *,
    verb: str,
    raw_line: str,
    context: str | None,
    runner: Runner | None,
) -> DslResult:
    if verb in _COMPAT_QUERY_VERBS:
        from dsl2koru.handlers.query import run_query

        return run_query(payload, line=raw_line, runner=runner)

    if verb in UI_VERBS:
        from dsl2koru.handlers.ui import run_ui_command

        return run_ui_command(payload, line=raw_line)

    if verb in _COMPAT_COMMAND_VERBS:
        from dsl2koru.handlers.command import run_command

        result = run_command(payload, line=raw_line, runner=runner)
        event_id = None
        if result.ok:
            event_id = EventStore.for_default(context).append_command(payload, result.to_dict())
        result.event_id = event_id
        return result

    return DslResult(ok=False, verb=verb, command=raw_line, error=f"unsupported verb: {verb}")


def dispatch(
    command: str | dict[str, Any] | bytes,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    project_root: Path | None = None,
    runner: Runner | None = None,
) -> DslResult:
    """Validate and execute one native or compatibility command."""
    raw_line = ""
    context = default_file if default_file is not None else default_project
    try:
        payload, raw_line, early = _normalize_command(command, context)
        if early is not None:
            return early

        verb = str(payload["verb"]).upper()
        if verb in _NATIVE_QUERY_VERBS or verb in _NATIVE_COMMAND_VERBS:
            root = (
                project_root or Path(payload.get("project", context or "."))
            ).expanduser().resolve()
            return _dispatch_native(payload, verb=verb, raw_line=raw_line, project_root=root)
        return _dispatch_compat(payload, verb=verb, raw_line=raw_line, context=context, runner=runner)
    except Exception as exc:
        if not raw_line and isinstance(command, str):
            raw_line = command.strip()
        return DslResult(ok=False, command=raw_line or str(command), error=str(exc))


def execute_dsl_line(
    line: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    project_root: Path | None = None,
    runner: Runner | None = None,
) -> DslResult:
    return dispatch(
        line,
        default_file=default_file,
        default_project=default_project,
        project_root=project_root,
        runner=runner,
    )


def execute_dsl(
    text: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    project_root: Path | None = None,
    runner: Runner | None = None,
) -> list[DslResult]:
    results: list[DslResult] = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        results.append(
            execute_dsl_line(
                line,
                default_file=default_file,
                default_project=default_project,
                project_root=project_root,
                runner=runner,
            )
        )
    return results


def dispatch_text(
    script: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    project_root: Path | None = None,
    runner: Runner | None = None,
) -> list[dict[str, Any]]:
    return [
        result.to_dict()
        for result in execute_dsl(
            script,
            default_file=default_file,
            default_project=default_project,
            project_root=project_root,
            runner=runner,
        )
    ]
