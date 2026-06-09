"""UI command handlers — delegate to koru.integrations.imgl_client."""

from __future__ import annotations

from typing import Any

from dsl2coru.result import DslResult


def run_ui_command(payload: dict[str, Any], *, line: str) -> DslResult:
    verb = str(payload["verb"]).upper()
    try:
        from koru.integrations.imgl_client import execute_nl, imgl_available, imgl_missing_message
    except ImportError as exc:
        return DslResult(
            ok=False,
            verb=verb,
            command=line,
            action=verb.lower(),
            error=f"koru integrations unavailable: {exc}",
        )

    if not imgl_available():
        return DslResult(
            ok=False,
            verb=verb,
            command=line,
            action=verb.lower(),
            error=imgl_missing_message(),
        )

    image = payload.get("image")
    window = payload.get("window")
    execute = bool(payload.get("execute", True))
    dry_run = not execute

    if verb == "UI_CAPTURE":
        prompt = "zrzut ekranu"
    elif verb == "UI_TYPE":
        value = str(payload.get("value") or "")
        field = str(payload.get("field") or "Chat input")
        prompt = f"wpisz {value} w {field}"
    elif verb == "UI_KEY":
        keys = str(payload.get("keys") or "Return")
        if "ctrl" in keys.lower():
            prompt = "naciśnij ctrl+enter"
        else:
            prompt = "naciśnij enter"
    elif verb == "UI_CLICK":
        target = str(payload.get("target") or "")
        prompt = f"kliknij {target}"
    elif verb == "UI_NL":
        prompt = str(payload.get("prompt") or "")
    else:
        return DslResult(ok=False, verb=verb, command=line, error=f"unknown UI verb: {verb}")

    result = execute_nl(prompt, image=image, window=window, execute=execute, dry_run=dry_run)
    return DslResult(
        ok=bool(result.get("ok")),
        verb=verb,
        command=line,
        action=verb.lower(),
        output=result.get("output"),
        data=result.get("data") or result,
        error=result.get("error"),
    )
