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


def _set_query_repair_history(msg: Any, cmd: dict[str, Any]) -> None:
    msg.project = str(cmd.get("project", "."))
    msg.limit = int(cmd.get("limit", 20))
    if cmd.get("code"):
        msg.code = str(cmd["code"])


def _set_query_lane_status(msg: Any, cmd: dict[str, Any]) -> None:
    msg.ide = str(cmd.get("ide", "auto"))
    msg.instance = str(cmd.get("instance", "default"))


def _set_validate_lane(msg: Any, cmd: dict[str, Any]) -> None:
    msg.ide = str(cmd.get("ide", "auto"))
    msg.instance = str(cmd.get("instance", "default"))


def _set_resolve(msg: Any, cmd: dict[str, Any]) -> None:
    msg.prompt = str(cmd.get("prompt", ""))
    if cmd.get("project"):
        msg.project = str(cmd["project"])


def _set_repair_run(msg: Any, cmd: dict[str, Any]) -> None:
    msg.ide = str(cmd.get("ide", "auto"))
    msg.instance = str(cmd.get("instance", "default"))
    msg.project = str(cmd.get("project", "."))
    msg.trigger = str(cmd.get("trigger", "manual"))


_BODY_SETTERS: dict[str, Any] = {
    "QUERY_REPAIR_HISTORY": _set_query_repair_history,
    "QUERY_LANE_STATUS": _set_query_lane_status,
    "VALIDATE_LANE": _set_validate_lane,
    "RESOLVE": _set_resolve,
    "REPAIR_RUN": _set_repair_run,
}


def _set_body(envelope: command_pb2.DslEnvelope, cmd: dict[str, Any]) -> None:
    verb = str(cmd.get("verb", "")).upper()
    field = _BODY_MAP.get(verb)
    if not field:
        return
    setter = _BODY_SETTERS.get(verb)
    if setter:
        setter(getattr(envelope, field), cmd)


def _extract_query_repair_history(msg: Any, cmd: dict[str, Any]) -> None:
    cmd["project"] = msg.project or "."
    if msg.limit:
        cmd["limit"] = msg.limit
    if msg.code:
        cmd["code"] = msg.code


def _extract_query_lane_status(msg: Any, cmd: dict[str, Any]) -> None:
    cmd["ide"] = msg.ide or "auto"
    cmd["instance"] = msg.instance or "default"


def _extract_validate_lane(msg: Any, cmd: dict[str, Any]) -> None:
    cmd["ide"] = msg.ide or "auto"
    cmd["instance"] = msg.instance or "default"


def _extract_resolve(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.prompt:
        cmd["prompt"] = msg.prompt
    if msg.project:
        cmd["project"] = msg.project


def _extract_repair_run(msg: Any, cmd: dict[str, Any]) -> None:
    cmd["ide"] = msg.ide or "auto"
    cmd["instance"] = msg.instance or "default"
    cmd["project"] = msg.project or "."
    if msg.trigger:
        cmd["trigger"] = msg.trigger


_BODY_EXTRACTORS: dict[str, Any] = {
    "QUERY_REPAIR_HISTORY": _extract_query_repair_history,
    "QUERY_LANE_STATUS": _extract_query_lane_status,
    "VALIDATE_LANE": _extract_validate_lane,
    "RESOLVE": _extract_resolve,
    "REPAIR_RUN": _extract_repair_run,
}


def envelope_to_dict(envelope: command_pb2.DslEnvelope) -> dict[str, Any]:
    verb = envelope.verb.upper()
    cmd: dict[str, Any] = {"verb": verb}
    field = _BODY_MAP.get(verb)
    if not field or envelope.WhichOneof("body") != field:
        return cmd
    extractor = _BODY_EXTRACTORS.get(verb)
    if extractor:
        extractor(getattr(envelope, field), cmd)
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
