"""Validated command dict → text DSL grammar."""

from __future__ import annotations

from typing import Any


def _append_flag(parts: list[str], payload: dict[str, Any], name: str, *, flag: str | None = None) -> None:
    value = payload.get(name)
    if value is True:
        parts.append(flag or f"--{name.replace('_', '-')}")
    elif value not in (None, "", False):
        parts.extend([flag or f"--{name.replace('_', '-')}", str(value)])


def _serialize_status(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("probe"):
        parts.append("--probe")


def _serialize_env(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("file"):
        parts.extend(["--file", str(payload["file"])])


def _serialize_query(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("target"):
        parts.append(str(payload["target"]))


def _serialize_auto(parts: list[str], payload: dict[str, Any]) -> None:
    _append_flag(parts, payload, "shell")
    _append_flag(parts, payload, "auto_args")
    if payload.get("target"):
        parts.append(str(payload["target"]))


def _serialize_lane(parts: list[str], payload: dict[str, Any]) -> None:
    _append_flag(parts, payload, "ide")
    _append_flag(parts, payload, "instance")
    _append_flag(parts, payload, "file")


def _serialize_ensure(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("install"):
        parts.append("--install")


def _serialize_doctor(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("fix"):
        parts.append("--fix")
    if payload.get("probe"):
        parts.append("--probe")
    _append_flag(parts, payload, "probe_prompt", flag="--probe-prompt")


def _serialize_calibration(parts: list[str], payload: dict[str, Any]) -> None:
    for key in ("skip_fix", "skip_desktop", "skip_bridge"):
        if payload.get(key):
            parts.append(f"--{key.replace('_', '-')}")
    _append_flag(parts, payload, "probe_prompt", flag="--probe-prompt")


def _serialize_chat(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("llm"):
        parts.append("--llm")
    _append_flag(parts, payload, "shell")
    if payload.get("single_action"):
        parts.append("--single-action")


def _serialize_text(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("target"):
        parts.append(str(payload["target"]))
    if payload.get("llm"):
        parts.append("--llm")
    _append_flag(parts, payload, "shell")
    if payload.get("single_action"):
        parts.append("--single-action")


def _serialize_sync(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("all_ides"):
        parts.append("--all-ides")


def _serialize_repair_run(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("fix"):
        parts.append("--fix")
    _append_flag(parts, payload, "ide")
    _append_flag(parts, payload, "instance")


def _serialize_repair_history(_parts: list[str], _payload: dict[str, Any]) -> None:
    pass


def _serialize_ui_type(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("value") is not None:
        parts.append(f'"{payload["value"]}"')
    if payload.get("field"):
        parts.extend(["IN", f'"{payload["field"]}"'])


def _serialize_ui_key(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("keys"):
        parts.append(str(payload["keys"]))


def _serialize_ui_click(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("target"):
        parts.append(f'"{payload["target"]}"')


def _serialize_ui_nl(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("prompt"):
        parts.append(f'"{payload["prompt"]}"')


_SERIALIZERS: dict[str, Any] = {
    "STATUS": _serialize_status,
    "ENV": _serialize_env,
    "QUERY": _serialize_query,
    "AUTO": _serialize_auto,
    "LANE": _serialize_lane,
    "ENSURE": _serialize_ensure,
    "DOCTOR": _serialize_doctor,
    "CALIBRATION": _serialize_calibration,
    "CHAT": _serialize_chat,
    "TEXT": _serialize_text,
    "SYNC": _serialize_sync,
    "REPAIR_RUN": _serialize_repair_run,
    "REPAIR_HISTORY": _serialize_repair_history,
    "UI_TYPE": _serialize_ui_type,
    "UI_KEY": _serialize_ui_key,
    "UI_CLICK": _serialize_ui_click,
    "UI_NL": _serialize_ui_nl,
}


def to_text(payload: dict[str, Any]) -> str:
    verb = str(payload.get("verb", "")).upper()
    parts = [verb]
    if verb.startswith("UI_"):
        _append_flag(parts, payload, "image")
        _append_flag(parts, payload, "window")
        if payload.get("execute") is False:
            parts.append("EXECUTE 0")
    serializer = _SERIALIZERS.get(verb)
    if serializer:
        serializer(parts, payload)
    else:
        raise ValueError(f"cannot serialize verb: {verb}")
    return " ".join(parts)