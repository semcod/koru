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


def _parse_standard(verb: str, rest: list[str], std_fields: Payload, context: str | None) -> None:
    fields, positional = _VERB_SPECS[verb]
    for name, is_boolean in fields:
        value = _flag(rest, name)
        if value:
            std_fields[name] = True if is_boolean else value
    if verb == "ENV" and "file" not in std_fields and context:
        std_fields["file"] = context
    if positional and (args := _arguments(rest)):
        std_fields[positional] = " ".join(args)


def _parse_query_repair_history(rest: list[str], history_fields: Payload, default_project: str | None) -> None:
    history_fields["project"] = _flag(rest, "project") or default_project or "."
    history_fields["limit"] = int(limit) if (limit := _flag(rest, "limit")) else 20
    if code := _flag(rest, "code"):
        history_fields["code"] = code


def _parse_lane_status(rest: list[str], lane_fields: Payload, _context: str | None) -> None:
    lane_fields["ide"] = (_flag(rest, "ide") or rest[0]) if rest else "auto"
    lane_fields["instance"] = _flag(rest, "instance") or "default"


def _parse_resolve(rest: list[str], resolve_fields: Payload, default_project: str | None) -> None:
    stop = next((index for index, token in enumerate(rest) if token.upper() == "PROJECT"), len(rest))
    resolve_fields["prompt"] = " ".join(rest[:stop]).strip('"')
    if project := _flag(rest, "project") or default_project:
        resolve_fields["project"] = project


def _parse_repair_run(rest: list[str], repair_fields: Payload, default_project: str | None) -> None:
    canonical = default_project is not None or any(
        token.upper() in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} for token in rest
    )
    if _flag(rest, "fix"):
        repair_fields["fix"] = True
    for name in ("ide", "instance"):
        if value := _flag(rest, name):
            repair_fields[name] = value
    if canonical:
        repair_fields.setdefault(
            "ide",
            rest[0] if rest and rest[0].upper() not in {"IDE", "INSTANCE", "PROJECT", "TRIGGER"} else "auto",
        )
        repair_fields.setdefault("instance", "default")
        repair_fields["project"] = _flag(rest, "project") or default_project or "."
        repair_fields["trigger"] = _flag(rest, "trigger") or "manual"


_SPECIAL_PARSERS: dict[str, Parser] = {
    "QUERY_REPAIR_HISTORY": _parse_query_repair_history,
    "QUERY_LANE_STATUS": _parse_lane_status,
    "VALIDATE_LANE": _parse_lane_status,
    "RESOLVE": _parse_resolve,
    "REPAIR_RUN": _parse_repair_run,
}


def _parse_ui(verb: str, rest: list[str], ui_fields: Payload) -> None:
    for name in ("image", "window"):
        if value := _flag(rest, name):
            ui_fields[name] = value
    ui_fields["execute"] = not (_flag(rest, "execute") == "0" or _flag(rest, "dry_run"))
    args = _ui_arguments(rest)
    if verb == "UI_TYPE":
        if len(args) >= 2 and args[0].upper() == "IN":
            ui_fields.update(value="", field=" ".join(args[1:]).strip('"'))
        elif len(args) >= 3 and args[1].upper() == "IN":
            ui_fields.update(value=args[0].strip('"'), field=" ".join(args[2:]).strip('"'))
        elif args:
            ui_fields["value"] = args[0].strip('"')
    elif args:
        name, join = {
            "UI_KEY": ("keys", False),
            "UI_CLICK": ("target", True),
            "UI_NL": ("prompt", True),
        }.get(verb, ("", False))
        if name:
            ui_fields[name] = (" ".join(args) if join else args[0]).strip('"')


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
    parsed: Payload = {"verb": verb}
    if raw_verb.replace("-", "_") == "LANE_STATUS":
        parsed["lane_status"] = True
    context = default_project if verb in _SPECIAL_PARSERS else default_file
    if verb.startswith("UI_"):
        _parse_ui(verb, tokens[1:], parsed)
    elif parser := _SPECIAL_PARSERS.get(verb):
        parser(tokens[1:], parsed, context)
    elif verb in _VERB_SPECS:
        _parse_standard(verb, tokens[1:], parsed, context)
    else:
        raise ValueError(f"unknown DSL verb: {verb}")
    return parsed


