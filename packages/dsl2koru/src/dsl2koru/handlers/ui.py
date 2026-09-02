"""Compatibility UI command handlers delegated to IMGL."""

from __future__ import annotations

from typing import Any

from dsl2koru.result import DslResult


def _ui_prompt_for_verb(verb: str, payload: dict[str, Any]) -> str | None:
    if verb == "UI_CAPTURE":
        return "zrzut ekranu"
    if verb == "UI_TYPE":
        value = str(payload.get("value") or "")
        field = str(payload.get("field") or "Chat input")
        return f"wpisz {value} w {field}"
    if verb == "UI_KEY":
        keys = str(payload.get("keys") or "Return")
        return "naciśnij ctrl+enter" if "ctrl" in keys.lower() else "naciśnij enter"
    if verb == "UI_CLICK":
        return f"kliknij {payload.get('target') or ''}"
    if verb == "UI_NL":
        return str(payload.get("prompt") or "")
    return None


def _ensure_imgl_available() -> tuple[Any, str]:
    try:
        from koru.integrations.imgl_client import execute_nl, imgl_available, imgl_missing_message
    except ImportError as exc:
        return None, f"koru integrations unavailable: {exc}"
    return (execute_nl, "") if imgl_available() else (None, imgl_missing_message())


def run_ui_command(payload: dict[str, Any], *, line: str) -> DslResult:
    verb = str(payload["verb"]).upper()
    executor, error = _ensure_imgl_available()
    if executor is None:
        return DslResult(ok=False, verb=verb, command=line, action=verb.lower(), error=error)

    prompt = _ui_prompt_for_verb(verb, payload)
    if prompt is None:
        return DslResult(ok=False, verb=verb, command=line, error=f"unknown UI verb: {verb}")
    execute = bool(payload.get("execute", True))
    result = executor(
        prompt,
        image=payload.get("image"),
        window=payload.get("window"),
        execute=execute,
        dry_run=not execute,
    )
    return DslResult(
        ok=bool(result.get("ok")),
        verb=verb,
        command=line,
        action=verb.lower(),
        output=result.get("output"),
        data=result.get("data") or result,
        error=result.get("error"),
    )
