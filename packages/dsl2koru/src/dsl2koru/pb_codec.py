"""Dict ↔ protobuf DslEnvelope / DslResult."""

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
}


def _set_body(envelope: command_pb2.DslEnvelope, cmd: dict[str, Any]) -> None:
    verb = str(cmd.get("verb", "")).upper()
    field = _BODY_MAP.get(verb)
    if not field:
        return
    msg = getattr(envelope, field)
    if verb == "QUERY_REPAIR_HISTORY":
        msg.project = str(cmd.get("project", "."))
        msg.limit = int(cmd.get("limit", 20))
        if cmd.get("code"):
            msg.code = str(cmd["code"])
    elif verb == "QUERY_LANE_STATUS":
        msg.ide = str(cmd.get("ide", "auto"))
        msg.instance = str(cmd.get("instance", "default"))
    elif verb == "VALIDATE_LANE":
        msg.ide = str(cmd.get("ide", "auto"))
        msg.instance = str(cmd.get("instance", "default"))
    elif verb == "RESOLVE":
        msg.prompt = str(cmd.get("prompt", ""))
        if cmd.get("project"):
            msg.project = str(cmd["project"])
    elif verb == "REPAIR_RUN":
        msg.ide = str(cmd.get("ide", "auto"))
        msg.instance = str(cmd.get("instance", "default"))
        msg.project = str(cmd.get("project", "."))
        msg.trigger = str(cmd.get("trigger", "manual"))


def envelope_to_dict(envelope: command_pb2.DslEnvelope) -> dict[str, Any]:
    verb = envelope.verb.upper()
    cmd: dict[str, Any] = {"verb": verb}
    field = _BODY_MAP.get(verb)
    if not field or envelope.WhichOneof("body") != field:
        return cmd
    msg = getattr(envelope, field)
    if verb == "QUERY_REPAIR_HISTORY":
        cmd["project"] = msg.project or "."
        if msg.limit:
            cmd["limit"] = msg.limit
        if msg.code:
            cmd["code"] = msg.code
    elif verb == "QUERY_LANE_STATUS":
        cmd["ide"] = msg.ide or "auto"
        cmd["instance"] = msg.instance or "default"
    elif verb == "VALIDATE_LANE":
        cmd["ide"] = msg.ide or "auto"
        cmd["instance"] = msg.instance or "default"
    elif verb == "RESOLVE":
        if msg.prompt:
            cmd["prompt"] = msg.prompt
        if msg.project:
            cmd["project"] = msg.project
    elif verb == "REPAIR_RUN":
        cmd["ide"] = msg.ide or "auto"
        cmd["instance"] = msg.instance or "default"
        cmd["project"] = msg.project or "."
        if msg.trigger:
            cmd["trigger"] = msg.trigger
    return cmd


def encode_protobuf(cmd: dict[str, Any], *, default_project: str = "", correlation_id: str = "") -> bytes:
    envelope = command_pb2.DslEnvelope()
    envelope.verb = str(cmd.get("verb", "")).upper()
    _set_body(envelope, cmd)
    envelope.default_project = default_project
    envelope.correlation_id = correlation_id
    return envelope.SerializeToString()


def decode_protobuf(data: bytes) -> dict[str, Any]:
    envelope = command_pb2.DslEnvelope()
    envelope.ParseFromString(data)
    return envelope_to_dict(envelope)


def encode_text_to_protobuf(line: str, *, default_project: str = "", correlation_id: str = "") -> bytes:
    payload = parse_line(line, default_project=default_project or None)
    if not payload:
        raise ValueError("empty command")
    return encode_protobuf(payload, default_project=default_project, correlation_id=correlation_id)


def decode_protobuf_to_text(data: bytes) -> str:
    return to_text(decode_protobuf(data))


def result_to_pb(result: DslResult) -> result_pb2.DslResult:
    pb = result_pb2.DslResult()
    pb.ok = result.ok
    pb.verb = result.verb
    pb.output = result.output
    pb.data_json = json.dumps(result.data, ensure_ascii=False).encode("utf-8")
    pb.error = result.error or ""
    pb.event_id = result.event_id or ""
    pb.command = result.command
    return pb


def encode_result_protobuf(result: DslResult) -> bytes:
    return result_to_pb(result).SerializeToString()
