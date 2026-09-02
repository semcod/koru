"""Canonical dict ↔ protobuf codecs for Koru and Coru compatibility verbs."""

from __future__ import annotations

import json
from typing import Any

from dsl2koru.grammar import parse_line, to_text
from dsl2koru.result import DslResult
from dsl2koru.v1 import command_pb2, result_pb2

_BODY_MAP = {
    "QUERY_REPAIR_HISTORY": "query_repair_history",
    "QUERY_LANE_STATUS": "query_lane_status",
    "VALIDATE_LANE": "validate_lane",
    "RESOLVE": "resolve",
    "REPAIR_RUN": "repair_run",
    "STATUS": "status",
    "REPAIR_HISTORY": "repair_history",
    "ENV": "env",
    "QUERY": "query",
    "AUTO": "auto",
    "LANE": "lane",
    "ENSURE": "ensure",
    "DOCTOR": "doctor",
    "CALIBRATION": "calibration",
    "CHAT": "chat",
    "TEXT": "text",
    "SYNC": "sync",
}

# Values written when callers omit a field. Besides carrying command defaults,
# these assignments preserve which empty proto3 oneof bodies existed before the
# descriptor-driven codec replaced the individual verb functions.
_ENCODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "QUERY_REPAIR_HISTORY": {"project": ".", "limit": 20},
    "QUERY_LANE_STATUS": {"ide": "auto", "instance": "default"},
    "VALIDATE_LANE": {"ide": "auto", "instance": "default"},
    "RESOLVE": {"prompt": ""},
    "REPAIR_RUN": {"ide": "auto", "instance": "default", "fix": False},
    "STATUS": {"probe": False},
    "LANE": {"lane_status": False},
    "ENSURE": {"install": False},
    "DOCTOR": {"fix": False, "probe": False},
    "CALIBRATION": {"skip_fix": False, "skip_desktop": False, "skip_bridge": False},
    "CHAT": {"llm": False, "single_action": False},
    "TEXT": {"llm": False, "single_action": False},
    "SYNC": {"all_ides": False},
}

_DECODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "QUERY_REPAIR_HISTORY": {"project": "."},
    "QUERY_LANE_STATUS": {"ide": "auto", "instance": "default"},
    "VALIDATE_LANE": {"ide": "auto", "instance": "default"},
    "REPAIR_RUN": {"ide": "auto", "instance": "default"},
}

_EMPTY_VALUE_DEFAULTS = {"REPAIR_RUN": {"project": ".", "trigger": "manual"}}


def _write_field(message: Any, field: Any, value: Any) -> None:
    if field.is_repeated:
        values = value.split() if isinstance(value, str) else value
        getattr(message, field.name).extend(map(str, values))
    elif field.type == field.TYPE_BOOL:
        setattr(message, field.name, bool(value))
    elif field.type == field.TYPE_INT32:
        setattr(message, field.name, int(value))
    else:
        setattr(message, field.name, str(value))


def _set_body(envelope: command_pb2.DslEnvelope, cmd: dict[str, Any]) -> None:
    verb = str(cmd.get("verb", "")).upper()
    body_name = _BODY_MAP.get(verb)
    if not body_name:
        return
    message = getattr(envelope, body_name)
    defaults = _ENCODE_DEFAULTS.get(verb, {})
    empty_defaults = _EMPTY_VALUE_DEFAULTS.get(verb, {})
    wrote_field = False
    for field in message.DESCRIPTOR.fields:
        if field.name in cmd:
            value = cmd[field.name]
            if not value and field.name in empty_defaults:
                value = empty_defaults[field.name]
        elif field.name in defaults:
            value = defaults[field.name]
        else:
            continue
        if not value and field.name not in defaults and field.name not in empty_defaults:
            continue
        _write_field(message, field, value)
        wrote_field = True
    if not wrote_field and not message.DESCRIPTOR.fields:
        message.SetInParent()


def dict_to_envelope(
    cmd: dict[str, Any],
    *,
    default_project: str = "",
    default_file: str = "",
    correlation_id: str = "",
) -> command_pb2.DslEnvelope:
    envelope = command_pb2.DslEnvelope()
    envelope.verb = str(cmd.get("verb", "")).upper()
    _set_body(envelope, cmd)
    envelope.default_project = default_project
    envelope.default_file = default_file
    envelope.correlation_id = correlation_id
    return envelope


def envelope_to_dict(envelope: command_pb2.DslEnvelope) -> dict[str, Any]:
    verb = envelope.verb.upper()
    cmd: dict[str, Any] = {"verb": verb}
    body_name = _BODY_MAP.get(verb)
    if not body_name or envelope.WhichOneof("body") != body_name:
        return cmd
    message = getattr(envelope, body_name)
    defaults = _DECODE_DEFAULTS.get(verb, {})
    for field in message.DESCRIPTOR.fields:
        value = getattr(message, field.name)
        if field.is_repeated:
            if value:
                cmd[field.name] = list(value)
        elif field.name in defaults:
            cmd[field.name] = value or defaults[field.name]
        elif value:
            cmd[field.name] = value
    return cmd


def encode_protobuf(
    cmd: dict[str, Any],
    *,
    default_project: str = "",
    default_file: str = "",
    correlation_id: str = "",
) -> bytes:
    return dict_to_envelope(
        cmd,
        default_project=default_project,
        default_file=default_file,
        correlation_id=correlation_id,
    ).SerializeToString()


def decode_protobuf(data: bytes) -> dict[str, Any]:
    envelope = command_pb2.DslEnvelope()
    envelope.ParseFromString(data)
    return envelope_to_dict(envelope)


def encode_text_to_protobuf(
    line: str,
    *,
    default_project: str = "",
    default_file: str = "",
    correlation_id: str = "",
) -> bytes:
    payload = parse_line(
        line,
        default_project=default_project or None,
        default_file=default_file or None,
    )
    if not payload:
        raise ValueError("empty command")
    return encode_protobuf(
        payload,
        default_project=default_project,
        default_file=default_file,
        correlation_id=correlation_id,
    )


def decode_protobuf_to_text(data: bytes) -> str:
    return to_text(decode_protobuf(data))


def result_to_pb(result: DslResult) -> result_pb2.DslResult:
    pb = result_pb2.DslResult()
    pb.ok = result.ok
    pb.verb = result.verb
    pb.command = result.command
    pb.action = result.action
    pb.output = result.output
    pb.data_json = json.dumps(result.data, ensure_ascii=False).encode("utf-8")
    pb.error = result.error or ""
    pb.event_id = result.event_id or ""
    return pb


def pb_to_result(pb: result_pb2.DslResult) -> DslResult:
    try:
        data = json.loads(pb.data_json.decode("utf-8")) if pb.data_json else {}
    except json.JSONDecodeError:
        data = {}
    return DslResult(
        ok=pb.ok,
        verb=pb.verb,
        command=pb.command,
        action=pb.action,
        output=pb.output,
        data=data,
        error=pb.error or None,
        event_id=pb.event_id or None,
    )


def encode_result_protobuf(result: DslResult) -> bytes:
    return result_to_pb(result).SerializeToString()
