"""Canonical text grammar for the Koru and compatibility Coru verbs."""

from __future__ import annotations

import shlex
from typing import Any

from dsl2koru.schema_registry import normalize_verb


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
    dashed = f"--{name.replace('_', '-').lower()}"
    keyword = name.replace("-", "_").upper()
    for idx, token in enumerate(rest):
        if token.lower() != dashed and token.replace("-", "_").upper() != keyword:
            continue
        if idx + 1 < len(rest) and not rest[idx + 1].startswith("--"):
            return rest[idx + 1]
        return "true"
    return None


def _ui_args(rest: list[str], skip: set[str] | None = None) -> list[str]:
    skip = skip or {"WINDOW", "IMAGE", "EXECUTE"}
    out: list[str] = []
    i = 0
    while i < len(rest):
        token = rest[i]
        if token.startswith("--"):
            i += 2 if i + 1 < len(rest) and not rest[i + 1].startswith("--") else 1
            continue
        if token.upper() in skip:
            i += 2 if token.upper() in {"WINDOW", "IMAGE"} and i + 1 < len(rest) else 1
            continue
        out.append(token)
        i += 1
    return out


def _parse_query_repair_history(rest: list[str], payload: dict[str, Any], default_project: str | None) -> None:
    payload["project"] = _flag(rest, "project") or default_project or "."
    limit = _flag(rest, "limit")
    payload["limit"] = int(limit) if limit else 20
    if code := _flag(rest, "code"):
        payload["code"] = code