def _append_field(fields: list[str], values: Payload, name: str) -> None:
    value = values.get(name)
    flag = f"--{name.replace('_', '-')}"
    if value is True:
        fields.append(flag)
    elif value not in (None, "", False):
        fields.extend([flag, str(value)])


def _serialize_standard(verb: str, std_tokens: list[str], std_values: Payload) -> None:
    fields, positional = _VERB_SPECS[verb]
    if verb == "TEXT" and positional and std_values.get(positional):
        std_tokens.append(str(std_values[positional]))
    for name, _is_boolean in fields:
        _append_field(std_tokens, std_values, name)
    if verb != "TEXT" and positional and std_values.get(positional):
        std_tokens.append(str(std_values[positional]))


def _serialize_query_repair_history(history_tokens: list[str], history_values: Payload) -> None:
    history_tokens.extend(["PROJECT", str(history_values.get("project", "."))])
    if history_values.get("limit") not in (None, 20):
        history_tokens.extend(["LIMIT", str(history_values["limit"])])
    if history_values.get("code"):
        history_tokens.extend(["CODE", str(history_values["code"])])


def _serialize_lane_status(lane_tokens: list[str], lane_values: Payload) -> None:
    lane_tokens.extend(
        [
            "IDE",
            str(lane_values.get("ide", "auto")),
            "INSTANCE",
            str(lane_values.get("instance", "default")),
        ]
    )


def _serialize_resolve(resolve_tokens: list[str], resolve_values: Payload) -> None:
    resolve_tokens.append(f'"{resolve_values.get("prompt", "")}"')
    if resolve_values.get("project"):
        resolve_tokens.extend(["PROJECT", str(resolve_values["project"])])


def _serialize_repair_run(repair_tokens: list[str], repair_values: Payload) -> None:
    if "project" in repair_values or "trigger" in repair_values:
        repair_tokens.extend(
            ["IDE", str(repair_values.get("ide", "auto")), "INSTANCE", str(repair_values.get("instance", "default"))]
        )
        repair_tokens.extend(["PROJECT", str(repair_values.get("project", "."))])
        if repair_values.get("trigger") not in (None, "manual"):
            repair_tokens.extend(["TRIGGER", str(repair_values["trigger"])])
        if repair_values.get("fix"):
            repair_tokens.append("--fix")
        return
    for name in ("fix", "ide", "instance"):
        _append_field(repair_tokens, repair_values, name)


def _serialize_ui(verb: str, ui_tokens: list[str], ui_values: Payload) -> None:
    if verb == "UI_TYPE":
        if ui_values.get("value") is not None:
            ui_tokens.append(f'"{ui_values["value"]}"')
        if ui_values.get("field"):
            ui_tokens.extend(["IN", f'"{ui_values["field"]}"'])
        return
    name = {"UI_KEY": "keys", "UI_CLICK": "target", "UI_NL": "prompt"}.get(verb)
    if name and ui_values.get(name):
        value = str(ui_values[name])
        ui_tokens.append(value if verb == "UI_KEY" else f'"{value}"')


_SPECIAL_SERIALIZERS: dict[str, Callable[[list[str], Payload], None]] = {
    "QUERY_REPAIR_HISTORY": _serialize_query_repair_history,
    "QUERY_LANE_STATUS": _serialize_lane_status,
    "VALIDATE_LANE": _serialize_lane_status,
    "RESOLVE": _serialize_resolve,
    "REPAIR_RUN": _serialize_repair_run,
}


def to_text(command: Payload) -> str:
    verb = normalize_verb(str(command.get("verb", "")))
    serialized = [verb]
    if verb.startswith("UI_"):
        for name in ("image", "window"):
            _append_field(serialized, command, name)
        if command.get("execute") is False:
            serialized.extend(["EXECUTE", "0"])
        _serialize_ui(verb, serialized, command)
    elif serializer := _SPECIAL_SERIALIZERS.get(verb):
        serializer(serialized, command)
    elif verb in _VERB_SPECS:
        _serialize_standard(verb, serialized, command)
    else:
        raise ValueError(f"cannot serialize verb: {verb}")
    return " ".join(serialized)
