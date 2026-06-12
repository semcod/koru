"""UI command handlers — delegate to koru.integrations.imgl_client."""

from __future__ import annotations

from typing import Any

from dsl2coru.result import DslResult


def _ui_prompt_for_verb(verb: str, payload: dict[str, Any]) -> str | None:
    if verb == "UI_CAPTURE":
        return "zrzut ekranu"
    if verb == "UI_TYPE":
        value = str(payload.get("value") or "")
        field = str(payload.get("field") or "Chat input")
        return f"wpisz {value} w {field}"
    if verb == "UI_KEY":
        keys = str(payload.get("keys") or "Return")
        if "ctrl" in keys.lower():
            return "naciśnij ctrl+enter"
        return "naciśnij enter"
    if verb == "UI_CLICK":
        target = str(payload.get("target") or "")
        return f"kliknij {target}"
    if verb == "UI_NL":
        return str(payload.get("prompt") or "")
    return None


def _ensure_imgl_available(verb: str, line: str) -> tuple[Any, str] | None:
    try:
        from koru.integrations.imgl_client import execute_nl, imgl_available, imgl_missing_message
    except ImportError as exc:
        return None, f"koru integrations unavailable: {exc}"
    if not imgl_available():
        return None, imgl_missing_message()
    return execute_nl, ""


def _build_ui_result(
    verb: str, line: str, result: dict[str, Any]
) -> DslResult:
    return DslResult(
        ok=bool(result.get("ok")),
        verb=verb,
        command=line,
        action=verb.lower(),
        output=result.get("output"),
        data=result.get("data") or result,
        error=result.get("error"),
    )


def run_ui_command(payload: dict[str, Any], *, line: str) -> DslResult:
    verb = str(payload["verb"]).upper()
    executor, error = _ensure_imgl_available(verb, line)
    if executor is None:
        return DslResult(
            ok=False,
            verb=verb,
            command=line,
            action=verb.lower(),
            error=error,
        )

    image = payload.get("image")
    window = payload.get("window")
    execute = bool(payload.get("execute", True))
    dry_run = not execute

    prompt = _ui_prompt_for_verb(verb, payload)
    if prompt is None:
        return DslResult(ok=False, verb=verb, command=line, error=f"unknown UI verb: {verb}")

    result = executor(prompt, image=image, window=window, execute=execute, dry_run=dry_run)
    return _build_ui_result(verb, line, result)