def _parse_query_lane_status(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    payload["ide"] = (_flag(rest, "ide") or rest[0]) if rest else "auto"
    payload["instance"] = _flag(rest, "instance") or "default"


def _parse_validate_lane(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    _parse_query_lane_status(rest, payload, _default)


def _parse_resolve(rest: list[str], payload: dict[str, Any], default_project: str | None) -> None:
    stop = next((i for i, token in enumerate(rest) if token.upper() == "PROJECT"), len(rest))
    payload["prompt"] = " ".join(rest[:stop]).strip('"')
    project = _flag(rest, "project") or default_project
    if project:
        payload["project"] = project


def _parse_status(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if _flag(rest, "probe"):
        payload["probe"] = True


def _parse_repair_history(_rest: list[str], _payload: dict[str, Any], _default: str | None) -> None:
    pass


def _parse_env(rest: list[str], payload: dict[str, Any], default_file: str | None) -> None:
    if file_value := _flag(rest, "file") or default_file:
        payload["file"] = file_value


def _parse_query(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    args = [token for token in rest if not token.startswith("--")]
    if args:
        payload["target"] = " ".join(args)


def _parse_auto(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if shell := _flag(rest, "shell"):
        payload["shell"] = shell
    if auto_args := _flag(rest, "auto_args"):
        payload["auto_args"] = auto_args
    args = [token for token in rest if not token.startswith("--")]
    if args:
        payload["target"] = " ".join(args)


def _parse_lane(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    for name in ("ide", "instance", "file"):
        if value := _flag(rest, name):
            payload[name] = value


def _parse_ensure(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if _flag(rest, "install"):
        payload["install"] = True


def _parse_doctor(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if _flag(rest, "fix"):
        payload["fix"] = True
    if _flag(rest, "probe"):
        payload["probe"] = True
    if probe_prompt := _flag(rest, "probe_prompt"):
        payload["probe_prompt"] = probe_prompt


def _parse_calibration(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    for name in ("skip_fix", "skip_desktop", "skip_bridge"):
        if _flag(rest, name):
            payload[name] = True
    if probe_prompt := _flag(rest, "probe_prompt"):
        payload["probe_prompt"] = probe_prompt


def _parse_chat(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if _flag(rest, "llm"):
        payload["llm"] = True
    if shell := _flag(rest, "shell"):
        payload["shell"] = shell
    if _flag(rest, "single_action"):
        payload["single_action"] = True


def _parse_text(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    args = [token for token in rest if not token.startswith("--")]
    if args:
        payload["target"] = " ".join(args)
    _parse_chat(rest, payload, _default)


def _parse_sync(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    if _flag(rest, "all_ides"):
        payload["all_ides"] = True


def _parse_repair_run(rest: list[str], payload: dict[str, Any], default_project: str | None) -> None:
    canonical_style = default_project is not None or any(
        token.upper() in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} for token in rest
    )
    if _flag(rest, "fix"):
        payload["fix"] = True
    if ide := _flag(rest, "ide"):
        payload["ide"] = ide
    elif canonical_style:
        payload["ide"] = (
            rest[0] if rest and rest[0].upper() not in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} else "auto"
        )
    if instance := _flag(rest, "instance"):
        payload["instance"] = instance
    elif canonical_style:
        payload["instance"] = "default"
    if canonical_style:
        payload["project"] = _flag(rest, "project") or default_project or "."
        payload["trigger"] = _flag(rest, "trigger") or "manual"


def _parse_ui_common(rest: list[str], payload: dict[str, Any]) -> None:
    if image := _flag(rest, "image"):
        payload["image"] = image
    if window := _flag(rest, "window"):
        payload["window"] = window
    payload["execute"] = not (_flag(rest, "execute") == "0" or _flag(rest, "dry_run"))


def _parse_ui_capture(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    _parse_ui_common(rest, payload)


def _parse_ui_type(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
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


def _parse_ui_key(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    _parse_ui_common(rest, payload)
    if args := _ui_args(rest):
        payload["keys"] = args[0]


def _parse_ui_click(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    _parse_ui_common(rest, payload)
    if args := _ui_args(rest):
        payload["target"] = " ".join(args).strip('"')


def _parse_ui_nl(rest: list[str], payload: dict[str, Any], _default: str | None) -> None:
    _parse_ui_common(rest, payload)
    if args := _ui_args(rest):
        payload["prompt"] = " ".join(args).strip('"')


_PARSERS: dict[str, Any] = {
    "QUERY_REPAIR_HISTORY": _parse_query_repair_history,
    "QUERY_LANE_STATUS": _parse_query_lane_status,
    "VALIDATE_LANE": _parse_validate_lane,
    "RESOLVE": _parse_resolve,
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
    "UI_CAPTURE": _parse_ui_capture,
    "UI_TYPE": _parse_ui_type,
    "UI_KEY": _parse_ui_key,
    "UI_CLICK": _parse_ui_click,
    "UI_NL": _parse_ui_nl,
}


def parse_line(
    line: str,
    *,
    default_project: str | None = None,
    default_file: str | None = None,
) -> dict[str, Any]:
    tokens = _split_command(line)
    if not tokens:
        return {}
    raw_verb = tokens[0].upper()
    verb = normalize_verb(raw_verb)
    parser = _PARSERS.get(verb)
    if parser is None:
        raise ValueError(f"unknown DSL verb: {verb}")
    payload: dict[str, Any] = {"verb": verb}
    if raw_verb.replace("-", "_") == "LANE_STATUS":
        payload["lane_status"] = True
    context = default_project if verb in {"QUERY_REPAIR_HISTORY", "RESOLVE", "REPAIR_RUN"} else default_file
    parser(tokens[1:], payload, context)
    return payload


def _append_flag(parts: list[str], payload: dict[str, Any], name: str, *, flag: str | None = None) -> None:
    value = payload.get(name)
    if value is True:
        parts.append(flag or f"--{name.replace('_', '-')}")
    elif value not in (None, "", False):
        parts.extend([flag or f"--{name.replace('_', '-')}", str(value)])


def _serialize_query_repair_history(parts: list[str], payload: dict[str, Any]) -> None:
    parts.extend(["PROJECT", str(payload.get("project", "."))])
    if payload.get("limit") not in (None, 20):
        parts.extend(["LIMIT", str(payload["limit"])])
    if payload.get("code"):
        parts.extend(["CODE", str(payload["code"])])


def _serialize_query_lane_status(parts: list[str], payload: dict[str, Any]) -> None:
    parts.extend(["IDE", str(payload.get("ide", "auto")), "INSTANCE", str(payload.get("instance", "default"))])


def _serialize_validate_lane(parts: list[str], payload: dict[str, Any]) -> None:
    _serialize_query_lane_status(parts, payload)


def _serialize_resolve(parts: list[str], payload: dict[str, Any]) -> None:
    parts.append(f'"{payload.get("prompt", "")}"')
    if payload.get("project"):
        parts.extend(["PROJECT", str(payload["project"])])


def _serialize_status(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("probe"):
        parts.append("--probe")


def _serialize_env(parts: list[str], payload: dict[str, Any]) -> None:
    _append_flag(parts, payload, "file")


def _serialize_query(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("target"):
        parts.append(str(payload["target"]))


def _serialize_auto(parts: list[str], payload: dict[str, Any]) -> None:
    _append_flag(parts, payload, "shell")
    _append_flag(parts, payload, "auto_args")
    if payload.get("target"):
        parts.append(str(payload["target"]))


def _serialize_lane(parts: list[str], payload: dict[str, Any]) -> None:
    for name in ("ide", "instance", "file"):
        _append_flag(parts, payload, name)


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
    for name in ("skip_fix", "skip_desktop", "skip_bridge"):
        if payload.get(name):
            parts.append(f"--{name.replace('_', '-')}")
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
    _serialize_chat(parts, payload)


def _serialize_sync(parts: list[str], payload: dict[str, Any]) -> None:
    if payload.get("all_ides"):
        parts.append("--all-ides")


def _serialize_repair_run(parts: list[str], payload: dict[str, Any]) -> None:
    if "project" in payload or "trigger" in payload:
        parts.extend(["IDE", str(payload.get("ide", "auto")), "INSTANCE", str(payload.get("instance", "default"))])
        parts.extend(["PROJECT", str(payload.get("project", "."))])
        if payload.get("trigger") not in (None, "manual"):
            parts.extend(["TRIGGER", str(payload["trigger"])])
        if payload.get("fix"):
            parts.append("--fix")
        return
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
    "QUERY_REPAIR_HISTORY": _serialize_query_repair_history,
    "QUERY_LANE_STATUS": _serialize_query_lane_status,
    "VALIDATE_LANE": _serialize_validate_lane,
    "RESOLVE": _serialize_resolve,
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
    "UI_CAPTURE": lambda _parts, _payload: None,
    "UI_TYPE": _serialize_ui_type,
    "UI_KEY": _serialize_ui_key,
    "UI_CLICK": _serialize_ui_click,
    "UI_NL": _serialize_ui_nl,
}


def to_text(payload: dict[str, Any]) -> str:
    verb = normalize_verb(str(payload.get("verb", "")))
    serializer = _SERIALIZERS.get(verb)
    if serializer is None:
        raise ValueError(f"cannot serialize verb: {verb}")
    parts = [verb]
    if verb.startswith("UI_"):
        _append_flag(parts, payload, "image")
        _append_flag(parts, payload, "window")
        if payload.get("execute") is False:
            parts.extend(["EXECUTE", "0"])
    serializer(parts, payload)
    return " ".join(parts)
