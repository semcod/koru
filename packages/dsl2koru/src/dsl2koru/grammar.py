"""Canonical text grammar for the Koru and compatibility Coru verbs."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from typing import Any

from dsl2koru.schema_registry import normalize_verb

Payload = dict[str, Any]
Parser = Callable[[list[str], Payload, str | None], None]
Field = tuple[str, bool]
VerbSpec = tuple[tuple[Field, ...], str | None]


def _split_command(line: str) -> list[str]:
    line = line.strip()
    return [] if not line or line.startswith("#") else shlex.split(line, posix=True)


def _flag(rest: list[str], name: str) -> str | None:
    dashed = f"--{name.replace('_', '-').lower()}"
    keyword = name.replace("-", "_").upper()
    for index, token in enumerate(rest):
        if token.lower() != dashed and token.replace("-", "_").upper() != keyword:
            continue
        if index + 1 < len(rest) and not rest[index + 1].startswith("--"):
            return rest[index + 1]
        return "true"
    return None


def _arguments(rest: list[str]) -> list[str]:
    return [token for token in rest if not token.startswith("--")]


def _ui_arguments(rest: list[str]) -> list[str]:
    out: list[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token.startswith("--"):
            index += 2 if index + 1 < len(rest) and not rest[index + 1].startswith("--") else 1
        elif token.upper() in {"WINDOW", "IMAGE", "EXECUTE"}:
            index += 2 if token.upper() in {"WINDOW", "IMAGE"} and index + 1 < len(rest) else 1
        else:
            out.append(token)
            index += 1
    return out


# The bool marker distinguishes presence-only switches from value fields. Field
# order is also the canonical serialization order.
_VERB_SPECS: dict[str, VerbSpec] = {
    "STATUS": ((("probe", True),), None),
    "REPAIR_HISTORY": ((), None),
    "ENV": ((("file", False),), None),
    "QUERY": ((), "target"),
    "AUTO": ((("shell", False), ("auto_args", False)), "target"),
    "LANE": ((("ide", False), ("instance", False), ("file", False)), None),
    "ENSURE": ((("install", True),), None),
    "DOCTOR": ((("fix", True), ("probe", True), ("probe_prompt", False)), None),
    "CALIBRATION": (
        (("skip_fix", True), ("skip_desktop", True), ("skip_bridge", True), ("probe_prompt", False)),
        None,
    ),
    "CHAT": ((("llm", True), ("shell", False), ("single_action", True)), None),
    "TEXT": ((("llm", True), ("shell", False), ("single_action", True)), "target"),
    "SYNC": ((("all_ides", True),), None),
}


def _parse_standard(verb: str, rest: list[str], payload: Payload, context: str | None) -> None:
    fields, positional = _VERB_SPECS[verb]
    for name, is_boolean in fields:
        value = _flag(rest, name)
        if value:
            payload[name] = True if is_boolean else value
    if verb == "ENV" and "file" not in payload and context:
        payload["file"] = context
    if positional and (args := _arguments(rest)):
        payload[positional] = " ".join(args)


def _parse_query_repair_history(rest: list[str], payload: Payload, default_project: str | None) -> None:
    payload["project"] = _flag(rest, "project") or default_project or "."
    payload["limit"] = int(limit) if (limit := _flag(rest, "limit")) else 20
    if code := _flag(rest, "code"):
        payload["code"] = code


def _parse_lane_status(rest: list[str], payload: Payload, _context: str | None) -> None:
    payload["ide"] = (_flag(rest, "ide") or rest[0]) if rest else "auto"
    payload["instance"] = _flag(rest, "instance") or "default"


def _parse_resolve(rest: list[str], payload: Payload, default_project: str | None) -> None:
    stop = next((index for index, token in enumerate(rest) if token.upper() == "PROJECT"), len(rest))
    payload["prompt"] = " ".join(rest[:stop]).strip('"')
    if project := _flag(rest, "project") or default_project:
        payload["project"] = project


def _parse_repair_run(rest: list[str], payload: Payload, default_project: str | None) -> None:
    canonical = default_project is not None or any(
        token.upper() in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} for token in rest
    )
    if _flag(rest, "fix"):
        payload["fix"] = True
    for name in ("ide", "instance"):
        if value := _flag(rest, name):
            payload[name] = value
    if canonical:
        payload.setdefault(
            "ide",
            rest[0] if rest and rest[0].upper() not in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} else "auto",
        )
        payload.setdefault("instance", "default")
        payload["project"] = _flag(rest, "project") or default_project or "."
        payload["trigger"] = _flag(rest, "trigger") or "manual"


_SPECIAL_PARSERS: dict[str, Parser] = {
    "QUERY_REPAIR_HISTORY": _parse_query_repair_history,
    "QUERY_LANE_STATUS": _parse_lane_status,
    "VALIDATE_LANE": _parse_lane_status,
    "RESOLVE": _parse_resolve,
    "REPAIR_RUN": _parse_repair_run,
}


def _parse_ui(verb: str, rest: list[str], payload: Payload) -> None:
    for name in ("image", "window"):
        if value := _flag(rest, name):
            payload[name] = value
    payload["execute"] = not (_flag(rest, "execute") == "0" or _flag(rest, "dry_run"))
    args = _ui_arguments(rest)
    if verb == "UI_TYPE":
        if len(args) >= 2 and args[0].upper() == "IN":
            payload.update(value="", field=" ".join(args[1:]).strip('"'))
        elif len(args) >= 3 and args[1].upper() == "IN":
            payload.update(value=args[0].strip('"'), field=" ".join(args[2:]).strip('"'))
        elif args:
            payload["value"] = args[0].strip('"')
    elif args:
        name, join = {
            "UI_KEY": ("keys", False),
            "UI_CLICK": ("target", True),
            "UI_NL": ("prompt", True),
        }.get(verb, ("", False))
        if name:
            payload[name] = (" ".join(args) if join else args[0]).strip('"')


def parse_line(
    line: str,
    *,
    default_project: str | None = None,
    default_file: str | None = None,
) -> Payload:
    tokens = _split_command(line)
    if not tokens:
        return {}
    raw_verb = tokens[0].upper()
    verb = normalize_verb(raw_verb)
    payload: Payload = {"verb": verb}
    if raw_verb.replace("-", "_") == "LANE_STATUS":
        payload["lane_status"] = True
    context = default_project if verb in _SPECIAL_PARSERS else default_file
    if verb.startswith("UI_"):
        _parse_ui(verb, tokens[1:], payload)
    elif parser := _SPECIAL_PARSERS.get(verb):
        parser(tokens[1:], payload, context)
    elif verb in _VERB_SPECS:
        _parse_standard(verb, tokens[1:], payload, context)
    else:
        raise ValueError(f"unknown DSL verb: {verb}")
    return payload


def _append_field(parts: list[str], payload: Payload, name: str) -> None:
    value = payload.get(name)
    flag = f"--{name.replace('_', '-')}"
    if value is True:
        parts.append(flag)
    elif value not in (None, "", False):
        parts.extend([flag, str(value)])


def _serialize_standard(verb: str, parts: list[str], payload: Payload) -> None:
    fields, positional = _VERB_SPECS[verb]
    if verb == "TEXT" and positional and payload.get(positional):
        parts.append(str(payload[positional]))
    for name, _is_boolean in fields:
        _append_field(parts, payload, name)
    if verb != "TEXT" and positional and payload.get(positional):
        parts.append(str(payload[positional]))


def _serialize_query_repair_history(parts: list[str], payload: Payload) -> None:
    parts.extend(["PROJECT", str(payload.get("project", "."))])
    if payload.get("limit") not in (None, 20):
        parts.extend(["LIMIT", str(payload["limit"])])
    if payload.get("code"):
        parts.extend(["CODE", str(payload["code"])])


def _serialize_lane_status(parts: list[str], payload: Payload) -> None:
    parts.extend(["IDE", str(payload.get("ide", "auto")), "INSTANCE", str(payload.get("instance", "default"))])


def _serialize_resolve(parts: list[str], payload: Payload) -> None:
    parts.append(f'"{payload.get("prompt", "")}"')
    if payload.get("project"):
        parts.extend(["PROJECT", str(payload["project"])])


def _serialize_repair_run(parts: list[str], payload: Payload) -> None:
    if "project" in payload or "trigger" in payload:
        parts.extend(["IDE", str(payload.get("ide", "auto")), "INSTANCE", str(payload.get("instance", "default"))])
        parts.extend(["PROJECT", str(payload.get("project", "."))])
        if payload.get("trigger") not in (None, "manual"):
            parts.extend(["TRIGGER", str(payload["trigger"])])
        if payload.get("fix"):
            parts.append("--fix")
        return
    for name in ("fix", "ide", "instance"):
        _append_field(parts, payload, name)


def _serialize_ui(verb: str, parts: list[str], payload: Payload) -> None:
    if verb == "UI_TYPE":
        if payload.get("value") is not None:
            parts.append(f'"{payload["value"]}"')
        if payload.get("field"):
            parts.extend(["IN", f'"{payload["field"]}"'])
        return
    name = {"UI_KEY": "keys", "UI_CLICK": "target", "UI_NL": "prompt"}.get(verb)
    if name and payload.get(name):
        value = str(payload[name])
        parts.append(value if verb == "UI_KEY" else f'"{value}"')


_SPECIAL_SERIALIZERS: dict[str, Callable[[list[str], Payload], None]] = {
    "QUERY_REPAIR_HISTORY": _serialize_query_repair_history,
    "QUERY_LANE_STATUS": _serialize_lane_status,
    "VALIDATE_LANE": _serialize_lane_status,
    "RESOLVE": _serialize_resolve,
    "REPAIR_RUN": _serialize_repair_run,
}


def to_text(payload: Payload) -> str:
    verb = normalize_verb(str(payload.get("verb", "")))
    parts = [verb]
    if verb.startswith("UI_"):
        for name in ("image", "window"):
            _append_field(parts, payload, name)
        if payload.get("execute") is False:
            parts.extend(["EXECUTE", "0"])
        _serialize_ui(verb, parts, payload)
    elif serializer := _SPECIAL_SERIALIZERS.get(verb):
        serializer(parts, payload)
    elif verb in _VERB_SPECS:
        _serialize_standard(verb, parts, payload)
    else:
        raise ValueError(f"cannot serialize verb: {verb}")
    return " ".join(parts)
