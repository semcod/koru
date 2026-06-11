"""Text DSL grammar → validated command dict."""

from __future__ import annotations

import shlex
from typing import Any

from dsl2coru.schema_registry import normalize_verb


def _split_command(line: str) -> list[str]:
    line = line.strip()
    if not line or line.startswith("#"):
        return []
    return shlex.split(line, posix=True)


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    return str(value).lower() in {"1", "true", "yes"}


def _flag(rest: list[str], name: str) -> str | None:
    key = f"--{name.replace('_', '-')}"
    if key in rest:
        idx = rest.index(key)
        if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
            return rest[idx + 1]
        return "true"
    upper = name.upper()
    if upper in rest:
        idx = rest.index(upper)
        if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
            return rest[idx + 1]
    return None


def _ui_args(rest: list[str], skip: set[str] | None = None) -> list[str]:
    skip = skip or {"WINDOW", "IMAGE", "EXECUTE"}
    out: list[str] = []
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok.startswith("--"):
            i += 2 if i + 1 < len(rest) and not rest[i + 1].startswith("--") else 1
            continue
        if tok.upper() in skip:
            i += 2 if tok.upper() in {"WINDOW", "IMAGE"} and i + 1 < len(rest) else 1
            continue
        out.append(tok)
        i += 1
    return out


def _parse_status(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "probe"):
        payload["probe"] = True


def _parse_repair_history(_rest: list[str], _payload: dict[str, Any], _default_file: str | None) -> None:
    pass


def _parse_env(rest: list[str], payload: dict[str, Any], default_file: str | None) -> None:
    file_val = _flag(rest, "file") or default_file
    if file_val:
        payload["file"] = file_val


def _parse_query(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    args = [t for t in rest if not t.startswith("--")]
    if args:
        payload["target"] = " ".join(args)


def _parse_auto(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if shell := _flag(rest, "shell"):
        payload["shell"] = shell
    if auto_args := _flag(rest, "auto_args"):
        payload["auto_args"] = auto_args
    args = [t for t in rest if not t.startswith("--")]
    if args:
        payload["target"] = " ".join(args)


def _parse_lane(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if ide := _flag(rest, "ide"):
        payload["ide"] = ide
    if instance := _flag(rest, "instance"):
        payload["instance"] = instance
    if file_val := _flag(rest, "file"):
        payload["file"] = file_val


def _parse_ensure(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "install"):
        payload["install"] = True


def _parse_doctor(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "fix"):
        payload["fix"] = True
    if _flag(rest, "probe"):
        payload["probe"] = True
    if probe_prompt := _flag(rest, "probe_prompt") or _flag(rest, "probe-prompt"):
        payload["probe_prompt"] = probe_prompt


def _parse_calibration(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    for key, flag in (
        ("skip_fix", "skip-fix"),
        ("skip_desktop", "skip-desktop"),
        ("skip_bridge", "skip-bridge"),
    ):
        if _flag(rest, flag) or _flag(rest, key):
            payload[key] = True
    if probe_prompt := _flag(rest, "probe_prompt") or _flag(rest, "probe-prompt"):
        payload["probe_prompt"] = probe_prompt


def _parse_chat(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "llm"):
        payload["llm"] = True
    if shell := _flag(rest, "shell"):
        payload["shell"] = shell
    if _flag(rest, "single_action") or _flag(rest, "single-action"):
        payload["single_action"] = True


def _parse_text(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    args = [t for t in rest if not t.startswith("--")]
    if args:
        payload["target"] = " ".join(args)
    if _flag(rest, "llm"):
        payload["llm"] = True
    if shell := _flag(rest, "shell"):
        payload["shell"] = shell
    if _flag(rest, "single_action") or _flag(rest, "single-action"):
        payload["single_action"] = True


def _parse_sync(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "all_ides") or _flag(rest, "all-ides"):
        payload["all_ides"] = True


def _parse_repair_run(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    if _flag(rest, "fix"):
        payload["fix"] = True
    if ide := _flag(rest, "ide"):
        payload["ide"] = ide
    if instance := _flag(rest, "instance"):
        payload["instance"] = instance


def _parse_ui_common(rest: list[str], payload: dict[str, Any]) -> None:
    if image := _flag(rest, "image"):
        payload["image"] = image
    if window := _flag(rest, "window"):
        payload["window"] = window
    if _flag(rest, "execute") == "0" or _flag(rest, "dry_run"):
        payload["execute"] = False
    else:
        payload["execute"] = True


def _parse_ui_type(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    _parse_ui_common(rest, payload)
    args = _ui_args(rest)
    if len(args) >= 2 and args[0].upper() == "IN":
        payload["value"] = ""
        payload["field"] = " ".join(args[1:]).strip('"')
    elif len(args) >= 3 and args[1].upper() == "IN":
        payload["value"] = args[0].strip('"')
        payload["field"] = " ".join(args[2:]).strip('"')
    elif args:
        payload["value"] = args[0].strip('"')


def _parse_ui_key(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    _parse_ui_common(rest, payload)
    args = _ui_args(rest)
    if args:
        payload["keys"] = args[0]


def _parse_ui_click(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    _parse_ui_common(rest, payload)
    args = _ui_args(rest)
    if args:
        payload["target"] = " ".join(args).strip('"')


def _parse_ui_nl(rest: list[str], payload: dict[str, Any], _default_file: str | None) -> None:
    _parse_ui_common(rest, payload)
    args = _ui_args(rest)
    if args:
        payload["prompt"] = " ".join(args).strip('"')


_PARSERS: dict[str, Any] = {
    "STATUS": _parse_status,
    "REPAIR_HISTORY": _parse_repair_history,
    "ENV": _parse_env,
    "QUERY": _parse_query,
    "AUTO": _parse_auto,
    "LANE": _parse_lane,
    "ENSURE": _parse_ensure,
    "DOCTOR": _parse_doctor,
    "CALIBRATION": _parse_calibration,
    "CHAT": _parse_chat,
    "TEXT": _parse_text,
    "SYNC": _parse_sync,
    "REPAIR_RUN": _parse_repair_run,
    "UI_TYPE": _parse_ui_type,
    "UI_KEY": _parse_ui_key,
    "UI_CLICK": _parse_ui_click,
    "UI_NL": _parse_ui_nl,
}


def parse_line(line: str, *, default_file: str | None = None) -> dict[str, Any]:
    tokens = _split_command(line)
    if not tokens:
        return {}
    raw_verb = tokens[0].upper()
    verb = normalize_verb(raw_verb)
    rest = tokens[1:]
    payload: dict[str, Any] = {"verb": verb}
    if raw_verb in {"LANE_STATUS", "LANE-STATUS"}:
        payload["lane_status"] = True
    parser = _PARSERS.get(verb)
    if parser:
        parser(rest, payload, default_file)
    else:
        raise ValueError(f"unknown DSL verb: {verb}")
    return payload


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
